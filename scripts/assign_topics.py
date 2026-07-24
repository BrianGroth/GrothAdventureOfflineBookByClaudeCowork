"""Assign every entry a book chapter (topic) for the topic-based table of contents.

Two layers:
1. CURATED — hand-picked chapters, keyed by permalink slug (stable across
   databases and re-imports). These were curated by reading each post.
2. AUTO_RULES — keyword scoring for every entry not in CURATED (the full
   2018+ archive and any newly synced post). Title hits count 3x, body hits
   1x; the best-scoring chapter wins, ties go to the earlier rule. Entries
   with no signal land in the "New Adventures" fallback chapter.

Chapters are stored as tags (category='collection', slug 'topic-*');
curated links get EntryTag.auto=0, keyword-assigned ones auto=1.
Re-runnable: clears and re-applies all topic assignments.

To override an auto assignment: add the post's permalink slug to CURATED
and re-run. The script prints fallback entries so you can file them.

Usage (from project root):
    python scripts/assign_topics.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "db" / "scrapbook.sqlite"

# slug -> (label, emoji, tagline, color, order)
# Chapter order roughly follows the life the archive tells: the Bay Area
# years first, then the move to the Netherlands, then the wider world.
TOPICS = {
    "topic-bayarea": (
        "The Bay Area Years", "🌉",
        "Home in San Francisco and San Jose — city life, ballparks, and California road trips",
        "#d97706", 1,
    ),
    "topic-lowlands": (
        "Life in the Lowlands", "🌷",
        "Daily life, Dutch quirks, and discoveries around Amsterdam & Haarlem",
        "#c96f2f", 2,
    ),
    "topic-seasons": (
        "Through the Seasons", "🍂",
        "Tulips, fall colors, and first frosts — the turning year",
        "#b58900", 3,
    ),
    "topic-piper": (
        "Piper & Friends", "🐾",
        "Poodles, highland cows, wild horses, and the neighborhood deer",
        "#6b8c6b", 4,
    ),
    "topic-art": (
        "Art & Curiosities", "🎨",
        "Murals, sculptures, gable stones, museums, satellites, and things worth a second look",
        "#7c3aed", 5,
    ),
    "topic-transport": (
        "Planes, Trains & Bicycles", "🚲",
        "The curious ways the world gets around",
        "#3d7ea6", 6,
    ),
    "topic-europe": (
        "European Escapes", "🏰",
        "City breaks and road trips across the continent",
        "#8e5ba6", 7,
    ),
    "topic-japan": (
        "Adventures in Japan", "🗾",
        "Two trips east: Tokyo, Kyoto, Osaka, Nara & Mt. Fuji",
        "#c0392b", 8,
    ),
    "topic-downunder": (
        "Farther Afield", "🦘",
        "Australia, New Zealand, Singapore, Dubai, Israel & the Moroccan Sahara",
        "#a8622d", 9,
    ),
    "topic-america": (
        "American Adventures", "🗽",
        "Across the States: New York, Chicago, Vegas, Minnesota lakes & mountain snow",
        "#34698a", 10,
    ),
    "topic-sunshine": (
        "Sunshine Getaways", "🏝️",
        "Jersey, Tenerife, Malta & Turkey — warm light and open water",
        "#16a085", 11,
    ),
    "topic-celebrations": (
        "Celebrations & Milestones", "🎉",
        "Anniversaries, holidays, and moments worth marking",
        "#b3436c", 12,
    ),
}

FALLBACK = "topic-new"
FALLBACK_ROW = ("New Adventures", "✨", "Stories not yet filed into a chapter", "#8b6f4e", 99)

# permalink slug -> topic slug (hand-curated by reading each post)
CURATED = {
    "jersey-day-2": "topic-sunshine",
    "jersey-west-coast": "topic-sunshine",
    "jersey-wedding-day": "topic-sunshine",
    "jersey-part-1": "topic-sunshine",
    "hot-day-in-amsterdam": "topic-lowlands",
    "new-benches-in-amsterdam": "topic-lowlands",
    "mountain-climbing-at-80": "topic-america",
    "new-small-electric-cars-in-amsterdam": "topic-transport",
    "scottish-cows-ayrshire-poodles": "topic-piper",
    "random-amsterdam-things": "topic-lowlands",
    "happy-poodle-on-the-amstel": "topic-piper",
    "fall-colors-in-amsterdam-2": "topic-seasons",
    "amsterdam-marathon": "topic-lowlands",
    "october-colors": "topic-seasons",
    "flying-over-san-francisco": "topic-america",
    "pre-winter-scenes": "topic-seasons",
    "holiday-lights-are-starting-up-3": "topic-celebrations",
    "a-dutch-school-bus": "topic-transport",
    "rainy-dog-walk": "topic-piper",
    "touring-amsterdam": "topic-lowlands",
    "peanut-butter-store-in-amsterdam": "topic-lowlands",
    "february-evening-stroll": "topic-seasons",
    "distilling-rum-in-amsterdam": "topic-lowlands",
    "two-days-in-dublin": "topic-europe",
    "flower-time-in-amsterdam": "topic-seasons",
    "beach-shacks-at-zandvoort": "topic-lowlands",
    "champagne-roadtrip-may-2023": "topic-europe",
    "bicycle-towing": "topic-transport",
    "robot-cleaner-at-schiphol": "topic-transport",
    "escape-to-brookhaven-ny": "topic-america",
    "new-art-in-amsterdam-zuid": "topic-lowlands",
    "highland-cattle-in-the-netherlands": "topic-piper",
    "hiking-in-the-alsace-france-region": "topic-europe",
    "strasbourg-september-2023": "topic-europe",
    "wild-horses-cows": "topic-piper",
    "art-books": "topic-lowlands",
    "griffith-observatory": "topic-america",
    "eurostar-challenges": "topic-transport",
    "made-it-to-london": "topic-celebrations",
    "lille-france": "topic-europe",
    "a-cold-day-in-lille": "topic-europe",
    "our-new-place": "topic-lowlands",
    "my-walking-commute-in-london": "topic-europe",
    "keukenhof": "topic-seasons",
    "piper-in-the-blue-bells": "topic-piper",
    "unplanned-visit-to-tokyo-disney-sea": "topic-japan",
    "off-to-kyoto": "topic-japan",
    "kyoto-weekend": "topic-japan",
    "my-fuji-from-the-shinkansen-train": "topic-japan",
    "a-day-in-asakusa-tokyo": "topic-japan",
    "tsukuji-outer-market": "topic-japan",
    "lunch-in-yokohama": "topic-japan",
    "weekend-in-madrid": "topic-europe",
    "a-few-days-in-dublin-june-2024": "topic-europe",
    "elswout-netherlands": "topic-lowlands",
    "day-1-in-budapest": "topic-europe",
    "dat-2-in-budapest": "topic-europe",
    "budapest-day-4": "topic-europe",
    "ai-view-of-this-site": "topic-celebrations",
    "the-alkmaar-cheese-market": "topic-lowlands",
    "a-week-in-nyc": "topic-america",
    "24-hours-in-paris-2": "topic-europe",
    "the-mail-rail": "topic-transport",
    "car-wash-in-the-netherlands": "topic-lowlands",
    "weekend-in-osaka": "topic-japan",
    "kyoto-for-a-few-days": "topic-japan",
    "nara-with-deer": "topic-japan",
    "a-week-in-osaka": "topic-japan",
    "a-few-days-in-madrid": "topic-europe",
    "afternoon-in-amsterdam": "topic-lowlands",
    "sams-bowl": "topic-celebrations",
    "spring-is-coming-to-the-netherlands": "topic-seasons",
    "canal-ride-in-haarlem": "topic-lowlands",
    "25th-anniversary": "topic-celebrations",
    "but-building-hutten-bouwen": "topic-lowlands",
    "weekend-in-paris": "topic-europe",
    "june-in-the-netherlands": "topic-seasons",
    "a-day-in-singapore": "topic-downunder",
    "a-day-in-auckland-nz": "topic-downunder",
    "rotorua-nz-road-trip": "topic-downunder",
    "a-few-days-in-sydney": "topic-downunder",
    "adventures-in-cairns": "topic-downunder",
    "a-day-in-the-changi-airport-singapore": "topic-downunder",
    "a-few-days-in-nyc": "topic-america",
    "piper-in-amsterdam-2": "topic-piper",
    "hiking-with-the-deer": "topic-piper",
    "put-stop-on-the-way-to-f1": "topic-transport",
    "charging-our-volvo-c40": "topic-transport",
    "my-dreamforce-2025": "topic-america",
    "a-happy-piper-2": "topic-piper",
    "cologne-koln-christmas-markets": "topic-celebrations",
    "december-dublin": "topic-europe",
    "2025-travel-statistics": "topic-celebrations",
    "new-years-in-brighton": "topic-celebrations",
    "hello-las-vegas": "topic-america",
    "sting-in-las-vegas": "topic-america",
    "tenerife-february-2026": "topic-sunshine",
    "malta-march-2026": "topic-sunshine",
    "spring-in-the-netherlands": "topic-seasons",
    "turkey-may-2026": "topic-sunshine",
    "our-cows-horses": "topic-piper",
    # ── Curated strays from the 2018+ archive ──
    "assembling-clean-water-filters": "topic-celebrations",
    "our-garden-in-3d": "topic-lowlands",
    "new-phone-test": "topic-lowlands",
    "hiking-with-mushrooms": "topic-lowlands",
    "please-play": "topic-piper",
    "3000-cabernet-sauvignon-1998": "topic-celebrations",
    "we-have-a-3rd-pet": "topic-piper",
    # ── Photo-only posts (no text to classify) from the 2013–2017 archive ──
    # The 2016 puppy era: a long run of captionless dog photos.
    "play-time": "topic-piper",
    "finally-a-calm-moment": "topic-piper",
    "first-bath": "topic-piper",
    "never-enough-play-time": "topic-piper",
    "getting-along": "topic-piper",
    "beach-day-without-the-little-sister": "topic-piper",
    "rough-life": "topic-piper",
    "this-never-gets-old": "topic-piper",
    "good-sit": "topic-piper",
    "my-daughter-is-an-outstanding-student": "topic-piper",
    "hi": "topic-piper",
    "the-regal-boy": "topic-piper",
    "walking": "topic-piper",
    "almost-hidden": "topic-piper",
    "waiting": "topic-piper",
    "who-has-the-upper-hand": "topic-piper",
    "my-pit-girlfriend": "topic-piper",
    "sitting-on-a-bench-together": "topic-piper",
    "long-hair-windy-day": "topic-piper",
    "they-are-related-to-gail": "topic-piper",
    # Bay Area everyday life
    "and-more": "topic-bayarea",
    "good-view": "topic-bayarea",
    "sunday-afternoon": "topic-bayarea",
    "waiting-for-pho": "topic-bayarea",
    "bridge-demolition": "topic-bayarea",
    "back-to-the-fog": "topic-bayarea",
    "hello-world-2": "topic-bayarea",
    "when-you-think-youve-seen-it-all": "topic-bayarea",
    "construction-has-started": "topic-bayarea",
    "construction-monster": "topic-bayarea",
    "a-different-perspective": "topic-bayarea",
    "ice-cream-in-the-mail": "topic-bayarea",
    "colors-of-the-groth-household": "topic-bayarea",
    "improved-walk-sign": "topic-bayarea",
    # Netherlands everyday life
    "great-beach-day": "topic-lowlands",
    "beach-day": "topic-lowlands",
    "zoom-in-to-see-these-donuts-gone-wrong-or-good": "topic-lowlands",
    "where-am-i-now": "topic-lowlands",
    "saturday-in-the-park-3": "topic-lowlands",
    "ice-breaking-tour-boat": "topic-lowlands",
    # Getting around
    "part-of-the-morning-commute": "topic-transport",
    "rental-for-a-day": "topic-transport",
    # Gatherings, family, and things tasted
    "bartending-class": "topic-celebrations",
    "mixology-class": "topic-celebrations",
    "douglas-fir-makes-for-awful-brandy": "topic-celebrations",
    "tool-bag-thanks-mom": "topic-celebrations",
    "june-1972": "topic-celebrations",
    "human-the-movie": "topic-celebrations",
    # Elsewhere in the States
    "slc": "topic-america",
    "camp-site": "topic-america",
    "quick-la-visit": "topic-america",
    # Gadget teardown
    "guts-of-an-amazon-kindle-fire": "topic-art",
}

# Ordered rules: earlier rules win ties. Keywords match whole words,
# case-insensitively, in the title (3 points) and body text (1 point).
#
# Order matters. Distinctive destinations come first; the recurring art
# projects come before place rules so "30 Days of Outdoor Art: Day 5 …next
# to AT&T Park" files under Art rather than the Bay Area; and the two
# "home" chapters (Bay Area, Lowlands) sit last as catch-alls for the
# everyday posts of each era.
AUTO_RULES = [
    ("topic-japan", [
        "tokyo", "kyoto", "osaka", "nara", "japan", "japanese", "shinkansen",
        "yokohama", "fuji", "asakusa", "sake", "shibuya", "ginza",
    ]),
    ("topic-downunder", [
        "sydney", "auckland", "cairns", "singapore", "zealand", "australia",
        "rotorua", "changi", "dubai", "tel aviv", "jerusalem", "israel",
        "jaffa", "burj", "persian gulf", "ramadan", "koala", "wombat",
        "morocco", "marrakesh", "marrakech", "sahara", "saharan", "atlas mountains",
        "camel", "camels", "dromedary", "kasba", "casbah", "merzouga", "emirates",
    ]),
    ("topic-sunshine", [
        "jersey", "tenerife", "malta", "canary", "cappadocia", "turkey",
        "valletta", "sliema", "mallorca", "ibiza",
    ]),
    ("topic-art", [
        "art", "artwork", "mural", "murals", "sculpture", "sculptures",
        "statue", "statues", "graffiti", "gable stone", "gable stones",
        "gevelsteen", "street art", "painting", "paintings", "painted",
        "museum", "museums", "gallery", "exhibit", "exhibition", "mosaic",
        "satellite", "satellites", "planet labs", "rocket", "spaceship",
        "planetarium", "lego", "virtual reality",
    ]),
    ("topic-america", [
        "nyc", "new york", "brooklyn", "manhattan", "vegas", "chicago",
        "seattle", "utah", "alta", "snowbird", "loveland", "niagara",
        "toronto", "minnesota", "pickerel", "pickeral", "dreamforce", "jfk",
        "twa", "helens", "oregon", "portland", "boston", "texas", "florida",
        "denver", "colorado", "49ers", "levi stadium", "sharks hockey",
        "warren miller", "gi joe", "los angeles", "beverly hills", "tar pits",
        "jones island", "san juan islands",
    ]),
    ("topic-europe", [
        "london", "paris", "dublin", "madrid", "budapest", "lille", "lisbon",
        "porto", "portugal", "heidelberg", "stuttgart", "frankfurt",
        "cologne", "copenhagen", "stockholm", "zurich", "prague", "barcelona",
        "dusseldorf", "düsseldorf", "malaga", "málaga", "ireland", "france",
        "germany", "german", "spain", "champagne", "alsace", "strasbourg",
        "brighton", "cascais", "sintra", "czech", "vienna", "berlin",
        "munich", "italy", "italian", "rome", "edinburgh", "scotland",
        "venice", "verona", "florence", "cinque terre", "riomaggiore",
        "vernazza", "monterosso", "borough market", "england", "wales",
    ]),
    ("topic-transport", [
        "bike", "bikes", "bicycle", "bicycles", "biking", "tram", "trams",
        "train", "trains", "klm", "boeing", "airbus", "airport", "schiphol",
        "eurostar", "e-golf", "electric car", "electric cars", "charging",
        "cargo", "scooter", "karts", "metro", "cockpit", "vehicle",
        "vehicles", "wheeler", "spare tire", "ferry", "kayak", "kayaking",
        "sailing", "catamaran", "drawbridge", "draw bridge",
    ]),
    ("topic-piper", [
        "piper", "busby", "poodle", "poodles", "dog", "dogs", "puppy",
        "puppies", "pup", "pups", "cow", "cows", "horse", "horses", "deer",
        "swan", "swans", "bison", "buffalo", "wildlife", "parrot", "parrots",
        "fox", "clydesdale", "clydesdales", "squirrel", "groomed", "grooming",
        "haircut", "haircuts", "tug-of-war", "sibling", "leash", "kennel",
        "pigeons", "seagull", "sea lions", "worm", "worms",
    ]),
    ("topic-celebrations", [
        "christmas", "sinterklaas", "king's day", "kings day", "pride",
        "new year", "thanksgiving", "birthday", "birthdays", "anniversary",
        "mother's day", "father's day", "easter", "halloween", "holiday",
        "holidays", "xmas", "fireworks", "wedding", "light festival",
        "graduation", "valentine", "4th of july", "parade",
    ]),
    ("topic-seasons", [
        "spring", "springtime", "tulip", "tulips", "autumn", "fall colors",
        "snow", "snowy", "winter", "summer", "flower", "flowers", "daffodil",
        "blossom", "frozen", "freeze", "freezing", "seasons", "leaves",
        "rose", "roses",
    ]),
    ("topic-bayarea", [
        "san francisco", "bay bridge", "castro", "san jose", "at&t park",
        "giants", "warriors", "oakland", "berkeley", "monterey", "sonoma",
        "presidio", "ucsf", "silicon valley", "palo alto", "muni",
        "caltrain", "bart", "marin", "napa", "tahoe", "yosemite",
        "california", "santa barbara", "palm springs", "hollywood",
        "hearst", "candlestick", "delores park", "dolores park", "adobe",
        "xactly", "mission bay", "guadalupe", "vta", "the bay",
    ]),
    ("topic-lowlands", [
        "amsterdam", "amsterdamse", "netherlands", "dutch", "holland",
        "zandvoort", "haarlem", "utrecht", "dunes", "amstel", "canal",
        "canals", "rijks", "van gogh", "vondelpark", "noordwijk",
        "albert cuyp", "de pijp", "amstelpark", "north sea", "rotterdam",
        "delft", "leiden", "foodhallen", "a'dam", "elswout", "scheepvaart",
        "garden", "basketball", "car wash", "stroopwafel", "sprinkles",
        "cheese", "windmill", "windmills", "houseboat", "neighbourhood",
    ]),
]

_word_res = {
    topic: [re.compile(r"\b" + re.escape(kw) + r"\b") for kw in kws]
    for topic, kws in AUTO_RULES
}


def slug_of(permalink: str) -> str:
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?$", permalink or "")
    return m.group(4) if m else (permalink or "")


def _normalize(s: str) -> str:
    # Curly apostrophes/quotes would break "father's day"-style keywords
    return s.lower().replace("’", "'").replace("‘", "'")


def auto_topic(title: str, text: str) -> str | None:
    """Best-scoring chapter for an uncurated entry, or None if no signal."""
    title_l = _normalize(title or "")
    text_l = _normalize((text or "")[:2000])
    best_topic, best_score = None, 0
    for topic, _ in AUTO_RULES:
        score = 0
        for rx in _word_res[topic]:
            if rx.search(title_l):
                score += 3
            elif rx.search(text_l):
                score += 1
        if score > best_score:  # strict: ties keep the earlier rule
            best_topic, best_score = topic, score
    return best_topic


def main() -> int:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Upsert topic tags (incl. fallback)
    all_topics = dict(TOPICS)
    all_topics[FALLBACK] = FALLBACK_ROW
    tag_ids = {}
    for slug, (label, _emoji, _tagline, color, _order) in all_topics.items():
        row = cur.execute("SELECT id FROM tag WHERE slug = ?", (slug,)).fetchone()
        if row:
            tag_ids[slug] = row[0]
            cur.execute("UPDATE tag SET label = ?, category = 'collection', color = ? WHERE id = ?",
                        (label, color, row[0]))
        else:
            cur.execute("INSERT INTO tag (slug, label, category, color) VALUES (?, ?, 'collection', ?)",
                        (slug, label, color))
            tag_ids[slug] = cur.lastrowid

    # Clear previous topic assignments, then re-apply everything
    cur.execute(
        "DELETE FROM entry_tag WHERE tag_id IN (SELECT id FROM tag WHERE slug LIKE 'topic-%')"
    )

    entries = cur.execute(
        "SELECT id, permalink, title, substr(text_content, 1, 2000) FROM entry"
    ).fetchall()

    counts: dict[str, int] = {}
    fallback_entries = []
    curated_used = set()
    for entry_id, permalink, title, text in entries:
        s = slug_of(permalink)
        topic = CURATED.get(s)
        manual = topic is not None
        if manual:
            curated_used.add(s)
        else:
            topic = auto_topic(title, text) or FALLBACK
        cur.execute(
            "INSERT OR IGNORE INTO entry_tag (entry_id, tag_id, auto) VALUES (?, ?, ?)",
            (entry_id, tag_ids[topic], 0 if manual else 1),
        )
        counts[topic] = counts.get(topic, 0) + 1
        if topic == FALLBACK:
            fallback_entries.append((entry_id, s, title))

    con.commit()

    print("Chapter assignments:")
    for slug, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {all_topics[slug][0]:<30} {n}")
    print(f"  {'TOTAL':<30} {sum(counts.values())}")

    unused = set(CURATED) - curated_used
    if unused:
        print(f"\nNote: {len(unused)} curated slugs matched no entry: {sorted(unused)[:5]}…"
              if len(unused) > 5 else f"\nNote: curated slugs matched no entry: {sorted(unused)}")

    if fallback_entries:
        print(f"\n{len(fallback_entries)} entries had no keyword signal (in 'New Adventures').")
        print("Give them a home by adding their slug to CURATED in this script:")
        for eid, s, title in fallback_entries:
            print(f'    "{s}": "topic-…",  # {title}')

    return 0


if __name__ == "__main__":
    sys.exit(main())
