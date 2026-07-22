<?php

declare(strict_types=1);

$root = dirname(__DIR__, 2);
$libraryPath = $root . '/web/sweety-metrics-lib.php';
$endpointPath = $root . '/web/sweety-metrics.php';
$migrationPath = $root . '/app/tools/sweety_metrics.sql';
$failures = [];
$assertions = 0;

function check(bool $condition, string $message): void
{
    global $assertions, $failures;
    $assertions++;
    if (!$condition) {
        $failures[] = $message;
    }
}

function check_same(mixed $expected, mixed $actual, string $message): void
{
    check($expected === $actual, $message . ' (expected ' . var_export($expected, true) . ', got ' . var_export($actual, true) . ')');
}

check(is_file($libraryPath), 'metrics helper library exists');
check(is_file($endpointPath), 'metrics endpoint exists');
check(is_file($migrationPath), 'metrics migration exists');

if (is_file($libraryPath)) {
    require_once $libraryPath;
}

$requiredFunctions = [
    'sweety_metrics_summary',
    'sweety_metrics_is_valid_installation_id',
    'sweety_metrics_validate_payload',
    'sweety_metrics_is_authorized_post',
    'sweety_metrics_installation_hash',
    'sweety_metrics_monotonic_total',
];
foreach ($requiredFunctions as $function) {
    check(function_exists($function), "helper {$function} exists");
}

if (function_exists('sweety_metrics_summary')) {
    check_same(['totalDays' => 0, 'totalHours' => 0], sweety_metrics_summary(0), 'zero hours summary');
    check_same(['totalDays' => 0, 'totalHours' => 23], sweety_metrics_summary(23), '23 hours summary');
    check_same(['totalDays' => 1, 'totalHours' => 0], sweety_metrics_summary(24), '24 hours summary');
    check_same(['totalDays' => 2, 'totalHours' => 5], sweety_metrics_summary(53), '53 hours summary');
}

$validUuid = '123e4567-e89b-12d3-a456-426614174000';
if (function_exists('sweety_metrics_is_valid_installation_id')) {
    check(sweety_metrics_is_valid_installation_id($validUuid), 'canonical UUID is valid');
    check(sweety_metrics_is_valid_installation_id(strtoupper($validUuid)), 'uppercase canonical UUID is valid');
    foreach (['', '123e4567e89b12d3a456426614174000', '123e4567-e89b-12d3-a456-42661417400z', $validUuid . '0', 123] as $invalid) {
        check(!sweety_metrics_is_valid_installation_id($invalid), 'invalid installation ID is rejected');
    }
}

if (function_exists('sweety_metrics_validate_payload')) {
    check_same(
        ['installationId' => $validUuid, 'totalHours' => 53],
        sweety_metrics_validate_payload(['installationId' => $validUuid, 'totalHours' => 53]),
        'valid payload is accepted'
    );
    check_same(
        ['installationId' => $validUuid, 'totalHours' => 53],
        sweety_metrics_validate_payload(['totalHours' => 53, 'installationId' => $validUuid]),
        'JSON object field order does not affect validation'
    );
    foreach ([
        null,
        [],
        ['installationId' => $validUuid],
        ['installationId' => $validUuid, 'totalHours' => -1],
        ['installationId' => $validUuid, 'totalHours' => 1000001],
        ['installationId' => $validUuid, 'totalHours' => '53'],
        ['installationId' => 'not-a-uuid', 'totalHours' => 53],
        ['installationId' => $validUuid, 'totalHours' => 53, 'extra' => true],
    ] as $invalidPayload) {
        check_same(null, sweety_metrics_validate_payload($invalidPayload), 'malformed payload is rejected');
    }
}

if (function_exists('sweety_metrics_installation_hash')) {
    $hash = sweety_metrics_installation_hash($validUuid);
    check_same(64, strlen($hash), 'installation hash is 64 characters');
    check_same(hash('sha256', $validUuid), $hash, 'installation hash uses SHA-256');
    check($hash !== $validUuid, 'installation hash does not expose raw ID');
    check_same($hash, sweety_metrics_installation_hash(strtoupper($validUuid)), 'UUID case variants deduplicate to one hash');
}

if (function_exists('sweety_metrics_monotonic_total')) {
    check_same(20, sweety_metrics_monotonic_total(20, 10), 'stored total cannot decrease');
    check_same(30, sweety_metrics_monotonic_total(20, 30), 'stored total can advance');
}

check(function_exists('sweety_metrics_growth_decision'), 'growth decision helper exists');
if (function_exists('sweety_metrics_growth_decision')) {
    $now = 2000000000;
    check_same(['accepted' => true, 'total' => 24, 'delta' => 24], sweety_metrics_growth_decision(null, null, null, 24, $now), 'new installation may initially report 24 hours');
    check_same(['accepted' => false, 'total' => 25, 'delta' => 0], sweety_metrics_growth_decision(null, null, null, 25, $now), 'new installation may not initially report over 24 hours');
    check_same(['accepted' => true, 'total' => 24, 'delta' => 0], sweety_metrics_growth_decision(24, 24, $now, 23, $now), 'lower repeated report is accepted without decrement');
    check_same(['accepted' => true, 'total' => 24, 'delta' => 0], sweety_metrics_growth_decision(24, 24, $now, 24, $now), 'unchanged report is accepted without increment');
    check_same(['accepted' => true, 'total' => 26, 'delta' => 2], sweety_metrics_growth_decision(24, 24, $now, 26, $now), 'installation may consume fixed two-hour grace once');
    check_same(['accepted' => false, 'total' => 28, 'delta' => 0], sweety_metrics_growth_decision(26, 24, $now, 28, $now), 'fixed grace cannot be consumed repeatedly at one timestamp');
    check_same(['accepted' => true, 'total' => 29, 'delta' => 5], sweety_metrics_growth_decision(24, 24, $now - 10800, 29, $now), 'baseline plus created-age whole hours and grace are accepted');
    check_same(['accepted' => false, 'total' => 30, 'delta' => 0], sweety_metrics_growth_decision(24, 24, $now - 10800, 30, $now), 'growth beyond baseline-age ceiling is rejected');
    check_same(['accepted' => true, 'total' => 102, 'delta' => 2], sweety_metrics_growth_decision(100, 100, $now, 102, $now), 'legacy baseline permits two-hour grace without date backdating');
    check_same(['accepted' => false, 'total' => 103, 'delta' => 0], sweety_metrics_growth_decision(102, 100, $now, 103, $now), 'legacy baseline grace cannot repeat immediately');
    check_same(['accepted' => false, 'total' => 25, 'delta' => 0], sweety_metrics_growth_decision(24, null, $now, 25, $now), 'missing baseline fails closed');
    check_same(['accepted' => false, 'total' => 25, 'delta' => 0], sweety_metrics_growth_decision(24, 24, null, 25, $now), 'missing creation timestamp fails closed');
    check_same(['accepted' => true, 'total' => 1000000, 'delta' => 0], sweety_metrics_growth_decision(1000000, 1000000, $now, 1000000, $now), 'maximum legacy baseline remains within cap without old dates');
}
check(function_exists('sweety_metrics_parse_aggregate'), 'aggregate parser helper exists');
if (function_exists('sweety_metrics_parse_aggregate')) {
    check_same(53, sweety_metrics_parse_aggregate('53'), 'aggregate parser accepts non-negative database integer strings');
    check_same(PHP_INT_MAX, sweety_metrics_parse_aggregate((string) PHP_INT_MAX), 'aggregate parser accepts PHP integer maximum');
    check_same(null, sweety_metrics_parse_aggregate('18446744073709551615'), 'aggregate parser rejects unsigned BIGINT beyond PHP range');
    check_same(null, sweety_metrics_parse_aggregate('-1'), 'aggregate parser rejects negative totals');
}

if (function_exists('sweety_metrics_is_authorized_post')) {
    check(sweety_metrics_is_authorized_post('POST', 'desktop', 'SweetyApp/1.0', 'secret', 'secret'), 'desktop POST with matching token is authorized');
    check(!sweety_metrics_is_authorized_post('GET', 'desktop', 'SweetyApp/1.0', 'secret', 'secret'), 'GET cannot use desktop write authorization');
    check(!sweety_metrics_is_authorized_post('POST', 'browser', 'SweetyApp/1.0', 'secret', 'secret'), 'browser cannot write');
    check(!sweety_metrics_is_authorized_post('POST', 'desktop', 'Mozilla/5.0', 'secret', 'secret'), 'non-app user agent cannot write');
    check(!sweety_metrics_is_authorized_post('POST', 'desktop', 'SweetyApp/1.0', 'secret', 'wrong'), 'wrong token cannot write');
    check(!sweety_metrics_is_authorized_post('POST', 'desktop', 'SweetyApp/1.0', '', ''), 'empty configured token cannot authorize');
}

$endpoint = is_file($endpointPath) ? (string) file_get_contents($endpointPath) : '';
check(str_contains($endpoint, "header('Content-Type: application/json; charset=utf-8')"), 'endpoint sets UTF-8 JSON content type');
check((bool) preg_match("/Cache-Control:\\s*public,\\s*max-age=60/", $endpoint), 'GET has a short public cache window');
check(str_contains($endpoint, "header('Cache-Control: no-store')"), 'POST uses no-store');
check(str_contains($endpoint, "http_response_code(204)"), 'POST success is 204');
check(str_contains($endpoint, '405'), 'unsupported methods return 405');
check(str_contains($endpoint, '403'), 'unauthorized writes return 403');
check(str_contains($endpoint, '400'), 'malformed payloads return 400');
check(str_contains($endpoint, '500'), 'database failures return 500');
check(str_contains($endpoint, "require_once __DIR__ . '/MysqliDb.php'"), 'endpoint uses existing MysqliDb dependency');
check(str_contains($endpoint, "require __DIR__ . '/mysql.php'"), 'endpoint uses existing mysql configuration');
check(!str_contains($endpoint, 'REMOTE_ADDR'), 'endpoint never reads or stores the client IP');
check(!str_contains($endpoint, 'sweety-desktop-catalog-v1'), 'endpoint contains no committed fallback write token');
check(str_contains($endpoint, "getenv('SWEETY_METRICS_APP_TOKEN')"), 'endpoint uses dedicated metrics token environment variable');
check(!str_contains($endpoint, 'UTC_TIMESTAMP()'), 'endpoint never writes TIMESTAMP columns with explicit UTC values');
check(str_contains($endpoint, 'CURRENT_TIMESTAMP()'), 'endpoint writes TIMESTAMP columns in the database session timezone');
check(str_contains($endpoint, 'UNIX_TIMESTAMP(created_at)'), 'growth reads timezone-independent created epoch');

$migration = is_file($migrationPath) ? (string) file_get_contents($migrationPath) : '';
check((bool) preg_match('/CREATE TABLE(?: IF NOT EXISTS)? sweety_install_metrics/i', $migration), 'migration creates metrics table');
check((bool) preg_match('/installation_hash\s+CHAR\(64\)\s+NOT NULL\s+PRIMARY KEY/i', $migration), 'hashed installation ID is the primary key');
check((bool) preg_match('/total_hours\s+INT\s+UNSIGNED\s+NOT NULL/i', $migration), 'total hours is unsigned integer');
check((bool) preg_match('/updated_at\s+TIMESTAMP/i', $migration), 'migration tracks updated_at');
check((bool) preg_match('/created_at\s+TIMESTAMP/i', $migration), 'migration tracks installation creation time');
check((bool) preg_match('/baseline_hours\s+BIGINT\s+UNSIGNED\s+NOT NULL/i', $migration), 'migration stores immutable unsigned baseline hours');
check((bool) preg_match('/INDEX[^\n]*created_at/i', $migration), 'migration indexes installation creation time');
check(str_contains($migration, 'information_schema.columns'), 'migration upgrades an existing metrics table with created_at');
check(str_contains($migration, 'information_schema.statistics'), 'migration upgrades an existing metrics table with created_at index');
check(str_contains($migration, "column_name = 'baseline_hours'"), 'migration detects whether baseline existed before upgrade');
check((bool) preg_match('/ADD COLUMN baseline_hours BIGINT UNSIGNED NULL DEFAULT NULL AFTER total_hours/i', $migration), 'interrupted upgrade adds nullable baseline sentinel');
check((bool) preg_match('/SET\s+baseline_hours\s*=\s*total_hours,\s*created_at\s*=\s*CURRENT_TIMESTAMP\(\)\s*WHERE\s+baseline_hours\s+IS\s+NULL/i', $migration), 'every rerun recovers all null legacy baselines with session-correct timestamp');
check_same(1, substr_count($migration, 'WHERE baseline_hours IS NULL'), 'baseline zero is never used as upgrade sentinel');
check((bool) preg_match('/MODIFY COLUMN baseline_hours BIGINT UNSIGNED NOT NULL DEFAULT 0/i', $migration), 'upgrade seals baseline non-null after recovery');
$baselineBackfillPosition = strpos($migration, 'WHERE baseline_hours IS NULL');
$baselineNotNullPosition = strpos($migration, 'MODIFY COLUMN baseline_hours');
check($baselineBackfillPosition !== false && $baselineNotNullPosition !== false && $baselineBackfillPosition < $baselineNotNullPosition, 'interrupted migration always recovers nulls before enforcing NOT NULL');
check(!str_contains($migration, '@sweety_backfill_baseline_sql'), 'baseline recovery is not skipped merely because DDL previously autocommitted');
check(!str_contains($migration, 'UTC_TIMESTAMP()'), 'migration never explicitly writes UTC into TIMESTAMP columns');
check(!str_contains($migration, 'DATE_SUB('), 'migration never backdates timestamps outside TIMESTAMP range');
check((bool) preg_match('/CREATE TABLE(?: IF NOT EXISTS)? sweety_metrics_totals/i', $migration), 'migration creates aggregate singleton table');
check((bool) preg_match('/total_hours\s+BIGINT\s+UNSIGNED/i', $migration), 'aggregate total uses unsigned BIGINT');
check((bool) preg_match('/INSERT INTO sweety_metrics_totals[\s\S]*SELECT\s+1\s*,\s*COALESCE\(SUM\(total_hours\),\s*0\)[\s\S]*FROM sweety_install_metrics/i', $migration), 'migration backfills singleton from existing installation totals');
check((bool) preg_match('/CREATE TABLE(?: IF NOT EXISTS)? sweety_metrics_daily_registrations/i', $migration), 'migration creates UTC daily registration counter');
check(!str_contains($migration, 'installation_id'), 'migration does not store raw installation ID');

function test_http_request(int $port, string $method, string $mode, string $body = '', array $headers = []): array
{
    $requestHeaders = array_merge(['X-Test-Db-Mode: ' . $mode], $headers);
    $context = stream_context_create([
        'http' => [
            'method' => $method,
            'header' => implode("\r\n", $requestHeaders),
            'content' => $body,
            'ignore_errors' => true,
            'timeout' => 5,
        ],
    ]);
    $responseBody = file_get_contents("http://127.0.0.1:{$port}/sweety-metrics.php", false, $context);
    $responseHeaders = $http_response_header ?? [];
    $status = 0;
    $parsedHeaders = [];
    foreach ($responseHeaders as $line) {
        if (preg_match('/^HTTP\/\S+\s+(\d{3})/', $line, $matches)) {
            $status = (int) $matches[1];
            continue;
        }
        $separator = strpos($line, ':');
        if ($separator !== false) {
            $parsedHeaders[strtolower(substr($line, 0, $separator))] = trim(substr($line, $separator + 1));
        }
    }

    return ['status' => $status, 'headers' => $parsedHeaders, 'body' => $responseBody === false ? '' : $responseBody];
}

function test_header(array $response, string $name): string
{
    return (string) ($response['headers'][strtolower($name)] ?? '');
}

function test_remove_tree(string $directory): void
{
    if (!is_dir($directory)) {
        return;
    }
    foreach (scandir($directory) ?: [] as $entry) {
        if ($entry !== '.' && $entry !== '..') {
            $path = $directory . '/' . $entry;
            is_dir($path) ? test_remove_tree($path) : unlink($path);
        }
    }
    rmdir($directory);
}

$fixtureDirectory = sys_get_temp_dir() . '/sweety-metrics-' . getmypid() . '-' . bin2hex(random_bytes(4));
$capturePath = $fixtureDirectory . '/query.json';
$statePath = $fixtureDirectory . '/state.json';
$serverLog = $fixtureDirectory . '/server.log';
$server = null;

try {
    mkdir($fixtureDirectory, 0700, true);
    copy($libraryPath, $fixtureDirectory . '/sweety-metrics-lib.php');
    copy($endpointPath, $fixtureDirectory . '/sweety-metrics.php');
    file_put_contents($fixtureDirectory . '/mysql.php', "<?php\n\$mysqlhost = 'fake';\n\$mysqluser = 'fake';\n\$mysqlpasswd = 'fake';\n\$mysqldb = 'fake';\n");

    $fakeDatabase = <<<'PHP'
<?php
class MysqliDb
{
    private int $lastErrno = 0;
    private string $lastError = '';
    private ?array $transactionSnapshot = null;

    public function __construct(...$arguments) {}

    public function startTransaction(): bool
    {
        $this->transactionSnapshot = is_file(__STATE_PATH__)
            ? json_decode((string) file_get_contents(__STATE_PATH__), true)
            : [];
        return true;
    }

    public function commit(): bool
    {
        $this->transactionSnapshot = null;
        return true;
    }

    public function rollback(): bool
    {
        if ($this->transactionSnapshot !== null) {
            file_put_contents(__STATE_PATH__, json_encode($this->transactionSnapshot));
            $this->transactionSnapshot = null;
        }
        return true;
    }

    public function getLastErrno(): int
    {
        return $this->lastErrno;
    }

    public function getLastError(): string
    {
        return $this->lastError;
    }

    public function rawQuery(string $sql, array $parameters = []): array|bool
    {
        $this->lastErrno = 0;
        $this->lastError = '';
        $mode = (string) ($_SERVER['HTTP_X_TEST_DB_MODE'] ?? 'empty');
        $capture = is_file(__CAPTURE_PATH__) ? json_decode((string) file_get_contents(__CAPTURE_PATH__), true) : [];
        $capture[] = ['mode' => $mode, 'sql' => $sql, 'params' => $parameters];
        file_put_contents(__CAPTURE_PATH__, json_encode($capture));
        $upperSql = strtoupper($sql);
        $injectedWriteFailure = ($mode === 'install-write-failure' && str_contains($upperSql, 'INSERT INTO SWEETY_INSTALL_METRICS'))
            || ($mode === 'daily-write-failure' && str_contains($upperSql, 'UPDATE SWEETY_METRICS_DAILY_REGISTRATIONS'))
            || ($mode === 'singleton-write-failure' && str_contains($upperSql, 'UPDATE SWEETY_METRICS_TOTALS'));
        if ($mode === 'failure' || $injectedWriteFailure) {
            $this->lastErrno = 1205;
            $this->lastError = 'internal-db-secret: raw installation data must never leak';
            return false;
        }

        $states = is_file(__STATE_PATH__) ? json_decode((string) file_get_contents(__STATE_PATH__), true) : [];
        $state = $states[$mode] ?? ['installs' => [], 'total' => 0, 'daily' => 0];
        $normalized = strtoupper((string) preg_replace('/\s+/', ' ', trim($sql)));

        if (str_contains($normalized, 'FROM SWEETY_INSTALL_METRICS') && str_contains($normalized, 'FOR UPDATE')) {
            $hash = (string) ($parameters[0] ?? '');
            if (!isset($state['installs'][$hash]) && $mode === 'existing-growth') {
                $state['installs'][$hash] = ['total_hours' => 24, 'baseline_hours' => 24, 'created_unix' => time()];
            } elseif (!isset($state['installs'][$hash]) && $mode === 'legacy-baseline') {
                $state['installs'][$hash] = ['total_hours' => 100, 'baseline_hours' => 100, 'created_unix' => time()];
            } elseif (!isset($state['installs'][$hash]) && $mode === 'legacy-max') {
                $state['installs'][$hash] = ['total_hours' => 1000000, 'baseline_hours' => 1000000, 'created_unix' => time()];
            } elseif (!isset($state['installs'][$hash]) && $mode === 'timezone-sensitive') {
                $state['installs'][$hash] = ['total_hours' => 24, 'baseline_hours' => 24, 'created_unix' => time() - 3600];
            }
            $states[$mode] = $state;
            file_put_contents(__STATE_PATH__, json_encode($states));
            return isset($state['installs'][$hash]) ? [$state['installs'][$hash]] : [];
        }
        if (str_starts_with($normalized, 'SELECT TOTAL_HOURS FROM SWEETY_METRICS_TOTALS')) {
            if (!str_contains($normalized, 'FOR UPDATE')) {
                if ($mode === 'empty') {
                    return [];
                }
                if ($mode === '53') {
                    return [['total_hours' => 53]];
                }
                if ($mode === 'aggregate-overflow') {
                    return [['total_hours' => '18446744073709551615']];
                }
            }
            return [['total_hours' => (int) ($state['total'] ?? 0)]];
        }
        if (str_starts_with($normalized, 'INSERT INTO SWEETY_METRICS_DAILY_REGISTRATIONS')) {
            return true;
        }
        if (str_starts_with($normalized, 'SELECT REGISTRATION_COUNT')) {
            return [['registration_count' => $mode === 'daily-cap' ? 1000 : (int) ($state['daily'] ?? 0)]];
        }
        if (str_starts_with($normalized, 'UPDATE SWEETY_METRICS_DAILY_REGISTRATIONS')) {
            $state['daily'] = (int) ($state['daily'] ?? 0) + 1;
        } elseif (str_starts_with($normalized, 'INSERT INTO SWEETY_INSTALL_METRICS')) {
            $state['installs'][(string) $parameters[0]] = ['total_hours' => (int) $parameters[1], 'baseline_hours' => (int) $parameters[2], 'created_unix' => time()];
        } elseif (str_starts_with($normalized, 'UPDATE SWEETY_INSTALL_METRICS')) {
            $existingInstall = $state['installs'][(string) $parameters[1]] ?? ['created_unix' => time()];
            $existingInstall['total_hours'] = (int) $parameters[0];
            $state['installs'][(string) $parameters[1]] = $existingInstall;
        } elseif (str_starts_with($normalized, 'UPDATE SWEETY_METRICS_TOTALS')) {
            $state['total'] = (int) $parameters[0];
        }
        $states[$mode] = $state;
        file_put_contents(__STATE_PATH__, json_encode($states));
        return true;
    }
}
PHP;
    file_put_contents(
        $fixtureDirectory . '/MysqliDb.php',
        str_replace(
            ['__CAPTURE_PATH__', '__STATE_PATH__'],
            [var_export($capturePath, true), var_export($statePath, true)],
            $fakeDatabase
        )
    );
    file_put_contents($fixtureDirectory . '/router.php', <<<'PHP'
<?php
if (($_SERVER['HTTP_X_TEST_NO_TOKEN'] ?? '') === '1') {
    putenv('SWEETY_METRICS_APP_TOKEN=');
    putenv('SWEETY_APP_TOKEN=');
} elseif (($_SERVER['HTTP_X_TEST_LEGACY_TOKEN_ONLY'] ?? '') === '1') {
    putenv('SWEETY_METRICS_APP_TOKEN=');
    putenv('SWEETY_APP_TOKEN=isolated-test-token');
} else {
    putenv('SWEETY_METRICS_APP_TOKEN=isolated-test-token');
    putenv('SWEETY_APP_TOKEN=isolated-test-token');
}
require __DIR__ . '/sweety-metrics.php';
PHP);

    $socket = stream_socket_server('tcp://127.0.0.1:0', $errorNumber, $errorMessage);
    if ($socket === false) {
        throw new RuntimeException("Unable to allocate test port: {$errorMessage}");
    }
    $socketName = stream_socket_get_name($socket, false);
    fclose($socket);
    $port = (int) substr((string) $socketName, strrpos((string) $socketName, ':') + 1);

    $descriptors = [
        0 => ['pipe', 'r'],
        1 => ['file', $serverLog, 'a'],
        2 => ['file', $serverLog, 'a'],
    ];
    $server = proc_open(
        [PHP_BINARY, '-S', "127.0.0.1:{$port}", '-t', $fixtureDirectory, $fixtureDirectory . '/router.php'],
        $descriptors,
        $serverPipes,
        null,
        []
    );
    if (!is_resource($server)) {
        throw new RuntimeException('Unable to start isolated PHP server.');
    }
    fclose($serverPipes[0]);
    $ready = false;
    for ($attempt = 0; $attempt < 50; $attempt++) {
        $connection = @fsockopen('127.0.0.1', $port, $socketError, $socketErrorMessage, 0.1);
        if (is_resource($connection)) {
            fclose($connection);
            $ready = true;
            break;
        }
        usleep(20000);
    }
    if (!$ready) {
        throw new RuntimeException('Isolated PHP server did not become ready.');
    }

    $response = test_http_request($port, 'PUT', 'empty');
    check_same(405, $response['status'], 'unsupported method returns HTTP 405');
    check_same('{"ok":false,"error":"method_not_allowed"}', $response['body'], 'unsupported method returns generic JSON');
    check_same('GET, POST', test_header($response, 'Allow'), 'unsupported method advertises allowed methods');
    check_same('no-store', test_header($response, 'Cache-Control'), 'unsupported method is not cached');

    $response = test_http_request($port, 'POST', 'empty', '{}', ['Content-Type: application/json']);
    check_same(403, $response['status'], 'unauthorized POST returns HTTP 403');
    check_same('{"ok":false,"error":"forbidden"}', $response['body'], 'unauthorized POST returns generic JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'unauthorized POST is not cached');

    $authorizedHeaders = [
        'Content-Type: application/json',
        'X-Sweety-App: desktop',
        'User-Agent: SweetyApp/1.0',
        'X-Sweety-App-Token: isolated-test-token',
    ];
    $response = test_http_request($port, 'POST', 'empty', '{', $authorizedHeaders);
    check_same(400, $response['status'], 'authorized malformed POST returns HTTP 400');
    check_same('{"ok":false,"error":"invalid_payload"}', $response['body'], 'malformed POST returns generic JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'malformed POST is not cached');

    $missingTokenHeaders = array_merge($authorizedHeaders, ['X-Test-No-Token: 1']);
    $response = test_http_request($port, 'POST', 'empty', (string) json_encode(['installationId' => $validUuid, 'totalHours' => 1]), $missingTokenHeaders);
    check_same(403, $response['status'], 'POST fails closed when dedicated server token is missing');
    check_same('{"ok":false,"error":"forbidden"}', $response['body'], 'missing server token returns generic forbidden JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'missing-token POST is not cached');

    $legacyOnlyHeaders = array_merge($authorizedHeaders, ['X-Test-Legacy-Token-Only: 1']);
    $response = test_http_request($port, 'POST', 'empty', (string) json_encode(['installationId' => $validUuid, 'totalHours' => 1]), $legacyOnlyHeaders);
    check_same(403, $response['status'], 'legacy shared app token environment variable cannot authorize metrics writes');

    $response = test_http_request($port, 'POST', 'empty', str_repeat('x', 1025), $authorizedHeaders);
    check_same(413, $response['status'], 'oversized POST returns HTTP 413');
    check_same('{"ok":false,"error":"payload_too_large"}', $response['body'], 'oversized POST returns generic JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'oversized POST is not cached');

    foreach (['zero'] as $mode) {
        $response = test_http_request($port, 'GET', $mode);
        check_same(200, $response['status'], "{$mode} aggregate returns HTTP 200");
        check_same('{"totalDays":0,"totalHours":0}', $response['body'], "{$mode} aggregate returns exact zero shape");
        check_same('public, max-age=60', test_header($response, 'Cache-Control'), "{$mode} aggregate uses public cache");
    }
    $response = test_http_request($port, 'GET', 'empty');
    check_same(500, $response['status'], 'missing aggregate singleton row returns HTTP 500');
    check_same('{"ok":false,"error":"metrics_unavailable"}', $response['body'], 'missing aggregate singleton returns generic unavailable JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'missing aggregate singleton is not cached');
    $response = test_http_request($port, 'GET', '53');
    check_same(200, $response['status'], '53-hour aggregate returns HTTP 200');
    check_same('{"totalDays":2,"totalHours":5}', $response['body'], '53-hour aggregate returns exact split shape');
    check_same('public, max-age=60', test_header($response, 'Cache-Control'), 'successful aggregate uses public cache');
    check_same('application/json; charset=utf-8', test_header($response, 'Content-Type'), 'successful aggregate uses UTF-8 JSON');

    $response = test_http_request($port, 'GET', 'aggregate-overflow');
    check_same(500, $response['status'], 'out-of-range aggregate returns HTTP 500');
    check_same('{"ok":false,"error":"metrics_unavailable"}', $response['body'], 'out-of-range aggregate returns generic unavailable JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'out-of-range aggregate is not cached');

    $postBody = json_encode(['installationId' => $validUuid, 'totalHours' => 20]);
    $response = test_http_request($port, 'POST', 'capture', (string) $postBody, $authorizedHeaders);
    check_same(204, $response['status'], 'valid authorized POST returns HTTP 204');
    check_same('', $response['body'], 'successful POST has no body');
    check_same('no-store', test_header($response, 'Cache-Control'), 'successful POST is not cached');
    $capture = json_decode((string) file_get_contents($capturePath), true);
    check(is_array($capture), 'fake database captured write transaction queries');
    $installQueries = array_values(array_filter($capture, fn (array $item): bool => str_contains($item['sql'], 'INSERT INTO sweety_install_metrics')));
    check_same([hash('sha256', strtolower($validUuid)), 20, 20], $installQueries[0]['params'] ?? null, 'write parameters contain normalized hash, total, and immutable initial baseline');
    check(str_contains((string) ($installQueries[0]['sql'] ?? ''), 'VALUES (?, ?, ?, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())'), 'installation write query uses parameterization and session-correct TIMESTAMP values');
    check((bool) array_filter($capture, fn (array $item): bool => str_contains($item['sql'], 'FOR UPDATE')), 'write transaction uses locking reads');
    check(!str_contains((string) json_encode($capture), $validUuid), 'raw installation ID is absent from SQL');
    check(!str_contains((string) file_get_contents($capturePath), $validUuid), 'raw installation ID is absent from captured database call');

    $response = test_http_request(
        $port,
        'POST',
        'new-growth-cap',
        (string) json_encode(['installationId' => $validUuid, 'totalHours' => 25]),
        $authorizedHeaders
    );
    check_same(422, $response['status'], 'new installation over 24 hours is rejected');
    check_same('{"ok":false,"error":"metric_rejected"}', $response['body'], 'new-install anomaly returns generic JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'new-install anomaly is not cached');

    $response = test_http_request(
        $port,
        'POST',
        'existing-growth',
        (string) json_encode(['installationId' => $validUuid, 'totalHours' => 27]),
        $authorizedHeaders
    );
    check_same(422, $response['status'], 'existing installation jump beyond grace is rejected');
    $response = test_http_request(
        $port,
        'POST',
        'existing-growth',
        (string) json_encode(['installationId' => $validUuid, 'totalHours' => 26]),
        $authorizedHeaders
    );
    check_same(204, $response['status'], 'existing installation growth within grace is accepted');

    $createdAtAfterFirstReport = null;
    foreach ([24 => 204, 26 => 204, 28 => 422] as $reportedTotal => $expectedStatus) {
        $response = test_http_request(
            $port,
            'POST',
            'repeat-grace-attack',
            (string) json_encode(['installationId' => $validUuid, 'totalHours' => $reportedTotal]),
            $authorizedHeaders
        );
        check_same($expectedStatus, $response['status'], "repeat-grace report {$reportedTotal} has bounded status");
        if ($reportedTotal === 24) {
            $states = json_decode((string) file_get_contents($statePath), true);
            $firstInstall = array_values($states['repeat-grace-attack']['installs'] ?? [])[0] ?? [];
            $createdAtAfterFirstReport = $firstInstall['created_unix'] ?? null;
        }
    }
    $states = json_decode((string) file_get_contents($statePath), true);
    check_same(26, $states['repeat-grace-attack']['total'] ?? null, 'repeat grace attack contributes at most fixed ceiling');
    $repeatInstall = array_values($states['repeat-grace-attack']['installs'] ?? [])[0] ?? [];
    check(isset($repeatInstall['created_unix']), 'installation creation timestamp remains present');
    check_same($createdAtAfterFirstReport, $repeatInstall['created_unix'] ?? null, 'installation creation timestamp is immutable across accepted growth');
    check_same(24, $repeatInstall['baseline_hours'] ?? null, 'installation baseline remains its immutable first report');

    foreach ([102 => 204, 103 => 422] as $reportedTotal => $expectedStatus) {
        $response = test_http_request(
            $port,
            'POST',
            'legacy-baseline',
            (string) json_encode(['installationId' => $validUuid, 'totalHours' => $reportedTotal]),
            $authorizedHeaders
        );
        check_same($expectedStatus, $response['status'], "legacy baseline report {$reportedTotal} has bounded status");
    }
    $states = json_decode((string) file_get_contents($statePath), true);
    $legacyInstall = array_values($states['legacy-baseline']['installs'] ?? [])[0] ?? [];
    check_same(100, $legacyInstall['baseline_hours'] ?? null, 'legacy baseline remains immutable after accepted growth');
    check(($legacyInstall['created_unix'] ?? 0) > 0, 'legacy baseline uses an in-range current timestamp');

    $response = test_http_request(
        $port,
        'POST',
        'legacy-max',
        (string) json_encode(['installationId' => $validUuid, 'totalHours' => 1000000]),
        $authorizedHeaders
    );
    check_same(204, $response['status'], 'legacy one-million-hour row remains valid without timestamp backdating');
    $states = json_decode((string) file_get_contents($statePath), true);
    $maxInstall = array_values($states['legacy-max']['installs'] ?? [])[0] ?? [];
    check_same(1000000, $maxInstall['baseline_hours'] ?? null, 'legacy maximum baseline is preserved');
    check(($maxInstall['created_unix'] ?? 0) > 0, 'legacy maximum uses an in-range current timestamp');

    foreach ([27 => 204, 28 => 422] as $reportedTotal => $expectedStatus) {
        $response = test_http_request(
            $port,
            'POST',
            'timezone-sensitive',
            (string) json_encode(['installationId' => $validUuid, 'totalHours' => $reportedTotal]),
            $authorizedHeaders
        );
        check_same($expectedStatus, $response['status'], "epoch-based growth remains stable across session timezone for {$reportedTotal}");
    }

    $response = test_http_request(
        $port,
        'POST',
        'daily-cap',
        (string) json_encode(['installationId' => $validUuid, 'totalHours' => 1]),
        $authorizedHeaders
    );
    check_same(429, $response['status'], 'UTC daily new-installation cap returns HTTP 429');
    check_same('{"ok":false,"error":"registration_limit"}', $response['body'], 'daily cap returns generic JSON');
    check_same('no-store', test_header($response, 'Cache-Control'), 'daily cap rejection is not cached');

    $caseUuid = strtoupper($validUuid);
    foreach ([$caseUuid, strtolower($caseUuid)] as $caseVariant) {
        $response = test_http_request(
            $port,
            'POST',
            'case-dedupe',
            (string) json_encode(['installationId' => $caseVariant, 'totalHours' => 10]),
            $authorizedHeaders
        );
        check_same(204, $response['status'], 'UUID case variant is accepted');
    }
    $states = json_decode((string) file_get_contents($statePath), true);
    check_same(1, count($states['case-dedupe']['installs'] ?? []), 'UUID case variants create one installation row');
    check_same(1, $states['case-dedupe']['daily'] ?? null, 'UUID case variants consume one daily registration');
    check_same(10, $states['case-dedupe']['total'] ?? null, 'UUID case variants contribute once to aggregate');

    foreach ([20, 20, 22] as $reportedTotal) {
        $response = test_http_request(
            $port,
            'POST',
            'aggregate-flow',
            (string) json_encode(['installationId' => $validUuid, 'totalHours' => $reportedTotal]),
            $authorizedHeaders
        );
        check_same(204, $response['status'], "aggregate-flow report {$reportedTotal} is accepted");
    }
    $response = test_http_request($port, 'GET', 'aggregate-flow');
    check_same(200, $response['status'], 'singleton aggregate GET succeeds after delta updates');
    check_same('{"totalDays":0,"totalHours":22}', $response['body'], 'singleton total increments only by accepted deltas');

    foreach (['daily-write-failure', 'install-write-failure', 'singleton-write-failure'] as $failureMode) {
        $response = test_http_request(
            $port,
            'POST',
            $failureMode,
            (string) json_encode(['installationId' => $validUuid, 'totalHours' => 1]),
            $authorizedHeaders
        );
        check_same(500, $response['status'], "recorded {$failureMode} cannot return 204");
        check_same('{"ok":false,"error":"metrics_unavailable"}', $response['body'], "recorded {$failureMode} returns generic unavailable JSON");
        $states = json_decode((string) file_get_contents($statePath), true);
        check_same([], $states[$failureMode]['installs'] ?? [], "{$failureMode} rolls back installation write");
        check_same(0, $states[$failureMode]['daily'] ?? 0, "{$failureMode} rolls back daily counter write");
        check_same(0, $states[$failureMode]['total'] ?? 0, "{$failureMode} rolls back singleton write");
    }

    foreach (['GET', 'POST'] as $failedMethod) {
        $failureBody = $failedMethod === 'POST' ? (string) $postBody : '';
        $failureHeaders = $failedMethod === 'POST' ? $authorizedHeaders : [];
        $response = test_http_request($port, $failedMethod, 'failure', $failureBody, $failureHeaders);
        check_same(500, $response['status'], "failed {$failedMethod} returns HTTP 500");
        check_same('{"ok":false,"error":"metrics_unavailable"}', $response['body'], "failed {$failedMethod} returns generic unavailable JSON");
        check_same('no-store', test_header($response, 'Cache-Control'), "failed {$failedMethod} is not cached");
        check(!str_contains($response['body'], 'internal-db-secret'), "failed {$failedMethod} hides internal database errors");
        check(!str_contains($response['body'], $validUuid), "failed {$failedMethod} hides raw installation ID");
        check(!str_contains($response['body'], 'totalDays'), "failed {$failedMethod} exposes no aggregate or per-install data");
    }
} catch (Throwable $exception) {
    check(false, 'behavioral HTTP fixture completed: ' . $exception->getMessage());
} finally {
    if (is_resource($server)) {
        proc_terminate($server);
        proc_close($server);
    }
    test_remove_tree($fixtureDirectory);
}

$configOnlyCode = 'define("SWEETY_MYSQL_CONFIG_ONLY", true); require ' . var_export($root . '/web/mysql.php', true)
    . '; echo isset($mysqlhost, $mysqluser, $mysqlpasswd, $mysqldb) ? "configured" : "missing";';
$configProcess = proc_open(
    [PHP_BINARY, '-d', 'display_errors=1', '-r', $configOnlyCode],
    [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']],
    $configPipes
);
if (is_resource($configProcess)) {
    fclose($configPipes[0]);
    $configOutput = stream_get_contents($configPipes[1]);
    $configErrors = stream_get_contents($configPipes[2]);
    fclose($configPipes[1]);
    fclose($configPipes[2]);
    $configExit = proc_close($configProcess);
    check_same(0, $configExit, 'mysql config-only include exits successfully without connecting');
    check_same('configured', $configOutput, 'mysql config-only include exposes configuration variables only');
    check_same('', $configErrors, 'mysql config-only include emits no connection errors');
} else {
    check(false, 'mysql config-only subprocess started');
}

if ($failures !== []) {
    fwrite(STDERR, "FAIL: " . count($failures) . " of {$assertions} assertions failed\n");
    foreach ($failures as $failure) {
        fwrite(STDERR, " - {$failure}\n");
    }
    exit(1);
}

echo "PASS: {$assertions} assertions\n";
