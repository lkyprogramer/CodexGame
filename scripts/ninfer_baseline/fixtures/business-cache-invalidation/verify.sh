#!/usr/bin/env bash
set -euo pipefail
mkdir -p out
javac -d out $(find src/main/java src/test/java -name "*.java" | sort)
java -cp out ServiceTest
