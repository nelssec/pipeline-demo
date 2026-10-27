<?php
// Minimal page so the container has something to serve. The demo is about the PHP runtime
// version in the base image, not this code.
header('Content-Type: application/json');
echo json_encode(['service' => 'php-app', 'php' => PHP_VERSION]);
