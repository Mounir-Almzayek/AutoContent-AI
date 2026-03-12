#!/usr/bin/env bash
# Dependency security audit — run before deploy. Exit non-zero if vulnerabilities found.
set -e
pip install -q pip-audit
pip-audit -r requirements.txt
