#!/bin/sh
ln -sf /usr/local/bin/duckdb /tmp/duckdb
exec /usr/local/bin/supercronic /app/crontab
