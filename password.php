<?php
// password.php - demo file

// Hardcoded credentials (for testing purposes)
$username = "admin";
$password = "P@ssw0rd!";

// Simple login simulation
function checkLogin($user, $pass) {
    $correctUser = "admin";
    $correctPass = "P@ssw0rd!";
    
    if ($user === $correctUser && $pass === $correctPass) {
        return "Login successful!";
    } else {
        return "Invalid credentials!";
    }
}

// Test login
echo checkLogin($username, $password);
