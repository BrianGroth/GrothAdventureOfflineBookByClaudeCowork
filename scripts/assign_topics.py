"""Assign each entry a book chapter (topic) for the topic-based table of contents.

Topics were curated by reading every entry. They are stored as tags with
category='collection' and slug 'topic-<name>', with EntryTag.auto=0 so a
re-sync never clobbers them. Re-runnable: clears and re-applies assignments.

Usage (from project root):
    python scripts/assign_topics.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "db" / "scrapbook.sqlite"

# slug -> (label, emoji, tagline, color, order)
TOPICS = {
    "topic-lowlands": (
        "Life in the Lowlands", "🌷",
        "Daily life, Dutch quirks, and discoveries around Amsterdam & Haarlem",
        "#c96f2f", 1,
    ),
    "topic-seasons": (
        "Through the Seasons", "🍂",
        "Tulips, fall colors, and first frosts — the turning year in the Netherlands",
        "#b58900", 2,
    ),
    "topic-piper": (
        "Piper & Friends", "🐾",
        "Poodles, highland cows, wild horses, and the neighborhood deer",
        "#6b8c6b", 3,
    ),
    "topic-transport": (
        "Planes, Trains & Bicycles", "🚲",
        "The curious ways the world gets around",
        "#3d7ea6", 4,
    ),
    "topic-europe": (
        "European Escapes", "🏰",
        "City breaks and road trips across the continent",
        "#8e5ba6", 5,
    ),
    "topic-japan": (
        "Adventures in Japan", "🗾",
        "Two trips east: Tokyo, Kyoto, Osaka, Nara & Mt. Fuji",
        "#c0392b", 6,
    ),
    "topic-downunder": (
        "Down Under & Beyond", "🦘",
        "Singapore, New Zealand & Australia in one great loop",
        "#a8622d", 7,
    ),
    "topic-america": (
        "American Adventures", "🗽",
        "Stateside visits: New York, Vegas, LA & the Pacific Northwest",
        "#34698a", 8,
    ),
    "topic-sunshine": (
        "Sunshine Getaways", "🏝️",
        "Jersey, Tenerife, Malta & Turkey — warm light and open water",
        "#16a085", 9,
    ),
    "topic-celebrations": (
        "Celebrations & Milestones", "🎉",
        "Anniversaries, holidays, and moments worth marking",
        "#b3436c", 10,
    ),
}

# entry id -> topic slug (curated by reading each entry)
ASSIGNMENTS = {
    # ── 2022 ──
    100: "topic-sunshine",      # Jersey, Day 2
    99: "topic-sunshine",       # Jersey, West Coast
    98: "topic-sunshine",       # Jersey, Wedding Day
    97: "topic-lowlands",       # Hot day in Amsterdam
    96: "topic-lowlands",       # New Benches in Amsterdam
    95: "topic-america",        # Mountain Climbing at 80 (Mt. St. Helens)
    94: "topic-transport",      # New Small Electric Cars in Amsterdam
    93: "topic-piper",          # Scottish Cows (Ayrshire) & Poodles
    92: "topic-lowlands",       # Random Amsterdam Things
    91: "topic-piper",          # Happy Poodle on The Amstel
    90: "topic-seasons",        # Fall Colors in Amsterdam
    89: "topic-lowlands",       # Amsterdam Marathon
    88: "topic-seasons",        # October Colors
    87: "topic-america",        # Flying over San Francisco
    86: "topic-seasons",        # Pre-Winter Scenes
    85: "topic-celebrations",   # Holiday lights are starting up
    84: "topic-transport",      # A Dutch School "Bus"
    # ── 2023 ──
    83: "topic-piper",          # Rainy Dog Walk
    82: "topic-lowlands",       # Touring Amsterdam
    81: "topic-lowlands",       # Peanut butter store in Amsterdam
    80: "topic-seasons",        # February Evening Stroll
    79: "topic-lowlands",       # Distilling Rum in Amsterdam
    78: "topic-europe",         # Two Days in Dublin
    77: "topic-seasons",        # Flower Time in Amsterdam
    76: "topic-lowlands",       # Beach Shacks at Zandvoort
    75: "topic-europe",         # Champagne Roadtrip: May 2023
    74: "topic-transport",      # Bicycle Towing
    73: "topic-transport",      # Robot Cleaner at Schiphol
    72: "topic-america",        # Escape to Brookhaven, NY
    71: "topic-lowlands",       # New Art in Amsterdam Zuid
    70: "topic-piper",          # Highland Cattle in the Netherlands
    69: "topic-europe",         # Hiking in the Alsace, France region
    68: "topic-europe",         # Strasbourg, September 2023
    67: "topic-piper",          # Wild Horses & Cows
    66: "topic-lowlands",       # Art & Books
    65: "topic-america",        # Griffith Observatory
    64: "topic-transport",      # Eurostar Challenges
    63: "topic-celebrations",   # Made it to London (New Year's)
    # ── 2024 ──
    62: "topic-europe",         # Lille, France
    61: "topic-europe",         # A Cold Day in Lille
    60: "topic-lowlands",       # Our New Place
    59: "topic-europe",         # My Walking Commute in London
    58: "topic-seasons",        # Keukenhof
    57: "topic-piper",          # Piper in the Blue Bells
    56: "topic-japan",          # Unplanned visit to Tokyo Disney Sea
    55: "topic-japan",          # Off to Kyoto
    54: "topic-japan",          # Kyoto Weekend
    53: "topic-japan",          # Mt. Fuji from the Shinkansen Train
    52: "topic-japan",          # A day in Asakusa, Tokyo
    51: "topic-japan",          # Tsukuji Outer Market
    50: "topic-japan",          # Lunch in Yokohama
    49: "topic-europe",         # Weekend in Madrid
    48: "topic-europe",         # A Few Days in Dublin, June 2024
    47: "topic-lowlands",       # Elswout, Netherlands
    46: "topic-europe",         # Day 1 in Budapest
    45: "topic-europe",         # Day 2 in Budapest
    44: "topic-europe",         # Budapest Day 3
    43: "topic-celebrations",   # AI View of This Site
    42: "topic-lowlands",       # The Alkmaar Cheese Market
    41: "topic-america",        # A Week in NYC
    40: "topic-europe",         # 24 Hours in Paris
    39: "topic-transport",      # The Mail Rail
    38: "topic-lowlands",       # Car Wash in The Netherlands
    37: "topic-japan",          # Weekend in Osaka
    36: "topic-japan",          # Kyoto for a few days
    35: "topic-japan",          # Nara with deer
    34: "topic-japan",          # A week in Osaka
    # ── 2025 ──
    33: "topic-europe",         # A Few Days in Madrid
    32: "topic-lowlands",       # Afternoon in Amsterdam
    31: "topic-celebrations",   # Sam's Bowl
    30: "topic-seasons",        # Spring is coming to the Netherlands
    29: "topic-lowlands",       # Canal Ride in Haarlem
    28: "topic-celebrations",   # 25th Anniversary
    27: "topic-lowlands",       # But Building (hutten bouwen)
    26: "topic-europe",         # Weekend in Paris
    25: "topic-seasons",        # June in the Netherlands
    24: "topic-downunder",      # A day in Singapore
    23: "topic-downunder",      # A Day in Auckland, NZ
    18: "topic-downunder",      # Rotorua, NZ Road Trip
    22: "topic-downunder",      # A Few Days in Sydney
    21: "topic-downunder",      # Adventures in Cairns
    20: "topic-downunder",      # A Day in The Changi Airport (Singapore)
    19: "topic-america",        # A few days in NYC
    17: "topic-piper",          # Piper in Amsterdam
    16: "topic-piper",          # Hiking with the deer
    15: "topic-transport",      # Pit Stop on the way to F1
    14: "topic-transport",      # Charging our Volvo C40
    13: "topic-america",        # My Dreamforce 2025
    12: "topic-piper",          # A Happy Piper
    11: "topic-celebrations",   # Cologne (Köln) Christmas Markets
    10: "topic-europe",         # December Dublin
    9: "topic-celebrations",    # 2025 Travel Statistics
    # ── 2026 ──
    8: "topic-celebrations",    # New Year's in Brighton
    7: "topic-america",         # Hello Las Vegas
    6: "topic-america",         # Sting in Las Vegas
    5: "topic-sunshine",        # Tenerife, February 2026
    4: "topic-sunshine",        # Malta, March 2026
    3: "topic-seasons",         # Spring in the Netherlands
    2: "topic-sunshine",        # Turkey, May 2026
    1: "topic-piper",           # Our Cows & Horses
}


def main() -> int:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Upsert topic tags
    tag_ids = {}
    for slug, (label, emoji, tagline, color, order) in TOPICS.items():
        row = cur.execute("SELECT id FROM tag WHERE slug = ?", (slug,)).fetchone()
        # Encode emoji/tagline/order into label-adjacent fields we have:
        # label stays clean; metadata is served by the book API from this table
        # plus the TOPICS constants mirrored in core/api/routers/book.py.
        if row:
            tag_ids[slug] = row[0]
            cur.execute("UPDATE tag SET label = ?, category = 'collection', color = ? WHERE id = ?",
                        (label, color, row[0]))
        else:
            cur.execute("INSERT INTO tag (slug, label, category, color) VALUES (?, ?, 'collection', ?)",
                        (slug, label, color))
            tag_ids[slug] = cur.lastrowid

    # Clear previous topic assignments, then apply
    cur.execute(
        "DELETE FROM entry_tag WHERE tag_id IN (SELECT id FROM tag WHERE slug LIKE 'topic-%')"
    )

    missing = []
    for entry_id, slug in ASSIGNMENTS.items():
        row = cur.execute("SELECT id, title FROM entry WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            missing.append(entry_id)
            continue
        cur.execute(
            "INSERT OR IGNORE INTO entry_tag (entry_id, tag_id, auto) VALUES (?, ?, 0)",
            (entry_id, tag_ids[slug]),
        )

    # Report entries with no topic (e.g. newly synced posts)
    unassigned = cur.execute("""
        SELECT e.id, e.event_date, e.title FROM entry e
        WHERE e.id NOT IN (
            SELECT et.entry_id FROM entry_tag et
            JOIN tag t ON t.id = et.tag_id WHERE t.slug LIKE 'topic-%'
        )
        ORDER BY e.event_date
    """).fetchall()

    con.commit()

    counts = cur.execute("""
        SELECT t.slug, COUNT(*) FROM entry_tag et JOIN tag t ON t.id = et.tag_id
        WHERE t.slug LIKE 'topic-%' GROUP BY t.slug ORDER BY COUNT(*) DESC
    """).fetchall()
    print("Topic assignments:")
    for slug, n in counts:
        print(f"  {TOPICS[slug][0]:<30} {n}")
    total = sum(n for _, n in counts)
    print(f"  {'TOTAL':<30} {total}")

    if missing:
        print(f"\nWARNING: mapped entry ids not found in DB: {missing}")
    if unassigned:
        print(f"\n{len(unassigned)} entries have no topic (add them to ASSIGNMENTS):")
        for eid, date, title in unassigned:
            print(f"  #{eid} {date} {title}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
