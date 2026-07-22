<?php

declare(strict_types=1);

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
    if ($sql === false || !$mysqli->multi_query($sql)) {
        throw new RuntimeException($mysqli->error ?: 'Migration payload could not be executed.');
    }
    do {
        if ($result = $mysqli->store_result()) {
            $result->free();
        }
        if ($mysqli->errno) {
            throw new RuntimeException($mysqli->error);
        }
    } while ($mysqli->more_results() && $mysqli->next_result());

    $requiredTables = [
        'sweety_install_metrics',
        'sweety_metrics_totals',
        'sweety_metrics_daily_registrations',
    ];
    foreach ($requiredTables as $table) {
        $result = $mysqli->query("SHOW TABLES LIKE '{$table}'");
        if (!$result || $result->num_rows !== 1) {
            throw new RuntimeException("Missing metrics table {$table}.");
        }
        $result->free();
    }

    $result = $mysqli->query(
        "SELECT COUNT(*) AS total
         FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'sweety_install_metrics'
           AND COLUMN_NAME IN ('installation_hash', 'total_hours', 'baseline_hours', 'created_at', 'updated_at')"
    );
    if (!$result || (int) $result->fetch_assoc()['total'] !== 5) {
        throw new RuntimeException('Metrics installation schema is incomplete.');
    }
    $result->free();

    $result = $mysqli->query('SELECT total_hours FROM sweety_metrics_totals WHERE id = 1');
    if (!$result || $result->num_rows !== 1) {
        throw new RuntimeException('Metrics aggregate singleton is unavailable.');
    }
    $aggregate = (string) $result->fetch_assoc()['total_hours'];
    $result->free();

    $mysqli->close();
    $response = ['ok' => true, 'aggregateHours' => $aggregate];
} catch (Throwable $error) {
    $response = ['ok' => false, 'error' => $error->getMessage()];
} finally {
    @unlink($sqlFile);
    @unlink($runnerFile);
}

echo json_encode($response, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
