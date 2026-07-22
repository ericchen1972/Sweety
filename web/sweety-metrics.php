<?php

declare(strict_types=1);

require_once __DIR__ . '/sweety-metrics-lib.php';

header('Content-Type: application/json; charset=utf-8');

const SWEETY_METRICS_MAX_BODY_BYTES = 1024;
const SWEETY_METRICS_MAX_DAILY_REGISTRATIONS = 1000;

function sweety_metrics_json_response(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function sweety_metrics_header(string $name): string
{
    $key = 'HTTP_' . strtoupper(str_replace('-', '_', $name));
    return trim((string) ($_SERVER[$key] ?? ''));
}

function sweety_metrics_database(): MysqliDb
{
    require_once __DIR__ . '/MysqliDb.php';

    if (!defined('SWEETY_MYSQL_CONFIG_ONLY')) {
        define('SWEETY_MYSQL_CONFIG_ONLY', true);
    }
    require __DIR__ . '/mysql.php';

    if (!isset($mysqlhost, $mysqluser, $mysqlpasswd, $mysqldb)) {
        throw new RuntimeException('Database configuration is unavailable.');
    }

    return new MysqliDb($mysqlhost, $mysqluser, $mysqlpasswd, $mysqldb, 3306, 'utf8mb4');
}

function sweety_metrics_assert_database_ok(MysqliDb $db): void
{
    $errorNumber = method_exists($db, 'getLastErrno') ? (int) $db->getLastErrno() : 0;
    $errorMessage = method_exists($db, 'getLastError') ? trim((string) $db->getLastError()) : '';
    if ($errorNumber !== 0 || $errorMessage !== '') {
        throw new RuntimeException('Database operation failed.');
    }
}

function sweety_metrics_rollback(MysqliDb $db): void
{
    try {
        $db->rollback();
    } catch (Throwable $ignored) {
    }
}

$method = (string) ($_SERVER['REQUEST_METHOD'] ?? 'GET');
if ($method !== 'GET' && $method !== 'POST') {
    header('Allow: GET, POST');
    header('Cache-Control: no-store');
    sweety_metrics_json_response(405, ['ok' => false, 'error' => 'method_not_allowed']);
}

if ($method === 'GET') {
    header('Cache-Control: public, max-age=60');

    try {
        $db = sweety_metrics_database();
        $rows = $db->rawQuery('SELECT total_hours FROM sweety_metrics_totals WHERE id = 1');
        sweety_metrics_assert_database_ok($db);
        if (!is_array($rows)) {
            throw new RuntimeException('Metrics query failed.');
        }

        if (!isset($rows[0]['total_hours'])) {
            throw new RuntimeException('Aggregate singleton is unavailable.');
        }
        $aggregateHours = sweety_metrics_parse_aggregate($rows[0]['total_hours']);
        if ($aggregateHours === null) {
            throw new RuntimeException('Aggregate total is out of range.');
        }
        $summary = sweety_metrics_summary($aggregateHours);
        sweety_metrics_json_response(200, $summary);
    } catch (Throwable $exception) {
        header('Cache-Control: no-store');
        sweety_metrics_json_response(500, ['ok' => false, 'error' => 'metrics_unavailable']);
    }
}

header('Cache-Control: no-store');

// This shared secret only bounds public write access; it is not installation identity.
$expectedToken = getenv('SWEETY_METRICS_APP_TOKEN');
$authorized = is_string($expectedToken) && sweety_metrics_is_authorized_post(
    $method,
    sweety_metrics_header('X-Sweety-App'),
    (string) ($_SERVER['HTTP_USER_AGENT'] ?? ''),
    $expectedToken,
    sweety_metrics_header('X-Sweety-App-Token')
);
if (!$authorized) {
    sweety_metrics_json_response(403, ['ok' => false, 'error' => 'forbidden']);
}

$contentLength = $_SERVER['CONTENT_LENGTH'] ?? null;
if ($contentLength !== null && ctype_digit((string) $contentLength) && (int) $contentLength > SWEETY_METRICS_MAX_BODY_BYTES) {
    sweety_metrics_json_response(413, ['ok' => false, 'error' => 'payload_too_large']);
}
$input = fopen('php://input', 'rb');
$rawBody = is_resource($input) ? fread($input, SWEETY_METRICS_MAX_BODY_BYTES + 1) : false;
if (is_resource($input)) {
    fclose($input);
}
if (!is_string($rawBody) || strlen($rawBody) > SWEETY_METRICS_MAX_BODY_BYTES) {
    sweety_metrics_json_response(413, ['ok' => false, 'error' => 'payload_too_large']);
}

$decoded = json_decode($rawBody, true);
$payload = json_last_error() === JSON_ERROR_NONE ? sweety_metrics_validate_payload($decoded) : null;
if ($payload === null) {
    sweety_metrics_json_response(400, ['ok' => false, 'error' => 'invalid_payload']);
}

$installationHash = sweety_metrics_installation_hash($payload['installationId']);
$reportedHours = $payload['totalHours'];
unset($payload);

$db = null;
$transactionStarted = false;
try {
    $db = sweety_metrics_database();
    $db->startTransaction();
    $transactionStarted = true;
    sweety_metrics_assert_database_ok($db);

    $rows = $db->rawQuery(
        'SELECT total_hours, baseline_hours, UNIX_TIMESTAMP(created_at) AS created_unix
         FROM sweety_install_metrics
         WHERE installation_hash = ?
         FOR UPDATE',
        [$installationHash]
    );
    sweety_metrics_assert_database_ok($db);
    if (!is_array($rows)) {
        throw new RuntimeException('Installation lookup failed.');
    }

    $existing = $rows[0] ?? null;
    $storedHours = is_array($existing) ? (int) $existing['total_hours'] : null;
    $baselineHours = is_array($existing) && isset($existing['baseline_hours'])
        ? sweety_metrics_parse_aggregate($existing['baseline_hours'])
        : null;
    $createdUnix = is_array($existing) && isset($existing['created_unix'])
        ? (int) $existing['created_unix']
        : null;
    $decision = sweety_metrics_growth_decision(
        $storedHours,
        $baselineHours,
        $createdUnix,
        $reportedHours,
        time()
    );
    if (!$decision['accepted']) {
        sweety_metrics_rollback($db);
        $transactionStarted = false;
        sweety_metrics_json_response(422, ['ok' => false, 'error' => 'metric_rejected']);
    }

    if ($existing === null) {
        $db->rawQuery(
            'INSERT INTO sweety_metrics_daily_registrations (registration_date, registration_count)
             VALUES (UTC_DATE(), 0)
             ON DUPLICATE KEY UPDATE registration_count = registration_count'
        );
        sweety_metrics_assert_database_ok($db);
        $dailyRows = $db->rawQuery(
            'SELECT registration_count
             FROM sweety_metrics_daily_registrations
             WHERE registration_date = UTC_DATE()
             FOR UPDATE'
        );
        sweety_metrics_assert_database_ok($db);
        if (!is_array($dailyRows) || !isset($dailyRows[0]['registration_count'])) {
            throw new RuntimeException('Daily registration counter is unavailable.');
        }
        if ((int) $dailyRows[0]['registration_count'] >= SWEETY_METRICS_MAX_DAILY_REGISTRATIONS) {
            sweety_metrics_rollback($db);
            $transactionStarted = false;
            sweety_metrics_json_response(429, ['ok' => false, 'error' => 'registration_limit']);
        }
        $db->rawQuery(
            'UPDATE sweety_metrics_daily_registrations
             SET registration_count = registration_count + 1
             WHERE registration_date = UTC_DATE()'
        );
        sweety_metrics_assert_database_ok($db);
        $db->rawQuery(
            'INSERT INTO sweety_install_metrics (installation_hash, total_hours, baseline_hours, created_at, updated_at)
             VALUES (?, ?, ?, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())',
            [$installationHash, $decision['total'], $decision['total']]
        );
        sweety_metrics_assert_database_ok($db);
    } elseif ($decision['delta'] > 0) {
        $db->rawQuery(
            'UPDATE sweety_install_metrics
             SET total_hours = ?, updated_at = CURRENT_TIMESTAMP()
             WHERE installation_hash = ?',
            [$decision['total'], $installationHash]
        );
        sweety_metrics_assert_database_ok($db);
    }

    if ($decision['delta'] > 0) {
        $totalRows = $db->rawQuery(
            'SELECT total_hours FROM sweety_metrics_totals WHERE id = 1 FOR UPDATE'
        );
        sweety_metrics_assert_database_ok($db);
        if (!is_array($totalRows) || !isset($totalRows[0]['total_hours'])) {
            throw new RuntimeException('Aggregate total is unavailable.');
        }
        $aggregateHours = sweety_metrics_parse_aggregate($totalRows[0]['total_hours']);
        if ($aggregateHours === null || $aggregateHours > PHP_INT_MAX - $decision['delta']) {
            throw new RuntimeException('Aggregate total is out of range.');
        }
        $db->rawQuery(
            'UPDATE sweety_metrics_totals SET total_hours = ? WHERE id = 1',
            [$aggregateHours + $decision['delta']]
        );
        sweety_metrics_assert_database_ok($db);
    }

    $commitResult = $db->commit();
    sweety_metrics_assert_database_ok($db);
    if ($commitResult === false) {
        throw new RuntimeException('Metrics commit failed.');
    }
    $transactionStarted = false;
    http_response_code(204);
    exit;
} catch (Throwable $exception) {
    if ($transactionStarted && $db instanceof MysqliDb) {
        sweety_metrics_rollback($db);
    }
    sweety_metrics_json_response(500, ['ok' => false, 'error' => 'metrics_unavailable']);
}
