# -*- coding: utf-8 -*-

import os
import requests
import pandas as pd

from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
from supabase import create_client

# -----------------------------
# Supabase connection
# -----------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# Current scrape time
# -----------------------------

scraped_at = datetime.now(ZoneInfo("Europe/Brussels")).isoformat(timespec="seconds")

print(f"Scrape run time: {scraped_at}")

# -----------------------------
# Scrape quotes
# -----------------------------

base_url = "https://quotes.toscrape.com/"
current_url = base_url

all_quotes_data = []

while True:
    print(f"Scraping: {current_url}")

    response = requests.get(current_url, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    for item in soup.select(".quote"):
        quote_el = item.select_one(".text")
        author_el = item.select_one(".author")
        tag_els = item.select(".tag")

        quote = quote_el.get_text(strip=True) if quote_el else None
        author = author_el.get_text(strip=True) if author_el else None
        tags = ", ".join(tag.get_text(strip=True) for tag in tag_els)

        all_quotes_data.append({
            "quote": quote,
            "author": author,
            "tags": tags,
            "scraped_at": scraped_at
        })

    next_button = soup.select_one("li.next a")

    if next_button:
        current_url = urljoin(base_url, next_button["href"])
    else:
        break

# -----------------------------
# Save CSV
# -----------------------------

df = pd.DataFrame(all_quotes_data)
df["scraped_at"] = df["scraped_at"].astype(str)

df.to_csv("my_dataset.csv", index=False, encoding="utf-8")

print(f"Scraped {len(df)} rows.")

# -----------------------------
# Insert all rows as logs
# -----------------------------

rows = df.to_dict(orient="records")

if not rows:
    print("No rows found. Nothing inserted.")
else:
    try:
        print("Trying to insert rows into Supabase...")

        result = supabase.table("quotes").insert(rows).execute()

        print("Insert request finished.")
        print(f"Inserted rows returned by Supabase: {len(result.data or [])}")
        print(f"scraped_at used: {scraped_at}")

    except Exception as e:
        print("❌ Supabase insert failed.")
        print("Error details:")
        print(e)
        raise
