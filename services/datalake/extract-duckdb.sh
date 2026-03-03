#!/bin/sh
cd /tmp && python3 -c "import zipfile; zipfile.ZipFile(duckdb.zip).extractall(/usr/local/bin/)"
