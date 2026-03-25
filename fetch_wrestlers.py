#!/usr/bin/env python3
"""
Fetch active Makuuchi wrestlers from the official sumo site,
download their portraits, and update wrestlers.json.
"""

import json
import re
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.sumo.or.jp"
SEARCH_URL = f"{BASE_URL}/EnSumoDataRikishi/search/"
IMAGES_DIR = Path(__file__).parent / "wiki_images"
JSON_PATH = IMAGES_DIR / "wrestlers.json"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; sumo-quiz-scraper/1.0)"})


def fetch(url: str) -> BeautifulSoup:
    resp = SESSION.get(url, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.content, "html.parser")


def get_makuuchi_wrestlers() -> list[dict]:
    """Return list of {name, profile_url} for all Makuuchi wrestlers."""
    soup = fetch(SEARCH_URL)
    table = soup.find("table")
    wrestlers = []
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        name_cell = cells[1]
        link = name_cell.find("a")
        if not link:
            continue
        name = link.get_text(strip=True)
        href = link.get("href", "")
        if "/EnSumoDataRikishi/profile/" in href:
            wrestlers.append({"name": name, "profile_url": BASE_URL + href})
    return wrestlers


def get_portrait_url(profile_url: str) -> str | None:
    """Scrape the 270x474 portrait URL from a wrestler's profile page."""
    soup = fetch(profile_url)
    img = soup.find("img", src=re.compile(r"/img/sumo_data/rikishi/270x474/"))
    if img:
        return BASE_URL + img["src"]
    return None


def download_image(url: str, dest: Path) -> bool:
    """Download image to dest. Returns True on success."""
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"  ERROR downloading {url}: {e}")
        return False


def main():
    IMAGES_DIR.mkdir(exist_ok=True)

    print("Fetching Makuuchi wrestler list...")
    wrestlers = get_makuuchi_wrestlers()
    print(f"Found {len(wrestlers)} wrestlers.\n")

    results = []
    for i, w in enumerate(wrestlers, 1):
        name = w["name"]
        print(f"[{i:02d}/{len(wrestlers)}] {name}")

        portrait_url = get_portrait_url(w["profile_url"])
        if not portrait_url:
            print(f"  WARNING: no portrait found, skipping.")
            continue

        filename = f"{name.replace(' ', '_')}.jpg"
        dest = IMAGES_DIR / filename

        print(f"  Downloading {portrait_url}")
        if download_image(portrait_url, dest):
            print(f"  Saved → {filename}")
            results.append({"name": name, "image": filename})

        time.sleep(0.3)  # be polite

    print(f"\nWriting wrestlers.json ({len(results)} entries)...")
    JSON_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print("Done.")


if __name__ == "__main__":
    main()
