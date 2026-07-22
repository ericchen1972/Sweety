<?php

declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    header('Content-Type: application/json; charset=utf-8');
    $expectedToken = '__TOKEN__';
    $providedToken = isset($_GET['token']) ? (string) $_GET['token'] : '';
    if (!hash_equals($expectedToken, $providedToken)) {
        http_response_code(403);
        echo json_encode(['ok' => false, 'error' => 'Forbidden']);
        exit;
    }
}

$sqlFile = __DIR__ . '/__SQL_FILE__';
$runnerFile = __FILE__;
$response = ['ok' => false];

try {
    mysqli_report(MYSQLI_REPORT_OFF);
    require __DIR__ . '/mysql.php';

    if (!isset($mysqli) || !($mysqli instanceof mysqli)) {
        throw new RuntimeException('Database connection was not created.');
    }

    $sql = file_get_contents($sqlFile);
    if ($sql === false) {
        throw new RuntimeException('Migration payload could not be read.');
    }

    $legacyPersonaColumns = [
        'summary_zh_tw', 'summary_en', 'prompt_zh_tw', 'prompt_en',
        'speech_style_zh_tw', 'speech_style_en', 'is_active',
    ];
    $tableResult = $mysqli->query("SHOW TABLES LIKE 'base_personas'");
    $personaTableExists = $tableResult !== false && $tableResult->num_rows > 0;
    if ($tableResult instanceof mysqli_result) {
        $tableResult->free();
    }
    if ($personaTableExists) {
        $columnResult = $mysqli->query('SHOW COLUMNS FROM base_personas');
        $personaColumns = [];
        while ($row = $columnResult->fetch_assoc()) {
            $personaColumns[] = (string) $row['Field'];
        }
        $columnResult->free();
        if (!in_array('content_zh_tw', $personaColumns, true)) {
            if (!$mysqli->query('ALTER TABLE base_personas ADD COLUMN content_zh_tw LONGTEXT NULL AFTER name_en, ADD COLUMN content_en LONGTEXT NULL AFTER content_zh_tw')) {
                throw new RuntimeException($mysqli->error);
            }
        }
        if (in_array('prompt_zh_tw', $personaColumns, true) && in_array('speech_style_zh_tw', $personaColumns, true)) {
            if (!$mysqli->query("UPDATE base_personas SET content_zh_tw = CONCAT('人物資料：\\n', prompt_zh_tw, '\\n\\n風格個性：\\n', speech_style_zh_tw), content_en = CONCAT('Character information:\\n', prompt_en, '\\n\\nPersonality and style:\\n', speech_style_en) WHERE content_zh_tw IS NULL OR TRIM(content_zh_tw) = ''")) {
                throw new RuntimeException($mysqli->error);
            }
        }
    }

    if (!$mysqli->multi_query($sql)) {
        throw new RuntimeException($mysqli->error);
    }

    do {
        if ($result = $mysqli->store_result()) {
            $result->free();
        }

        if ($mysqli->errno) {
            throw new RuntimeException($mysqli->error);
        }
    } while ($mysqli->more_results() && $mysqli->next_result());

    $indexResult = $mysqli->query("SHOW INDEX FROM base_personas WHERE Key_name = 'idx_base_personas_filter'");
    $personaFilterIndexExists = $indexResult !== false && $indexResult->num_rows > 0;
    if ($indexResult instanceof mysqli_result) {
        $indexResult->free();
    }
    foreach ($legacyPersonaColumns as $column) {
        $columnResult = $mysqli->query("SHOW COLUMNS FROM base_personas LIKE '{$column}'");
        $exists = $columnResult !== false && $columnResult->num_rows > 0;
        if ($columnResult instanceof mysqli_result) {
            $columnResult->free();
        }
        if ($exists && !$mysqli->query("ALTER TABLE base_personas DROP COLUMN `{$column}`")) {
            throw new RuntimeException($mysqli->error);
        }
    }
    if (!$mysqli->query('ALTER TABLE base_personas MODIFY content_zh_tw LONGTEXT NOT NULL, MODIFY content_en LONGTEXT NOT NULL')) {
        throw new RuntimeException($mysqli->error);
    }
    if (!$personaFilterIndexExists && !$mysqli->query('ALTER TABLE base_personas ADD INDEX idx_base_personas_filter (age_group_id, gender, sort_order)')) {
        throw new RuntimeException($mysqli->error);
    }

    $tables = [
        'catalog_age_groups',
        'sweety_system_prompts',
        'base_personas',
        'base_weapons',
        'base_persona_weapons',
        'base_persona_examples',
    ];
    $counts = [];

    foreach ($tables as $table) {
        $result = $mysqli->query("SELECT COUNT(*) AS total FROM `{$table}`");
        if (!$result) {
            throw new RuntimeException($mysqli->error);
        }
        $counts[$table] = (int) $result->fetch_assoc()['total'];
        $result->free();
    }

    $genderCounts = [];
    $result = $mysqli->query(
        "SELECT a.slug AS age_group, p.gender, COUNT(*) AS total
         FROM base_personas p
         JOIN catalog_age_groups a ON a.id = p.age_group_id
         WHERE a.slug IN ('20-35', '35-50', '50-65', '65+')
         GROUP BY a.slug, p.gender"
    );
    while ($row = $result->fetch_assoc()) {
        $genderCounts[$row['age_group']][$row['gender']] = (int) $row['total'];
    }
    $result->free();

    foreach (['20-35', '35-50', '50-65', '65+'] as $ageGroup) {
        if (($genderCounts[$ageGroup]['female'] ?? 0) !== 3 || ($genderCounts[$ageGroup]['male'] ?? 0) !== 3) {
            throw new RuntimeException("The {$ageGroup} catalog must contain three female and three male personas.");
        }
    }

    $result = $mysqli->query(
        "SELECT p.slug, COUNT(DISTINCT pw.weapon_id) AS weapons, COUNT(DISTINCT e.id) AS examples
         FROM base_personas p
         LEFT JOIN base_persona_weapons pw ON pw.persona_id = p.id
         LEFT JOIN base_persona_examples e ON e.persona_id = p.id
         JOIN catalog_age_groups a ON a.id = p.age_group_id
         WHERE a.slug = '20-35'
         GROUP BY p.id, p.slug"
    );

    $verifiedPersonas = 0;
    while ($row = $result->fetch_assoc()) {
        if ((int) $row['weapons'] !== 3 || (int) $row['examples'] !== 4) {
            throw new RuntimeException("Incomplete catalog relations for {$row['slug']}.");
        }
        $verifiedPersonas++;
    }
    $result->free();

    if ($verifiedPersonas !== 6) {
        throw new RuntimeException('Expected to verify six 20-35 personas.');
    }

    $result = $mysqli->query(
        "SELECT COUNT(*) AS total
         FROM base_personas p
         JOIN catalog_age_groups a ON a.id = p.age_group_id
         WHERE a.slug IN ('20-35', '35-50', '50-65', '65+')
           AND CHAR_LENGTH(TRIM(p.content_zh_tw)) >= 180
           AND CHAR_LENGTH(TRIM(p.content_en)) >= 300"
    );
    $readableStylePersonas = (int) $result->fetch_assoc()['total'];
    $result->free();
    if ($readableStylePersonas !== 24) {
        $result = $mysqli->query(
            "SELECT COUNT(*) AS total,
                    MIN(CHAR_LENGTH(TRIM(content_zh_tw))) AS min_zh,
                    MIN(CHAR_LENGTH(TRIM(content_en))) AS min_en
             FROM base_personas"
        );
        $contentStats = $result->fetch_assoc();
        $result->free();
        throw new RuntimeException(sprintf(
            'Expected detailed localized content for all 24 personas; qualifying=%d total=%d min_zh=%d min_en=%d.',
            $readableStylePersonas,
            (int) $contentStats['total'],
            (int) $contentStats['min_zh'],
            (int) $contentStats['min_en']
        ));
    }

    $mysqli->close();
    $response = [
        'ok' => true,
        'counts' => $counts,
        'checks' => [
            'age_groups_verified' => 4,
            'personas_per_age_group' => 6,
            'weapons_per_persona' => 3,
            'examples_per_persona' => 4,
            'detailed_personas' => $readableStylePersonas,
        ],
    ];
} catch (Throwable $error) {
    http_response_code(500);
    $response = ['ok' => false, 'error' => $error->getMessage()];
} finally {
    @unlink($sqlFile);
    @unlink($runnerFile);
}

echo json_encode($response, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
