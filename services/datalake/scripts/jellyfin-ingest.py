#!/usr/bin/env python3
"""Jellyfin → DuckDB ingest script for personal data lake."""

import json
import os
import sys
import urllib.request
from datetime import datetime

JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://localhost:8096")
JELLYFIN_API_KEY = os.environ.get("JELLYFIN_API_KEY", "1ccf620dddba80946a086e11028beea66a6eec0753cc83e14693751c8957ed59")
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", os.path.expanduser("~/datalake/datalake.duckdb"))

def jf_get(path, params=None):
    """GET request to Jellyfin API."""
    url = f"{JELLYFIN_URL}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{qs}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"MediaBrowser Token={JELLYFIN_API_KEY}"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def create_tables(conn):
    """Create Jellyfin tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jellyfin_library (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            item_type VARCHAR NOT NULL,
            production_year INTEGER,
            community_rating DECIMAL(4,2),
            official_rating VARCHAR,
            genres VARCHAR,
            runtime_minutes INTEGER,
            studios VARCHAR,
            overview TEXT,
            date_created TIMESTAMP,
            premiere_date DATE,
            series_name VARCHAR,
            season_name VARCHAR,
            episode_index INTEGER,
            file_size_gb DECIMAL(8,2),
            container VARCHAR,
            video_codec VARCHAR,
            audio_codec VARCHAR,
            resolution VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("CREATE SEQUENCE IF NOT EXISTS jellyfin_playback_seq START 1")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jellyfin_playback (
            id INTEGER PRIMARY KEY DEFAULT (nextval('jellyfin_playback_seq')),
            user_name VARCHAR NOT NULL,
            date DATE NOT NULL,
            minutes_watched INTEGER NOT NULL,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_name, date)
        )
    """)

    # Views
    conn.execute("""
        CREATE OR REPLACE VIEW jellyfin_library_summary AS
        SELECT 
            item_type,
            COUNT(*) as total_items,
            ROUND(SUM(file_size_gb), 2) as total_size_gb,
            ROUND(AVG(community_rating), 2) as avg_rating,
            ROUND(AVG(runtime_minutes), 0) as avg_runtime
        FROM jellyfin_library
        GROUP BY item_type
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW jellyfin_genre_stats AS
        SELECT 
            genre,
            COUNT(*) as count,
            ROUND(AVG(community_rating), 2) as avg_rating,
            ROUND(SUM(file_size_gb), 2) as total_size_gb
        FROM (
            SELECT UNNEST(string_split(genres, ',')) as genre, community_rating, file_size_gb
            FROM jellyfin_library
            WHERE genres IS NOT NULL AND genres != ''
        )
        GROUP BY genre
        ORDER BY count DESC
    """)

def ingest_items(conn, item_type, include_type):
    """Ingest items of a given type."""
    fields = "DateCreated,Genres,CommunityRating,OfficialRating,RunTimeTicks,ProductionYear,Studios,Overview,PremiereDate,SeriesName,SeasonName,IndexNumber,MediaSources"
    data = jf_get("/Items", {
        "Recursive": "true",
        "IncludeItemTypes": include_type,
        "Fields": fields,
        "Limit": "500",
        "SortBy": "DateCreated",
        "SortOrder": "Descending"
    })

    items = data.get("Items", [])
    count = 0

    for item in items:
        item_id = item.get("Id", "")
        name = item.get("Name", "")
        year = item.get("ProductionYear")
        rating = item.get("CommunityRating")
        official_rating = item.get("OfficialRating")
        genres = ",".join(item.get("Genres", []))
        rt_ticks = item.get("RunTimeTicks", 0)
        runtime = round(rt_ticks / 600000000) if rt_ticks else None
        studios = ",".join([s.get("Name", "") for s in item.get("Studios", [])])
        overview = item.get("Overview", "")
        date_created = item.get("DateCreated", "")[:19] if item.get("DateCreated") else None
        premiere = item.get("PremiereDate", "")[:10] if item.get("PremiereDate") else None
        series_name = item.get("SeriesName")
        season_name = item.get("SeasonName")
        ep_index = item.get("IndexNumber")

        # Media source info
        ms = item.get("MediaSources", [])
        file_size_gb = round(ms[0].get("Size", 0) / 1e9, 2) if ms else None
        container = ms[0].get("Container") if ms else None

        # Video/audio streams
        video_codec = audio_codec = resolution = None
        if ms:
            for stream in ms[0].get("MediaStreams", []):
                if stream.get("Type") == "Video" and not video_codec:
                    video_codec = stream.get("Codec")
                    w = stream.get("Width", 0)
                    h = stream.get("Height", 0)
                    resolution = f"{w}x{h}" if w and h else None
                elif stream.get("Type") == "Audio" and not audio_codec:
                    audio_codec = stream.get("Codec")

        conn.execute("""
            INSERT OR REPLACE INTO jellyfin_library 
            (id, name, item_type, production_year, community_rating, official_rating,
             genres, runtime_minutes, studios, overview, date_created, premiere_date,
             series_name, season_name, episode_index, file_size_gb, container,
             video_codec, audio_codec, resolution, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [item_id, name, item_type, year, rating, official_rating,
              genres, runtime, studios, overview, date_created, premiere,
              series_name, season_name, ep_index, file_size_gb, container,
              video_codec, audio_codec, resolution])
        count += 1

    return count

def ingest_playback(conn):
    """Ingest playback activity from Playback Reporting plugin."""
    try:
        data = jf_get("/user_usage_stats/PlayActivity", {"days": "90"})
    except Exception as e:
        print(f"  Playback stats not available (plugin missing?): {e}")
        return 0

    count = 0
    for user in data:
        user_name = user.get("user_name", "")
        if user_name == "labels_user":
            continue
        usage = user.get("user_usage", {})
        for date_str, minutes in usage.items():
            if minutes > 0:
                conn.execute("""
                    INSERT INTO jellyfin_playback (user_name, date, minutes_watched, ingested_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_name, date) DO UPDATE SET 
                        minutes_watched = EXCLUDED.minutes_watched,
                        ingested_at = CURRENT_TIMESTAMP
                """, [user_name, date_str, minutes])
                count += 1
    return count

def ingest_activity(conn):
    """Ingest activity log and parse playback sessions."""
    import re
    
    # Create table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jellyfin_activity (
            id INTEGER PRIMARY KEY,
            event_type VARCHAR NOT NULL,
            user_name VARCHAR,
            user_id VARCHAR,
            item_name VARCHAR,
            device VARCHAR,
            timestamp TIMESTAMP NOT NULL,
            severity VARCHAR,
            raw_name TEXT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW jellyfin_watch_sessions AS
        WITH starts AS (
            SELECT id, user_name, item_name, device, timestamp as start_time,
                   LEAD(timestamp) OVER (PARTITION BY user_name, item_name ORDER BY timestamp) as next_start
            FROM jellyfin_activity
            WHERE event_type = 'VideoPlayback'
        ),
        stops AS (
            SELECT user_name, item_name, timestamp as stop_time
            FROM jellyfin_activity
            WHERE event_type = 'VideoPlaybackStopped'
        )
        SELECT 
            s.user_name,
            s.item_name,
            s.device,
            s.start_time,
            MIN(st.stop_time) as stop_time,
            ROUND(EXTRACT(EPOCH FROM (MIN(st.stop_time) - s.start_time)) / 60.0, 1) as duration_minutes
        FROM starts s
        LEFT JOIN stops st ON st.user_name = s.user_name 
            AND st.item_name = s.item_name
            AND st.stop_time > s.start_time
            AND (s.next_start IS NULL OR st.stop_time <= s.next_start)
        GROUP BY s.user_name, s.item_name, s.device, s.start_time
        HAVING MIN(st.stop_time) IS NOT NULL
        ORDER BY s.start_time DESC
    """)

    conn.execute("""
        CREATE OR REPLACE VIEW jellyfin_user_stats AS
        SELECT 
            user_name as usuario,
            COUNT(DISTINCT item_name) as titulos_assistidos,
            COUNT(*) as sessoes,
            ROUND(SUM(duration_minutes), 0) as minutos_total,
            ROUND(SUM(duration_minutes) / 60.0, 1) as horas_total,
            MAX(start_time) as ultima_sessao
        FROM jellyfin_watch_sessions
        WHERE duration_minutes > 0 AND duration_minutes < 600
        GROUP BY user_name
        ORDER BY horas_total DESC
    """)

    # Fetch all activity log entries
    all_entries = []
    start_index = 0
    limit = 100
    while True:
        data = jf_get("/System/ActivityLog/Entries", {"Limit": str(limit), "StartIndex": str(start_index)})
        items = data.get("Items", [])
        all_entries.extend(items)
        if len(items) < limit:
            break
        start_index += limit

    # Parse patterns: "user está reproduzindo TITLE em DEVICE" / "user parou de reproduzir TITLE em DEVICE"
    play_re = re.compile(r'^(.+?) está reproduzindo (.+?) em (.+)$')
    stop_re = re.compile(r'^(.+?) parou de reproduzir (.+?) em (.+)$')
    
    count = 0
    for entry in all_entries:
        entry_type = entry.get("Type", "")
        if "Playback" not in entry_type:
            continue
        
        entry_id = entry.get("Id", 0)
        name = entry.get("Name", "")
        user_id = entry.get("UserId", "")
        timestamp = entry.get("Date", "")[:19]
        severity = entry.get("Severity", "")
        
        # Parse user, item, device from Name
        user_name = item_name = device = None
        m = play_re.match(name) or stop_re.match(name)
        if m:
            user_name = m.group(1)
            item_name = m.group(2)
            device = m.group(3)
        
        conn.execute("""
            INSERT OR REPLACE INTO jellyfin_activity 
            (id, event_type, user_name, user_id, item_name, device, timestamp, severity, raw_name, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [entry_id, entry_type, user_name, user_id, item_name, device, timestamp, severity, name])
        count += 1
    
    return count

def main():
    try:
        import duckdb
    except ImportError:
        os.system("pip3 install duckdb -q")
        import duckdb

    print(f"[{datetime.now().strftime('%H:%M')}] Jellyfin ingest starting...")
    print(f"  Jellyfin: {JELLYFIN_URL}")
    print(f"  DuckDB: {DUCKDB_PATH}")

    # Retry logic: DuckDB só permite 1 writer — espera até 3 tentativas
    import time as _time
    conn = None
    for _attempt in range(1, 4):
        try:
            conn = duckdb.connect(DUCKDB_PATH)
            break
        except Exception as _e:
            if _attempt == 3:
                raise
            print(f"  [WARN] DuckDB lock conflict (tentativa {_attempt}/3): {_e}")
            _time.sleep(30)
    create_tables(conn)

    movies = ingest_items(conn, "Movie", "Movie")
    print(f"  Movies: {movies} ingested")

    series = ingest_items(conn, "Series", "Series")
    print(f"  Series: {series} ingested")

    episodes = ingest_items(conn, "Episode", "Episode")
    print(f"  Episodes: {episodes} ingested")

    playback = ingest_playback(conn)
    print(f"  Playback records: {playback}")

    activity = ingest_activity(conn)
    print(f"  Activity events: {activity}")

    # Summary
    result = conn.execute("SELECT item_type, COUNT(*) FROM jellyfin_library GROUP BY item_type").fetchall()
    total_size = conn.execute("SELECT ROUND(SUM(file_size_gb), 2) FROM jellyfin_library").fetchone()[0]
    
    print(f"\n  Library totals:")
    for row in result:
        print(f"    {row[0]}: {row[1]}")
    print(f"    Total size: {total_size} GB")

    conn.close()
    print(f"[{datetime.now().strftime('%H:%M')}] Jellyfin ingest complete!")

if __name__ == "__main__":
    main()
