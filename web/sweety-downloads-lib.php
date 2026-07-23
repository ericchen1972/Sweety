<?php

declare(strict_types=1);

function sweety_downloads_parse_total(mixed $value): ?int
{
    if (is_int($value)) {
        return $value >= 0 ? $value : null;
    }
    if (!is_string($value) || preg_match('/^[0-9]+$/D', $value) !== 1) {
        return null;
    }

    $normalized = ltrim($value, '0');
    if ($normalized === '') {
        return 0;
    }
    $maximum = (string) PHP_INT_MAX;
    if (strlen($normalized) > strlen($maximum)
        || (strlen($normalized) === strlen($maximum) && strcmp($normalized, $maximum) > 0)) {
        return null;
    }

    return (int) $normalized;
}
