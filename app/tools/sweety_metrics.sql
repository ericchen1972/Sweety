CREATE TABLE IF NOT EXISTS sweety_install_metrics (
    installation_hash CHAR(64) NOT NULL PRIMARY KEY,
    total_hours INT UNSIGNED NOT NULL,
    baseline_hours BIGINT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sweety_install_metrics_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Upgrade an earlier installation of this table without relying on
-- MariaDB-only ALTER TABLE ... IF NOT EXISTS syntax.
SET @sweety_has_baseline_hours = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'sweety_install_metrics'
      AND column_name = 'baseline_hours'
);
SET @sweety_baseline_hours_sql = IF(
    @sweety_has_baseline_hours = 0,
    'ALTER TABLE sweety_install_metrics ADD COLUMN baseline_hours BIGINT UNSIGNED NULL DEFAULT NULL AFTER total_hours',
    'SELECT 1'
);
PREPARE sweety_baseline_hours_statement FROM @sweety_baseline_hours_sql;
EXECUTE sweety_baseline_hours_statement;
DEALLOCATE PREPARE sweety_baseline_hours_statement;

SET @sweety_has_created_at = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'sweety_install_metrics'
      AND column_name = 'created_at'
);
SET @sweety_created_at_sql = IF(
    @sweety_has_created_at = 0,
    'ALTER TABLE sweety_install_metrics ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER baseline_hours',
    'SELECT 1'
);
PREPARE sweety_created_at_statement FROM @sweety_created_at_sql;
EXECUTE sweety_created_at_statement;
DEALLOCATE PREPARE sweety_created_at_statement;

-- NULL is a recoverable migration sentinel. If DDL autocommits and a later
-- statement is interrupted, rerunning fills only unfinished legacy rows.
-- Zero is a valid baseline and is therefore never treated as a sentinel.
UPDATE sweety_install_metrics
SET baseline_hours = total_hours, created_at = CURRENT_TIMESTAMP()
WHERE baseline_hours IS NULL;

ALTER TABLE sweety_install_metrics
MODIFY COLUMN baseline_hours BIGINT UNSIGNED NOT NULL DEFAULT 0;

SET @sweety_has_created_at_index = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'sweety_install_metrics'
      AND index_name = 'idx_sweety_install_metrics_created_at'
);
SET @sweety_created_at_index_sql = IF(
    @sweety_has_created_at_index = 0,
    'CREATE INDEX idx_sweety_install_metrics_created_at ON sweety_install_metrics (created_at)',
    'SELECT 1'
);
PREPARE sweety_created_at_index_statement FROM @sweety_created_at_index_sql;
EXECUTE sweety_created_at_index_statement;
DEALLOCATE PREPARE sweety_created_at_index_statement;

CREATE TABLE IF NOT EXISTS sweety_metrics_totals (
    id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    total_hours BIGINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- VALUES() remains supported by the deployed Synology MariaDB version.
INSERT INTO sweety_metrics_totals (id, total_hours)
SELECT 1, COALESCE(SUM(total_hours), 0)
FROM sweety_install_metrics
ON DUPLICATE KEY UPDATE id = VALUES(id);

CREATE TABLE IF NOT EXISTS sweety_metrics_daily_registrations (
    registration_date DATE NOT NULL PRIMARY KEY,
    registration_count INT UNSIGNED NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
