<?php

declare(strict_types=1);

$root = dirname(__DIR__, 2);
mysqli_report(MYSQLI_REPORT_OFF);
require $root . '/web/mysql.php';

if (!isset($mysqli) || !($mysqli instanceof mysqli)) {
    fwrite(STDERR, "Database connection was not created.\n");
    exit(1);
}

$sql = file_get_contents(__DIR__ . '/base_catalog.sql');
if ($sql === false) {
    fwrite(STDERR, "Unable to read base_catalog.sql.\n");
    exit(1);
}

if (!$mysqli->multi_query($sql)) {
    fwrite(STDERR, "Catalog migration failed: {$mysqli->error}\n");
    exit(1);
}

do {
    if ($result = $mysqli->store_result()) {
        $result->free();
    }

    if ($mysqli->errno) {
        fwrite(STDERR, "Catalog migration failed: {$mysqli->error}\n");
        exit(1);
    }
} while ($mysqli->more_results() && $mysqli->next_result());

$expected = [
    'catalog_age_groups' => 1,
    'base_personas' => 6,
    'base_weapons' => 3,
    'base_persona_weapons' => 18,
    'base_persona_examples' => 24,
];

foreach ($expected as $table => $minimum) {
    $result = $mysqli->query("SELECT COUNT(*) AS total FROM `{$table}`");
    if (!$result) {
        fwrite(STDERR, "Unable to verify {$table}: {$mysqli->error}\n");
        exit(1);
    }

    $total = (int) $result->fetch_assoc()['total'];
    $result->free();

    if ($total < $minimum) {
        fwrite(STDERR, "Verification failed for {$table}: expected at least {$minimum}, found {$total}.\n");
        exit(1);
    }

    printf("%-28s %d\n", $table, $total);
}

$mysqli->close();
