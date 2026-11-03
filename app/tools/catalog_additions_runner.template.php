<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
try {
    require __DIR__ . '/mysql.php';
    $mysqli->set_charset('utf8mb4');
    $payload = json_decode(file_get_contents(__DIR__ . '/__PAYLOAD__'), true, 512, JSON_THROW_ON_ERROR);
    $personas = $payload['selected'];
    if (($argv[1] ?? '') === 'backup') {
        $rows = $mysqli->query('SELECT * FROM base_personas')->fetch_all(MYSQLI_ASSOC);
        $prompts = $mysqli->query('SELECT * FROM sweety_system_prompts')->fetch_all(MYSQLI_ASSOC);
        $schema = $mysqli->query('SHOW CREATE TABLE base_personas')->fetch_assoc();
        echo json_encode(['ok' => true, 'personas' => $rows, 'prompts' => $prompts, 'schema' => $schema], JSON_UNESCAPED_UNICODE) . PHP_EOL;
        exit;
    }
    if (($argv[1] ?? '') !== 'apply' || !$personas) {
        throw new RuntimeException('Invalid operation or empty payload');
    }
    // Older production catalogs predate Japanese localization. Preserve all
    // existing Chinese/English content and only fill missing Japanese fields.
    $columns = array_column($mysqli->query('SHOW COLUMNS FROM base_personas')->fetch_all(MYSQLI_ASSOC), 'Field');
    foreach (['name_ja' => 'VARCHAR(100)', 'content_ja' => 'LONGTEXT'] as $column => $type) {
        if (!in_array($column, $columns, true)) {
            $mysqli->query("ALTER TABLE base_personas ADD COLUMN {$column} {$type} NULL");
        }
    }
    $mysqli->begin_transaction();
    $localize = $mysqli->prepare("UPDATE base_personas SET
        name_ja=IF(name_ja IS NULL OR TRIM(name_ja)='', ?, name_ja),
        content_ja=IF(content_ja IS NULL OR TRIM(content_ja)='', ?, content_ja) WHERE slug=?");
    foreach ($payload['localizations'] as $row) {
        $localize->bind_param('sss', $row['name'], $row['content'], $row['id']);
        $localize->execute();
    }
    $statement = $mysqli->prepare('INSERT INTO base_personas
        (slug, age_group_id, gender, name_zh_tw, name_en, name_ja, content_zh_tw, content_en, content_ja, image_path, sort_order)
        VALUES (?, (SELECT id FROM catalog_age_groups WHERE slug = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE age_group_id=VALUES(age_group_id), gender=VALUES(gender),
        name_zh_tw=VALUES(name_zh_tw), name_en=VALUES(name_en), name_ja=VALUES(name_ja),
        content_zh_tw=VALUES(content_zh_tw), content_en=VALUES(content_en), content_ja=VALUES(content_ja),
        image_path=VALUES(image_path), sort_order=VALUES(sort_order)');
    foreach ($personas as $p) {
        foreach (['name', 'content'] as $field) {
            foreach (['zh-TW', 'en', 'ja'] as $locale) {
                if (!is_string($p[$field][$locale] ?? null) || trim($p[$field][$locale]) === '') {
                    throw new RuntimeException('Incomplete localization');
                }
            }
        }
        $statement->bind_param('ssssssssssi', $p['id'], $p['ageGroup'], $p['gender'],
            $p['name']['zh-TW'], $p['name']['en'], $p['name']['ja'],
            $p['content']['zh-TW'], $p['content']['en'], $p['content']['ja'], $p['image'], $p['sortOrder']);
        $statement->execute();
    }
    $mysqli->commit();
    echo json_encode(['ok' => true, 'ids' => array_column($personas, 'id')]) . PHP_EOL;
} catch (Throwable $error) {
    if (isset($mysqli)) {
        $mysqli->rollback();
    }
    echo json_encode(['ok' => false, 'error' => $error->getMessage()]) . PHP_EOL;
    exit(1);
}
