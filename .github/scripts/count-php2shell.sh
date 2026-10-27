#!/usr/bin/env bash
# Count PHP2Shell findings in a QScanner JSON report directory.
#
# Usage: count-php2shell.sh REPORT_DIR QSCANNER_EXIT_CODE
# Reads PHP2SHELL_QIDS and PHP2SHELL_CVES (comma separated) from the environment and prints
# report=true|false and hits=<n> for $GITHUB_OUTPUT. Exit 40 from qscanner means the backend
# did not return the vulnerability report in time, so report=false and the caller decides.
set -uo pipefail

dir="$1"
rc="$2"

if [[ "$rc" -eq 40 ]]; then
  echo "::warning::QScanner could not fetch the vulnerability report in time (exit 40)" >&2
  echo "report=false"
  echo "hits=0"
  exit 0
fi
if [[ "$rc" -ne 0 ]]; then
  echo "::error::qscanner exited $rc" >&2
  exit "$rc"
fi

report=$(ls "$dir"/*-Report.json 2>/dev/null | head -1)
if [[ -z "$report" ]]; then
  echo "::warning::No QScanner Report.json in $dir" >&2
  echo "report=false"
  echo "hits=0"
  exit 0
fi

hits=$(jq --arg qids "$PHP2SHELL_QIDS" --arg cves "$PHP2SHELL_CVES" '
  ($qids | split(",") | map(tonumber)) as $q
  | ($cves | split(",")) as $c
  | [.VulnerabilityReport.details[]?
     | select((.qid as $id | $q | index($id)) or ((.cveids // []) | any(. as $x | $c | index($x))))]
  | length' "$report")
echo "report=true"
echo "hits=$hits"
