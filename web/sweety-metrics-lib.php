<?php

declare(strict_types=1);

const SWEETY_METRICS_MAX_TOTAL_HOURS = 1000000;
const SWEETY_METRICS_MAX_INITIAL_HOURS = 24;
const SWEETY_METRICS_GROWTH_GRACE_HOURS = 2;

function sweety_metrics_summary(int $totalHours): array
{
    $totalHours = max(0, $totalHours);

    return [
        'totalDays' => intdiv($totalHours, 24),
        'totalHours' => $totalHours % 24,
    ];
}

function sweety_metrics_parse_aggregate(mixed $value): ?int
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

function sweety_metrics_is_valid_installation_id(mixed $installationId): bool
{
    return is_string($installationId)
        && preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iD', $installationId) === 1;
}

function sweety_metrics_validate_payload(mixed $payload): ?array
{
    if (!is_array($payload)
        || count($payload) !== 2
        || !array_key_exists('installationId', $payload)
        || !array_key_exists('totalHours', $payload)) {
        return null;
    }

    if (!sweety_metrics_is_valid_installation_id($payload['installationId'])) {
        return null;
    }

    if (!is_int($payload['totalHours'])
        || $payload['totalHours'] < 0
        || $payload['totalHours'] > SWEETY_METRICS_MAX_TOTAL_HOURS) {
        return null;
    }

    return [
        'installationId' => $payload['installationId'],
        'totalHours' => $payload['totalHours'],
    ];
}

function sweety_metrics_is_authorized_post(
    string $method,
    string $appName,
    string $userAgent,
    string $expectedToken,
    string $providedToken
): bool {
    return $method === 'POST'
        && $appName === 'desktop'
        && str_starts_with($userAgent, 'SweetyApp/')
        && $expectedToken !== ''
        && hash_equals($expectedToken, $providedToken);
}

function sweety_metrics_installation_hash(string $installationId): string
{
    return hash('sha256', strtolower($installationId));
}

function sweety_metrics_monotonic_total(int $storedTotal, int $reportedTotal): int
{
    return max($storedTotal, $reportedTotal);
}

function sweety_metrics_growth_decision(
    ?int $storedTotal,
    ?int $baselineHours,
    ?int $createdAt,
    int $reportedTotal,
    int $now
): array {
    if ($storedTotal === null) {
        return $reportedTotal <= SWEETY_METRICS_MAX_INITIAL_HOURS
            ? ['accepted' => true, 'total' => $reportedTotal, 'delta' => $reportedTotal]
            : ['accepted' => false, 'total' => $reportedTotal, 'delta' => 0];
    }

    if ($reportedTotal <= $storedTotal) {
        return ['accepted' => true, 'total' => $storedTotal, 'delta' => 0];
    }

    if ($baselineHours === null
        || $baselineHours < 0
        || $baselineHours > SWEETY_METRICS_MAX_TOTAL_HOURS
        || $createdAt === null
        || $createdAt <= 0) {
        return ['accepted' => false, 'total' => $reportedTotal, 'delta' => 0];
    }

    $elapsedWholeHours = intdiv(max(0, $now - $createdAt), 3600);
    $baselineCeiling = $baselineHours >= SWEETY_METRICS_MAX_TOTAL_HOURS
        ? SWEETY_METRICS_MAX_TOTAL_HOURS
        : min(
            SWEETY_METRICS_MAX_TOTAL_HOURS,
            $baselineHours + $elapsedWholeHours + SWEETY_METRICS_GROWTH_GRACE_HOURS
        );
    $maximumTotal = max($storedTotal, $baselineCeiling);
    if ($reportedTotal > $maximumTotal) {
        return ['accepted' => false, 'total' => $reportedTotal, 'delta' => 0];
    }

    return [
        'accepted' => true,
        'total' => $reportedTotal,
        'delta' => $reportedTotal - $storedTotal,
    ];
}
