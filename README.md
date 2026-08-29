# Housing Listing & Location Scraper

An automated Python scraper for housing rent listings from [Xross House](https://x-house.co.jp/en/). It extracts property names, monthly rents, availability dates, and Google Maps location links, and calculates the exact **walking distance** and **walking duration** to the **Rakuten Main Office (Rakuten Crimson House, Futako-Tamagawa, Tokyo)** into an exportable CSV file.

---

## Table of Contents

- [Features](#features)
- [Installation & Setup](#installation--setup)
- [CLI Arguments Reference](#cli-arguments-reference)
- [Usage Examples](#usage-examples)
  - [1. Default Run](#1-default-run)
  - [2. Custom Search / Filter URL](#2-custom-search--filter-url)
  - [3. Custom Output Directory & Filename (with Timestamps)](#3-custom-output-directory--filename-with-timestamps)
  - [4. Adjust Delay to Avoid Rate Limits](#4-adjust-delay-to-avoid-rate-limits)
  - [5. Visual / Headful Mode](#5-visual--headful-mode)
  - [6. Full Pipeline with Combined Arguments](#6-full-pipeline-with-combined-arguments)
- [Output CSV Data Schema](#output-csv-data-schema)
- [How It Works](#how-it-works)

---

## Features

- **Automatic Timestamp Suffixes**: Filenames are automatically suffixed with readable timestamps (e.g. `data/setagaya_2026-08-29_23-18-01.csv`) so previous scrape runs are never overwritten.
- **Automatic Infinite Scroll & Pagination**: Automatically scrolls and loads 100% of available listings, matching the total count reported by the portal.
- **Polite Crawling & Anti-Blocking**: Built-in polite delay (`--delay`) and exponential backoff retry logic on `429`/`403` or network timeouts.
- **Custom Search URLs**: Pass any search or filter URL from Xross House via `--url`.
- **2-Step Scraping Pipeline**:
  1. Scrapes listing search results (names, rent, availability dates, detail URLs).
  2. Visits each individual property page to extract building addresses and Google Maps links.
- **Accurate Walking Distance & Duration**:
  - Uses Japan's official **GSI** (*Geospatial Information Authority of Japan*) geocoder for accurate address resolution.
  - Queries **OSRM Foot Routing** to compute exact pedestrian walking distance and travel duration to **Rakuten Crimson House** (`35.6104929, 139.6301311`).
  - Generates clickable Google Maps Walking Directions links.
- **Headful & Headless Modes**: Run silently in the background (default) or watch the browser navigate live with `--headful`.
- **Flexible Output Management**: Specify custom directories (`--dir`) and base names (`--name`), with automatic directory creation and extension resolution.

---

## Installation & Setup

### 1. Prerequisites
Ensure you have Python 3.9+ installed.

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

---

## CLI Arguments Reference

| Argument | Shorthand | Default | Description |
| :--- | :--- | :--- | :--- |
| `--url` | `-u` | *Default Setagaya search URL* | Target Xross House search/filter URL to scrape. |
| `--name` | `-n` | `listings` | Base filename for the output CSV (e.g. `setagaya` or `listings`). Readable timestamp will be appended before `.csv`. |
| `--dir` | `-d` | `data` | Directory where the CSV file will be saved. Automatically created if it does not exist. |
| `--no-timestamp` | | `False` | Disable appending timestamp suffix to output filename (e.g. to keep static name). |
| `--delay` | `-w` | `1.5` | Polite delay in seconds between detail page requests (with random jitter) to avoid rate limits. |
| `--output` | `-o` | `None` | Optional explicit full output path (e.g. `reports/custom.csv`). Overrides `--dir` and `--name`. |
| `--headful` | | `False` | Launches a visible Chromium browser window so you can watch the scraper live. |
| `--help` | `-h` | | Displays the help message with all available options. |

---

## Usage Examples

Make sure your virtual environment is active before running commands:
```bash
source venv/bin/activate
```

### 1. Default Run
Scrapes the default search URL and saves to `data/listings_YYYY-MM-DD_HH-MM-SS.csv`:
```bash
python scraper.py
```

### 2. Custom Output Directory & Filename
```bash
# Saves to data/setagaya_under_80k_YYYY-MM-DD_HH-MM-SS.csv
python scraper.py --name setagaya_under_80k

# Saves to reports/august_search_YYYY-MM-DD_HH-MM-SS.csv (creates reports/ folder automatically)
python scraper.py --dir reports --name august_search

# Disable timestamp suffix if you prefer a static filename (data/listings.csv):
python scraper.py --no-timestamp
```

### 3. Custom Search / Filter URL
Pass any custom filter URL (e.g. multi-city search, budget filters, specific stations):
```bash
python scraper.py \
  --url "https://x-house.co.jp/en/fee/?rent_min=&rent_max=80000&gender=no-female&city=%2C67%2C66%2C59..." \
  --name multi_city_search
```

### 4. Adjust Delay to Avoid Rate Limits
Customize the wait time between individual property page requests:
```bash
python scraper.py --delay 2.0
```

### 5. Visual / Headful Mode
Launch a visible browser window on your desktop to observe page loading and interactions in real time:
```bash
python scraper.py --headful
```

### 6. Full Pipeline with Combined Arguments
Combine search URL, custom delay, output directory, custom name, and headful mode:
```bash
python scraper.py \
  --url "https://x-house.co.jp/en/fee/?rent_min=&rent_max=&gender=no-female&date=&sort=room&vacant_room_flg=1&room_type=%2C5&walk=&station=&city=%2C67%2C66%2C59%2C459%2C458" \
  --dir data \
  --name tokyo_multi_city \
  --delay 1.5 \
  --headful
```

---

## Output CSV Data Schema

The generated CSV file contains the following fields:

| Column | Description | Example Value |
| :--- | :--- | :--- |
| `name` | Property title and room number | `AP408 Saison Futako-Tamagawa Part 1 102` |
| `rent` | Monthly rent (JPY) | `62,000 yen` |
| `available_from` | Earliest move-in date | `2027-03-03` |
| `walking_distance` | Pedestrian route distance to Rakuten Crimson House | `1.84 km` |
| `walking_time` | Estimated walking travel duration | `25 mins` / `1 hr 10 min` |
| `google_map_url` | Direct Google Maps search/location URL for the property | `https://www.google.com/maps/search/?api=1&query=...` |
| `google_map_walking_url` | Direct Google Maps walking directions URL to Rakuten Crimson House | `https://www.google.com/maps/dir/?api=1&origin=...&destination=...&travelmode=walking` |
| `detail_url` | Xross House property detail page URL | `https://x-house.co.jp/en/sharehouse/tokyo/city/setagaya/xross-1023/` |

---

## How It Works

1. **Step 1 — Search Results Extraction & Infinite Scroll**:
   - Uses Playwright to load the search page and inspects the total listing count reported by the portal.
   - Automatically scrolls through the page until all batch-loaded cards (e.g. 30, 36, 100+) are rendered into the DOM.
   - Extracts property name, rent, move-in availability date, and the link to each property page.

2. **Step 2 — Enrichment & Distance Calculation**:
   - Visits each property detail page with a polite randomized delay (`--delay`) and exponential backoff retry logic.
   - Geocodes the Japanese address using the Geospatial Information Authority of Japan (GSI) API.
   - Calculates pedestrian walking distance and walking duration to **Rakuten Crimson House** using the OpenStreetMap OSRM Foot Routing engine.
   - Constructs direct Google Maps walking navigation URLs.

3. **Step 3 — CSV Export with Timestamps**:
   - Appends a readable timestamp (e.g. `YYYY-MM-DD_HH-MM-SS`) to ensure runs are versioned and never overwritten.
   - Formats and exports the dataset into UTF-8 encoded CSV in the specified directory.
