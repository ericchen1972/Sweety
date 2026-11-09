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

$root = dirname(__DIR__, 2);
$remoteDirectory = '/sweety.tw/downloads';
$remotePath = '/sweety.tw/downloads/Sweety-Windows-Setup-2.0.4.exe';
$localPath = $root . '/dist/Sweety-Windows-Setup.exe';
$config = readConfig($root . '/web/sftp-config.json');

if (!is_file($localPath) || filesize($localPath) <= 0) {
    fail('Windows installer is missing or empty.');
}
$stream = fopen($localPath, 'rb');
$hasMzSignature = $stream !== false && fread($stream, 2) === 'MZ';
if (is_resource($stream)) {
    fclose($stream);
}
if (!$hasMzSignature) {
    fail('Windows installer does not have a valid executable signature.');
}

$ftp = connectFtp($config);
ensureDirectory($ftp, $remoteDirectory);
$temporaryPath = $remotePath . '.uploading';
if (!ftp_put($ftp, $temporaryPath, $localPath, FTP_BINARY)) {
    ftp_close($ftp);
    fail('Unable to upload the Windows installer.');
}
if (ftp_size($ftp, $temporaryPath) !== filesize($localPath)) {
    ftp_close($ftp);
    fail('Remote Windows installer size verification failed.');
}
$verified = tmpfile();
if ($verified === false || !ftp_fget($ftp, $verified, $temporaryPath, FTP_BINARY)) {
    fail('Unable to read back uploaded installer.');
}
rewind($verified);
$hash = hash_init('sha256');
hash_update_stream($hash, $verified);
fclose($verified);
if (!hash_equals(hash_file('sha256', $localPath), hash_final($hash))) {
    fail('Remote Windows installer SHA-256 verification failed.');
}
if (!ftp_rename($ftp, $temporaryPath, $remotePath)) {
    fail('Unable to publish verified Windows installer.');
}
ftp_close($ftp);

echo 'Uploaded ' . filesize($localPath) . " bytes to {$remotePath}.\n";
