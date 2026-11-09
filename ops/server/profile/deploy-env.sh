# Appended to /home/muttmetrics/.profile  (#93, docs/runbooks/release.md)
# What ops/deploy.py runs to restart, and where it checks the SPA proxy.
export MUTTMETRICS_RESTART_CMD="sudo systemctl restart muttmetrics-api caddy"
export MUTTMETRICS_APP_URL="http://127.0.0.1:8080"
