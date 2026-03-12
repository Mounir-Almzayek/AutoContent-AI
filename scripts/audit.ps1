# Dependency security audit — run before deploy. Exit non-zero if vulnerabilities found.
pip install -q pip-audit
pip-audit -r requirements.txt
if (-not $?) { exit 1 }
