<?php

declare(strict_types=1);

function fail(string $message): never
{
    fwrite(STDERR, $message . PHP_EOL);
    exit(1);
}

function readConfig(string $path): array
{
    $raw = file_get_contents($path);
    if ($raw === false) {
        fail('Unable to read FTP configuration.');
    }
    $raw = preg_replace('~^\s*//.*$~m', '', $raw);
    $raw = preg_replace('~,\s*([}\]])~', '$1', (string) $raw);
    $config = json_decode((string) $raw, true);
    if (!is_array($config)) {
        fail('FTP configuration is invalid.');
    }
    foreach (['host', 'user', 'password'] as $key) {
        if (!isset($config[$key]) || $config[$key] === '') {
            fail("FTP configuration is missing {$key}.");
        }
    }
    return $config;
}

function ensureDirectory(FTP\Connection $ftp, string $path): void
{
    $current = '';
    foreach (array_filter(explode('/', trim($path, '/'))) as $part) {
        $current .= '/' . $part;
        if (@ftp_chdir($ftp, $current)) {
            ftp_chdir($ftp, '/');
            continue;
        }
        if (!@ftp_mkdir($ftp, $current)) {
            fail("Unable to create remote directory {$current}.");
        }
    }
}

function uploadContents(FTP\Connection $ftp, string $remotePath, string $contents): void
{
    $stream = fopen('php://temp', 'r+');
    if ($stream === false) {
        fail('Unable to create upload stream.');
    }
    fwrite($stream, $contents);
    rewind($stream);
    $ok = ftp_fput($ftp, $remotePath, $stream, FTP_BINARY);
    fclose($stream);
    if (!$ok) {
        fail("Unable to upload {$remotePath}.");
    }
}

function downloadContents(FTP\Connection $ftp, string $remotePath): ?string
{
    $stream = fopen('php://temp', 'r+');
    if ($stream === false || !@ftp_fget($ftp, $stream, $remotePath, FTP_BINARY)) {
        if (is_resource($stream)) {
            fclose($stream);
        }
        return null;
    }
    rewind($stream);
    $contents = stream_get_contents($stream);
    fclose($stream);
    return is_string($contents) ? $contents : null;
}

$root = dirname(__DIR__, 2);
$siteRoot = '/sweety.tw';
$volumeRoot = '/volume1/sweety.tw';
$config = readConfig($root . '/web/sftp-config.json');
$ftp = ftp_connect((string) $config['host'], (int) ($config['port'] ?? 21), 30);
if ($ftp === false || !ftp_login($ftp, (string) $config['user'], (string) $config['password'])) {
    fail('Unable to connect or authenticate to FTP.');
}
ftp_pasv($ftp, (bool) ($config['ftp_passive_mode'] ?? true));
ensureDirectory($ftp, $siteRoot . '/images/home');

$files = [
    'index.html',
    'homepage.css',
    'homepage.js',
    'about_sweety.html',
    'robots.txt',
    'sitemap.xml',
    'llms.txt',
    'sweety-update.json',
    'images/logo.webp',
    'images/logo.png',
    'images/eric.png',
    'images/sweety-social-1200x630.png',
    'sweety-metrics.php',
    'sweety-metrics-lib.php',
    'mysql.php',
];
foreach (glob($root . '/web/images/home/*.{webp,png}', GLOB_BRACE) ?: [] as $image) {
    $files[] = 'images/home/' . basename($image);
}

foreach ($files as $relative) {
    $local = $root . '/web/' . $relative;
    $remote = $siteRoot . '/' . $relative;
    if (!ftp_put($ftp, $remote, $local, FTP_BINARY)) {
        fail("Unable to upload {$relative}.");
    }
    if (ftp_size($ftp, $remote) !== filesize($local)) {
        fail("Remote size verification failed for {$relative}.");
    }
}

$runtimePath = $siteRoot . '/.sweety-runtime-env.php';
$runtime = downloadContents($ftp, $runtimePath);
$metricsToken = null;
if (is_string($runtime) && preg_match("~SWEETY_METRICS_APP_TOKEN=([a-f0-9]{64})~", $runtime, $match)) {
    $metricsToken = $match[1];
}
if (!is_string($metricsToken)) {
    $metricsToken = bin2hex(random_bytes(32));
}
$runtime = "<?php\nputenv('SWEETY_METRICS_APP_TOKEN={$metricsToken}');\n";
uploadContents($ftp, $runtimePath, $runtime);
uploadContents($ftp, $siteRoot . '/.user.ini', "auto_prepend_file={$volumeRoot}/.sweety-runtime-env.php\n");

$suffix = bin2hex(random_bytes(8));
$runnerName = '.__sweety_metrics_' . $suffix . '.php';
$sqlName = '.__sweety_metrics_' . $suffix . '.sql';
$template = file_get_contents(__DIR__ . '/metrics_remote_runner.template.php');
$sql = file_get_contents(__DIR__ . '/sweety_metrics.sql');
if ($template === false || $sql === false) {
    fail('Unable to read metrics migration files.');
}
uploadContents($ftp, $siteRoot . '/' . $sqlName, $sql);
uploadContents($ftp, $siteRoot . '/' . $runnerName, str_replace('__SQL_FILE__', $sqlName, $template));

$remoteCommand = '/usr/local/bin/php82 ' . $volumeRoot . '/' . $runnerName;
$sshCommand = escapeshellarg('/usr/bin/expect') . ' '
    . escapeshellarg(__DIR__ . '/synology_ssh.exp') . ' '
    . escapeshellarg($remoteCommand);
$sshOutput = [];
$sshExit = 0;
exec($sshCommand, $sshOutput, $sshExit);
$migration = null;
foreach (array_reverse($sshOutput) as $line) {
    if (str_starts_with(trim($line), '{')) {
        $migration = json_decode(trim($line), true);
        break;
    }
}
if (!is_array($migration) || ($migration['ok'] ?? false) !== true) {
    @ftp_delete($ftp, $siteRoot . '/' . $sqlName);
    @ftp_delete($ftp, $siteRoot . '/' . $runnerName);
    fail('Remote metrics migration failed.');
}
ftp_close($ftp);

putenv('SWEETY_METRICS_APP_TOKEN=' . $metricsToken);
chdir($root . '/app/desktop');
passthru('./build_app.sh', $buildExit);
if ($buildExit !== 0) {
    fail('macOS app build failed after site deployment.');
}

echo 'Uploaded homepage files and ' . count($files) . " verified assets/files.\n";
echo 'Metrics schema verified; aggregate hours: ' . (string) $migration['aggregateHours'] . "\n";
echo "Rebuilt and signed app/desktop/dist/Sweety.app with dedicated metrics configuration.\n";
