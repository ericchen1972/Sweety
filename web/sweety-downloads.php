<?php

declare(strict_types=1);

require_once __DIR__ . '/sweety-downloads-lib.php';

header('Content-Type: application/json; charset=utf-8');

function sweety_downloads_json_response(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function sweety_downloads_database(): MysqliDb
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

function sweety_downloads_assert_database_ok(MysqliDb $db): void
{
    $errorNumber = method_exists($db, 'getLastErrno') ? (int) $db->getLastErrno() : 0;
    $errorMessage = method_exists($db, 'getLastError') ? trim((string) $db->getLastError()) : '';
    if ($errorNumber !== 0 || $errorMessage !== '') {
        throw new RuntimeException('Database operation failed.');
    }
}

function sweety_downloads_read_total(MysqliDb $db): int
{
    $rows = $db->rawQuery('SELECT total_downloads FROM sweety_download_totals WHERE id = 1');
    sweety_downloads_assert_database_ok($db);
    if (!is_array($rows) || !isset($rows[0]['total_downloads'])) {
        throw new RuntimeException('Download total is unavailable.');
    }
    $total = sweety_downloads_parse_total($rows[0]['total_downloads']);
    if ($total === null) {
        throw new RuntimeException('Download total is out of range.');
    }
    return $total;
}

$method = (string) ($_SERVER['REQUEST_METHOD'] ?? 'GET');
if ($method !== 'GET' && $method !== 'POST') {
    header('Allow: GET, POST');
    header('Cache-Control: no-store');
    sweety_downloads_json_response(405, ['ok' => false, 'error' => 'method_not_allowed']);
}

header($method === 'GET'
    ? 'Cache-Control: public, max-age=60'
    : 'Cache-Control: no-store');

try {
    $db = sweety_downloads_database();
    if ($method === 'POST') {
        $db->rawQuery(
            'UPDATE sweety_download_totals
             SET total_downloads = total_downloads + 1
             WHERE id = 1'
        );
        sweety_downloads_assert_database_ok($db);
    }
    sweety_downloads_json_response(200, [
        'totalDownloads' => sweety_downloads_read_total($db),
    ]);
} catch (Throwable $exception) {
    header('Cache-Control: no-store');
    sweety_downloads_json_response(500, ['ok' => false, 'error' => 'downloads_unavailable']);
}
