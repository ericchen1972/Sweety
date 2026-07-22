<?php

declare(strict_types=1);

function sweety_catalog_text(array $row, string $prefix): array
{
    return [
        'zh-TW' => (string) $row[$prefix . '_zh_tw'],
        'en' => (string) $row[$prefix . '_en'],
    ];
}

function sweety_catalog_persona(array $row, callable $assetUrl): array
{
    return [
        'id' => (string) $row['slug'],
        'ageGroup' => (string) $row['age_group_slug'],
        'gender' => (string) $row['gender'],
        'name' => sweety_catalog_text($row, 'name'),
        'content' => sweety_catalog_text($row, 'content'),
        'image' => $assetUrl((string) $row['image_path']),
    ];
}
