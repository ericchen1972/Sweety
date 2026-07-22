<?php

$mysqlhost = '127.0.0.1';
$mysqluser = 'replace-with-database-user';
$mysqlpasswd = 'replace-with-database-password';
$mysqldatabase = 'replace-with-database-name';

function get_db(): mysqli
{
    global $mysqlhost, $mysqluser, $mysqlpasswd, $mysqldatabase;
    $mysqli = new mysqli($mysqlhost, $mysqluser, $mysqlpasswd, $mysqldatabase);
    if ($mysqli->connect_error) {
        throw new RuntimeException('Database connection failed.');
    }
    $mysqli->set_charset('utf8mb4');
    return $mysqli;
}
