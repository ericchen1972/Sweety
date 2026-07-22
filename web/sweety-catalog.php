<?php

declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

require_once __DIR__ . '/sweety-catalog-lib.php';

const SWEETY_DEFAULT_APP_TOKEN = 'sweety-desktop-catalog-v1';

function sweety_json_response(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function sweety_header(string $name): string
{
    $key = 'HTTP_' . strtoupper(str_replace('-', '_', $name));
    return trim((string) ($_SERVER[$key] ?? ''));
}

function sweety_is_authorized_request(): bool
{
    $expectedToken = getenv('SWEETY_APP_TOKEN') ?: SWEETY_DEFAULT_APP_TOKEN;
    $providedToken = sweety_header('X-Sweety-App-Token');
    $appName = sweety_header('X-Sweety-App');
    $userAgent = (string) ($_SERVER['HTTP_USER_AGENT'] ?? '');

    return $_SERVER['REQUEST_METHOD'] === 'GET'
        && $appName === 'desktop'
        && str_starts_with($userAgent, 'SweetyApp/')
        && is_string($expectedToken)
        && $expectedToken !== ''
        && hash_equals($expectedToken, $providedToken);
}

function sweety_asset_url(string $path): string
{
    if (str_starts_with($path, 'http://') || str_starts_with($path, 'https://')) {
        return $path;
    }

    $relativePath = str_starts_with($path, '/') ? substr($path, 1) : $path;
    $localPath = __DIR__ . '/' . $relativePath;
    if (is_file($localPath)) {
        $contents = file_get_contents($localPath);
        if ($contents !== false) {
            $mime = function_exists('mime_content_type') ? (mime_content_type($localPath) ?: 'image/jpeg') : 'image/jpeg';
            return 'data:' . $mime . ';base64,' . base64_encode($contents);
        }
    }

    return 'https://sweety.tw' . (str_starts_with($path, '/') ? $path : '/' . $path);
}

if (!sweety_is_authorized_request()) {
    sweety_json_response(403, ['ok' => false, 'error' => 'forbidden']);
}

try {
    require_once __DIR__ . '/MysqliDb.php';

    ob_start();
    require __DIR__ . '/mysql.php';
    ob_end_clean();

    if (!isset($mysqlhost, $mysqluser, $mysqlpasswd, $mysqldb)) {
        throw new RuntimeException('Database configuration is unavailable.');
    }

    $db = new MysqliDb($mysqlhost, $mysqluser, $mysqlpasswd, $mysqldb, 3306, 'utf8mb4');

    $db->where('prompt_key', 'catalog_v1');
    $db->where('is_active', 1);
    $promptRow = $db->getOne('sweety_system_prompts', ['template']);
    if (!is_array($promptRow) || trim((string) ($promptRow['template'] ?? '')) === '') {
        throw new RuntimeException('System prompt is not configured.');
    }

    $rows = $db->rawQuery(
        "SELECT p.slug, p.gender, p.name_zh_tw, p.name_en,
                a.slug AS age_group_slug,
                p.content_zh_tw, p.content_en, p.image_path
         FROM base_personas p
         JOIN catalog_age_groups a ON a.id = p.age_group_id
         WHERE a.slug IN ('20-35', '35-50', '50-65', '65+')
         ORDER BY p.sort_order ASC, p.id ASC"
    );

    if (!is_array($rows) || count($rows) === 0) {
        throw new RuntimeException('Base personas are not configured.');
    }

    $basePersonas = [];
    foreach ($rows as $row) {
        $basePersonas[] = sweety_catalog_persona($row, 'sweety_asset_url');
    }

    sweety_json_response(200, [
        'systemPromptTemplate' => (string) $promptRow['template'],
        'basePersonas' => $basePersonas,
    ]);
} catch (Throwable $exception) {
    sweety_json_response(500, ['ok' => false, 'error' => 'catalog_unavailable']);
}
