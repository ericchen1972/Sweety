<?php

declare(strict_types=1);

function fail(string $message): never
{
    fwrite(STDERR, $message . PHP_EOL);
    exit(1);
}

function readSftpConfig(string $path): array
{
    $raw = file_get_contents($path);
    if ($raw === false) {
        fail('Unable to read FTP configuration.');
    }

    $raw = preg_replace('~^\s*//.*$~m', '', $raw);
    $raw = preg_replace('~,\s*([}\]])~', '$1', (string) $raw);
    $config = json_decode((string) $raw, true);

    if (!is_array($config)) {
        fail('FTP configuration is not valid JSON-with-comments.');
    }

    foreach (['type', 'host', 'user', 'password', 'remote_path'] as $key) {
        if (!isset($config[$key]) || $config[$key] === '') {
            fail("FTP configuration is missing {$key}.");
        }
    }

    if ($config['type'] !== 'ftp') {
        fail('This deploy helper currently supports the configured FTP connection only.');
    }

    return $config;
}

function ensureRemoteDirectory(FTP\Connection $ftp, string $path): void
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

function uploadString(FTP\Connection $ftp, string $remotePath, string $contents): void
{
    $stream = fopen('php://temp', 'r+');
    if ($stream === false) {
        fail('Unable to create an upload stream.');
    }
    fwrite($stream, $contents);
    rewind($stream);

    if (!ftp_fput($ftp, $remotePath, $stream, FTP_BINARY)) {
        fclose($stream);
        fail("Unable to upload {$remotePath}.");
    }
    fclose($stream);
}

$root = dirname(__DIR__, 2);
$config = readSftpConfig($root . '/web/sftp-config.json');
$port = isset($config['port']) ? (int) $config['port'] : 21;
$ftp = ftp_connect((string) $config['host'], $port, (int) ($config['connect_timeout'] ?? 30));
if ($ftp === false || !ftp_login($ftp, (string) $config['user'], (string) $config['password'])) {
    fail('Unable to connect or authenticate to FTP.');
}

ftp_pasv($ftp, (bool) ($config['ftp_passive_mode'] ?? true));
$assetRemoteRoot = '/' . trim((string) $config['remote_path'], '/');
ensureRemoteDirectory($ftp, $assetRemoteRoot . '/images/personas');
ensureRemoteDirectory($ftp, $assetRemoteRoot . '/images/weapons');
$siteRemoteRoot = '/sweety.tw';
ensureRemoteDirectory($ftp, $siteRemoteRoot . '/images/personas');
ensureRemoteDirectory($ftp, $siteRemoteRoot . '/images/weapons');

$assets = [
    'images/personas/cautious-accounting-assistant.jpg',
    'images/personas/busy-nail-salon-assistant.jpg',
    'images/personas/home-freelance-designer.jpg',
    'images/personas/night-shift-convenience-clerk.jpg',
    'images/personas/junior-sales-representative.jpg',
    'images/personas/reserved-freelance-photographer.jpg',
    'images/personas/careful-bank-operations-specialist.jpg',
    'images/personas/busy-bakery-owner.jpg',
    'images/personas/guarded-insurance-clerk.jpg',
    'images/personas/practical-taxi-driver.jpg',
    'images/personas/factory-shift-supervisor.jpg',
    'images/personas/independent-repair-technician.jpg',
    'images/personas/careful-community-pharmacist.jpg',
    'images/personas/busy-market-stall-owner.jpg',
    'images/personas/retired-school-administrator.jpg',
    'images/personas/practical-hardware-store-owner.jpg',
    'images/personas/apartment-building-manager.jpg',
    'images/personas/semi-retired-logistics-dispatcher.jpg',
    'images/personas/careful-retired-nurse.jpg',
    'images/personas/active-community-volunteer.jpg',
    'images/personas/frugal-retired-bookkeeper.jpg',
    'images/personas/retired-plumber.jpg',
    'images/personas/traditional-tea-shop-owner.jpg',
    'images/personas/retired-intercity-bus-driver.jpg',
    'images/weapons/one-step-at-a-time.jpg',
    'images/weapons/ask-someone-first.jpg',
    'images/weapons/constantly-interrupted.jpg',
];

foreach ($assets as $asset) {
    $localPath = $root . '/web/' . $asset;
    $remotePath = $assetRemoteRoot . '/' . $asset;
    if (!ftp_put($ftp, $remotePath, $localPath, FTP_BINARY)) {
        fail("Unable to upload {$asset}.");
    }
    if (ftp_size($ftp, $remotePath) !== filesize($localPath)) {
        fail("Remote size verification failed for {$asset}.");
    }
    $siteRemotePath = $siteRemoteRoot . '/' . $asset;
    if (!ftp_put($ftp, $siteRemotePath, $localPath, FTP_BINARY)) {
        fail("Unable to upload {$asset} to site root.");
    }
    if (ftp_size($ftp, $siteRemotePath) !== filesize($localPath)) {
        fail("Remote site-root size verification failed for {$asset}.");
    }
}

$migrationRemoteRoot = $siteRemoteRoot;
$migrationVolumeRoot = '/volume1/sweety.tw';
if (!ftp_put($ftp, $migrationRemoteRoot . '/about_sweety.html', $root . '/web/about_sweety.html', FTP_BINARY)) {
    fail('Unable to upload about_sweety.html to site root.');
}
$token = bin2hex(random_bytes(24));
$suffix = bin2hex(random_bytes(8));
$runnerName = '.__sweety_catalog_' . $suffix . '.php';
$sqlName = '.__sweety_catalog_' . $suffix . '.sql';
$template = file_get_contents(__DIR__ . '/catalog_remote_runner.template.php');
$sql = file_get_contents(__DIR__ . '/base_catalog.sql');
$generatedPersonas = file_get_contents(__DIR__ . '/base_personas.generated.sql');

if ($template === false || $sql === false || $generatedPersonas === false) {
    fail('Unable to read migration files.');
}
if (!str_contains($sql, '-- __BASE_PERSONAS_GENERATED__')) {
    fail('Persona insertion marker is missing.');
}
$sql = str_replace('-- __BASE_PERSONAS_GENERATED__', $generatedPersonas, $sql);

$runner = str_replace(['__TOKEN__', '__SQL_FILE__'], [$token, $sqlName], $template);
uploadString($ftp, $migrationRemoteRoot . '/' . $sqlName, $sql);
uploadString($ftp, $migrationRemoteRoot . '/' . $runnerName, $runner);

$remoteCommand = '/usr/local/bin/php82 ' . $migrationVolumeRoot . '/' . $runnerName;
$sshCommand = escapeshellarg('/usr/bin/expect') . ' '
    . escapeshellarg(__DIR__ . '/synology_ssh.exp') . ' '
    . escapeshellarg($remoteCommand);
$sshOutput = [];
$sshExitCode = 0;
exec($sshCommand, $sshOutput, $sshExitCode);

$body = null;
foreach (array_reverse($sshOutput) as $line) {
    if (str_starts_with(trim($line), '{')) {
        $body = trim($line);
        break;
    }
}

$result = $body === null ? null : json_decode($body, true);
if (!is_array($result) || ($result['ok'] ?? false) !== true) {
    @ftp_delete($ftp, $migrationRemoteRoot . '/' . $sqlName);
    @ftp_delete($ftp, $migrationRemoteRoot . '/' . $runnerName);
    $reason = is_array($result) ? (string) ($result['error'] ?? 'unknown error') : 'invalid response';
    fail('Remote catalog migration failed: ' . $reason . " (SSH exit {$sshExitCode})");
}

foreach (['sweety-catalog.php', 'sweety-catalog-lib.php'] as $catalogFile) {
    if (!ftp_put($ftp, $assetRemoteRoot . '/' . $catalogFile, $root . '/web/' . $catalogFile, FTP_BINARY)) {
        fail("Unable to upload {$catalogFile} to asset root.");
    }
    if (!ftp_put($ftp, $migrationRemoteRoot . '/' . $catalogFile, $root . '/web/' . $catalogFile, FTP_BINARY)) {
        fail("Unable to upload {$catalogFile} to site root.");
    }
}

ftp_close($ftp);

echo "Uploaded " . count($assets) . " catalog images.\n";
echo "Uploaded sweety-catalog.php and sweety-catalog-lib.php.\n";
echo "Uploaded about_sweety.html.\n";
foreach ($result['counts'] as $table => $count) {
    printf("%-28s %d\n", $table, (int) $count);
}
foreach ($result['checks'] as $check => $value) {
    printf("%-28s %d\n", $check, (int) $value);
}
