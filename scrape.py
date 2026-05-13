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
# This is local Belgium time.
# It is sent to Supabase as TEXT for the scraped_at column.

BRUSSELS_TZ = ZoneInfo("Europe/Brussels")
scraped_at = datetime.now(BRUSSELS_TZ).isoformat(timespec="seconds")

print(f"Current scraped_at value for this run: {scraped_at}")

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

        tags_list = [tag.get_text(strip=True) for tag in tag_els]
        tags_string = ", ".join(tags_list)

        all_quotes_data.append({
            "quote": quote,
            "author": author,
            "tags": tags_string,
            "scraped_at": scraped_at
        })

    next_button = soup.select_one("li.next a")

    if next_button:
        current_url = urljoin(base_url, next_button["href"])
    else:
        break

# -----------------------------
# Create dataframe
# -----------------------------

df = pd.DataFrame(all_quotes_data)

if not df.empty:
    df["scraped_at"] = df["scraped_at"].astype(str)

# -----------------------------
# Save locally as CSV
# -----------------------------

filename = "my_dataset.csv"
df.to_csv(filename, index=False, encoding="utf-8")

print(f"Saved {len(df)} rows to {filename}")

# -----------------------------
# Insert scrape as new log rows
# -----------------------------
# This keeps old rows and adds a new copy every run.
# No duplicate checking.
# No updating old rows.

rows = df.to_dict(orient="records")

if not rows:
    print("No rows found. Nothing inserted.")
else:
    result = supabase.table("quotes").insert(rows).execute()

    print(f"Inserted {len(rows)} new log row(s) into Supabase.")
    print(f"scraped_at used for this run: {scraped_at}")
