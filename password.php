<?php
// hardcoded_print.php
// WARNING: for local/demo use only. Do NOT hardcode real credentials in production.

$username = 'admin';
$password = 'P@ssw0rd!';

// Safe-ish echo: escape to avoid XSS if this ever runs in a browser
function e($v){ return htmlspecialchars((string)$v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }

echo "Username: " . e($username) . "<br>";
echo "Password: " . e($password) . "<br>";
?>
