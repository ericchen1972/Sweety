<?php

declare(strict_types=1);

require_once __DIR__ . '/../sweety-catalog-lib.php';

$persona = sweety_catalog_persona([
    'slug' => 'cautious-accounting-assistant',
    'age_group_slug' => '20-35',
    'gender' => 'female',
    'name_zh_tw' => '謹慎的會計助理',
    'name_en' => 'Cautious Accounting Assistant',
    'content_zh_tw' => '人物資料：王筱蘭住在板橋。',
    'content_en' => 'Character information: Wang Xiaolan lives in Banqiao.',
    'image_path' => '/images/personas/cautious-accounting-assistant.jpg',
], static fn (string $path): string => $path);

assert($persona === [
    'id' => 'cautious-accounting-assistant',
    'ageGroup' => '20-35',
    'gender' => 'female',
    'name' => ['zh-TW' => '謹慎的會計助理', 'en' => 'Cautious Accounting Assistant'],
    'content' => [
        'zh-TW' => '人物資料：王筱蘭住在板橋。',
        'en' => 'Character information: Wang Xiaolan lives in Banqiao.',
    ],
    'image' => '/images/personas/cautious-accounting-assistant.jpg',
]);
assert(array_intersect(['summary', 'profile', 'style', 'text'], array_keys($persona)) === []);

echo "PASS: simplified persona contract\n";
