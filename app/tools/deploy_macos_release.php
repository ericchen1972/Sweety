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

function connectFtp(array $config): FTP\Connection
{
    $ftp = ftp_connect((string) $config['host'], (int) ($config['port'] ?? 21), 30);
    if ($ftp === false || !ftp_login($ftp, (string) $config['user'], (string) $config['password'])) {
        fail('Unable to connect or authenticate to FTP.');
    }
    ftp_pasv($ftp, (bool) ($config['ftp_passive_mode'] ?? true));
    return $ftp;
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
$runtimePath = '/sweety.tw/.sweety-runtime-env.php';
$remoteDirectory = '/sweety.tw/downloads';
$targetArch = getenv('SWEETY_TARGET_ARCH');
if (!in_array($targetArch, ['arm64', 'x86_64'], true)) {
    fail('Set SWEETY_TARGET_ARCH to arm64 or x86_64 and supply SWEETY_PYTHON and SWEETY_NODE_PATH.');
}
$filename = 'Sweety-macos12.7-' . $targetArch . '-latest.dmg';
$remotePath = $remoteDirectory . '/' . $filename;
$buildRoot = getenv('SWEETY_BUILD_ROOT') ?: '/Users/eric/Documents/Codex-Temp/sweety-macos12/build-' . $targetArch;
$localPath = $buildRoot . '/dist/' . $filename;
$config = readConfig($root . '/web/sftp-config.json');

$ftp = connectFtp($config);
$runtime = downloadContents($ftp, $runtimePath);
ftp_close($ftp);

if (!is_string($runtime) || !preg_match("~SWEETY_METRICS_APP_TOKEN=([a-f0-9]{64})~", $runtime, $match)) {
    fail('Unable to load the existing release metrics configuration.');
}
putenv('SWEETY_METRICS_APP_TOKEN=' . $match[1]);

chdir($root . '/app/desktop');
passthru('./build_dmg.sh', $dmgExit);
if ($dmgExit !== 0 || !is_file($localPath)) {
    fail('macOS DMG build failed.');
}

$ftp = connectFtp($config);
ensureDirectory($ftp, $remoteDirectory);
if (!ftp_put($ftp, $remotePath . '.upload', $localPath, FTP_BINARY)) {
    ftp_close($ftp);
    fail('Unable to upload the macOS DMG.');
}
if (ftp_size($ftp, $remotePath . '.upload') !== filesize($localPath)) {
    ftp_close($ftp);
    fail('Remote DMG size verification failed.');
}
if (!ftp_rename($ftp, $remotePath . '.upload', $remotePath)) {
    fail('Unable to publish the verified macOS DMG.');
}
ftp_close($ftp);

echo 'Uploaded ' . filesize($localPath) . " bytes to {$remotePath}.\n";
