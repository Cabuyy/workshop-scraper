# -*- coding: utf-8 -*-

import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timezone
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
# Scrape quotes
# -----------------------------

base_url = "https://quotes.toscrape.com/"
current_url = base_url

all_quotes_data = []

# This is TEXT, suitable for a Supabase text column
scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

while True:
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
            "scraped_at": str(scraped_at)
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

# Make absolutely sure scraped_at is text
if not df.empty:
    df["scraped_at"] = df["scraped_at"].astype(str)

# -----------------------------
# Save locally as CSV
# -----------------------------

filename = "my_dataset.csv"
df.to_csv(filename, index=False, encoding="utf-8")

# -----------------------------
# Alert: new quotes detected
# -----------------------------

rows = df.to_dict(orient="records")

if not rows:
    print("No rows found.")
else:
    existing_result = supabase.table("quotes").select("quote, author").execute()

    existing_quotes = {
        (item["quote"], item["author"])
        for item in existing_result.data
    }

    new_rows = [
        row for row in rows
        if (row["quote"], row["author"]) not in existing_quotes
    ]

    if new_rows:
        print(f"⚠️ ALERT: {len(new_rows)} new quote(s) found on the site!")

        for row in new_rows:
            print(f"   - {row['quote']} — {row['author']}")

        result = supabase.table("quotes").insert(new_rows).execute()

        print(f"Inserted {len(new_rows)} new quote(s) into Supabase.")
    else:
        print("No new quotes found.")
