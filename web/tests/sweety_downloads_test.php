<?php

declare(strict_types=1);

$root = dirname(__DIR__, 2);
$libraryPath = $root . '/web/sweety-downloads-lib.php';
$endpointPath = $root . '/web/sweety-downloads.php';
$migrationPath = $root . '/app/tools/sweety_metrics.sql';
$runnerPath = $root . '/app/tools/metrics_remote_runner.template.php';
$failures = [];
$assertions = 0;

function download_check(bool $condition, string $message): void
{
    global $assertions, $failures;
    $assertions++;
    if (!$condition) {
        $failures[] = $message;
    }
}

function download_check_same(mixed $expected, mixed $actual, string $message): void
{
    download_check(
        $expected === $actual,
        $message . ' (expected ' . var_export($expected, true) . ', got ' . var_export($actual, true) . ')'
    );
}

function download_http_request(int $port, string $method, string $mode): array
{
    $context = stream_context_create([
        'http' => [
            'method' => $method,
            'header' => "X-Test-Db-Mode: {$mode}",
            'ignore_errors' => true,
            'timeout' => 5,
        ],
    ]);
    $body = file_get_contents("http://127.0.0.1:{$port}/sweety-downloads.php", false, $context);
    $status = 0;
    $headers = [];
    foreach ($http_response_header ?? [] as $line) {
        if (preg_match('/^HTTP\/\S+\s+(\d{3})/', $line, $matches)) {
            $status = (int) $matches[1];
            continue;
        }
        $separator = strpos($line, ':');
        if ($separator !== false) {
            $headers[strtolower(substr($line, 0, $separator))] = trim(substr($line, $separator + 1));
        }
    }
    return ['status' => $status, 'headers' => $headers, 'body' => $body === false ? '' : $body];
}

function download_header(array $response, string $name): string
{
    return (string) ($response['headers'][strtolower($name)] ?? '');
}

function download_remove_tree(string $directory): void
{
    if (!is_dir($directory)) {
        return;
    }
    foreach (scandir($directory) ?: [] as $entry) {
        if ($entry === '.' || $entry === '..') {
            continue;
        }
        $path = $directory . '/' . $entry;
        is_dir($path) ? download_remove_tree($path) : unlink($path);
    }
    rmdir($directory);
}

download_check(is_file($libraryPath), 'download helper library exists');
download_check(is_file($endpointPath), 'download endpoint exists');
download_check(is_file($migrationPath), 'metrics migration exists');
download_check(is_file($runnerPath), 'metrics migration runner exists');

if (is_file($libraryPath)) {
    require_once $libraryPath;
}

download_check(function_exists('sweety_downloads_parse_total'), 'download total parser exists');
if (function_exists('sweety_downloads_parse_total')) {
    download_check_same(0, sweety_downloads_parse_total(0), 'integer zero is valid');
    download_check_same(42, sweety_downloads_parse_total('42'), 'database integer string is valid');
    download_check_same(null, sweety_downloads_parse_total(-1), 'negative integer is invalid');
    download_check_same(null, sweety_downloads_parse_total('1.5'), 'decimal string is invalid');
    download_check_same(null, sweety_downloads_parse_total('18446744073709551615'), 'overflow is invalid');
}

$endpoint = is_file($endpointPath) ? (string) file_get_contents($endpointPath) : '';
download_check(str_contains($endpoint, 'Cache-Control: public, max-age=60'), 'GET is briefly cached');
download_check(str_contains($endpoint, 'Cache-Control: no-store'), 'POST is never cached');
download_check(str_contains($endpoint, 'total_downloads = total_downloads + 1'), 'POST increments atomically');
download_check(!str_contains($endpoint, 'REMOTE_ADDR'), 'endpoint does not read client IP');
download_check(str_contains($endpoint, "header('Content-Type: application/json; charset=utf-8')"), 'endpoint returns UTF-8 JSON');

$migration = is_file($migrationPath) ? (string) file_get_contents($migrationPath) : '';
download_check(
    (bool) preg_match('/CREATE TABLE(?: IF NOT EXISTS)? sweety_download_totals/i', $migration),
    'migration creates download singleton'
);
download_check(
    (bool) preg_match('/total_downloads\s+BIGINT\s+UNSIGNED/i', $migration),
    'download total uses unsigned BIGINT'
);
download_check(
    (bool) preg_match('/INSERT INTO sweety_download_totals[\s\S]*VALUES\s*\(1,\s*0\)/i', $migration),
    'migration seeds singleton'
);

$runner = is_file($runnerPath) ? (string) file_get_contents($runnerPath) : '';
download_check(str_contains($runner, "'sweety_download_totals'"), 'runner requires download table');
download_check(str_contains($runner, "'downloadTotal'"), 'runner reports download total');

$fixtureDirectory = null;
$server = null;
if ($endpoint !== '' && is_file($libraryPath)) {
    $fixtureDirectory = sys_get_temp_dir() . '/sweety-downloads-' . getmypid() . '-' . bin2hex(random_bytes(4));
    $statePath = $fixtureDirectory . '/state.json';
    $serverLog = $fixtureDirectory . '/server.log';
    try {
        mkdir($fixtureDirectory, 0700, true);
        copy($libraryPath, $fixtureDirectory . '/sweety-downloads-lib.php');
        copy($endpointPath, $fixtureDirectory . '/sweety-downloads.php');
        file_put_contents($statePath, json_encode(['total' => 0]));
        file_put_contents(
            $fixtureDirectory . '/mysql.php',
            "<?php\n\$mysqlhost='fake';\$mysqluser='fake';\$mysqlpasswd='fake';\$mysqldb='fake';\n"
        );
        $fakeDatabase = <<<'PHP'
<?php
class MysqliDb
{
    private int $lastErrno = 0;
    private string $lastError = '';

    public function __construct(...$arguments) {}

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
        $mode = (string) ($_SERVER['HTTP_X_TEST_DB_MODE'] ?? 'normal');
        if ($mode === 'failure') {
            $this->lastErrno = 1205;
            $this->lastError = 'internal database detail must not leak';
            return false;
        }
        $this->lastErrno = 0;
        $this->lastError = '';
        $state = json_decode((string) file_get_contents(__STATE_PATH__), true);
        $normalized = strtoupper((string) preg_replace('/\s+/', ' ', trim($sql)));
        if (str_starts_with($normalized, 'UPDATE SWEETY_DOWNLOAD_TOTALS')) {
            $state['total'] = (int) ($state['total'] ?? 0) + 1;
            file_put_contents(__STATE_PATH__, json_encode($state));
            return true;
        }
        if (str_starts_with($normalized, 'SELECT TOTAL_DOWNLOADS FROM SWEETY_DOWNLOAD_TOTALS')) {
            return [['total_downloads' => (int) ($state['total'] ?? 0)]];
        }
        return false;
    }
}
PHP;
        file_put_contents(
            $fixtureDirectory . '/MysqliDb.php',
            str_replace('__STATE_PATH__', var_export($statePath, true), $fakeDatabase)
        );
        file_put_contents($fixtureDirectory . '/router.php', "<?php\nrequire __DIR__ . '/sweety-downloads.php';\n");

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

        $get = download_http_request($port, 'GET', 'normal');
        download_check_same(200, $get['status'], 'GET succeeds');
        download_check_same(['totalDownloads' => 0], json_decode($get['body'], true), 'GET returns zero');
        download_check_same('public, max-age=60', download_header($get, 'Cache-Control'), 'GET uses short cache');

        $post = download_http_request($port, 'POST', 'normal');
        download_check_same(200, $post['status'], 'POST succeeds');
        download_check_same(['totalDownloads' => 1], json_decode($post['body'], true), 'POST returns incremented total');
        download_check_same('no-store', download_header($post, 'Cache-Control'), 'POST is not cached');

        $secondPost = download_http_request($port, 'POST', 'normal');
        download_check_same(200, $secondPost['status'], 'second POST succeeds');
        download_check_same(['totalDownloads' => 2], json_decode($secondPost['body'], true), 'repeated click counts again');

        $put = download_http_request($port, 'PUT', 'normal');
        download_check_same(405, $put['status'], 'unsupported method is rejected');
        download_check_same('GET, POST', download_header($put, 'Allow'), 'unsupported method advertises methods');

        $failure = download_http_request($port, 'GET', 'failure');
        download_check_same(500, $failure['status'], 'database failure is reported');
        download_check_same(
            ['ok' => false, 'error' => 'downloads_unavailable'],
            json_decode($failure['body'], true),
            'database failure is generic'
        );
        download_check(!str_contains($failure['body'], 'internal database detail'), 'database details do not leak');
    } catch (Throwable $error) {
        $failures[] = 'download endpoint integration setup failed: ' . $error->getMessage();
    } finally {
        if (is_resource($server)) {
            proc_terminate($server);
            proc_close($server);
        }
        if (is_string($fixtureDirectory)) {
            download_remove_tree($fixtureDirectory);
        }
    }
}

if ($failures !== []) {
    fwrite(STDERR, implode(PHP_EOL, $failures) . PHP_EOL);
    exit(1);
}

echo "OK ({$assertions} assertions)\n";
