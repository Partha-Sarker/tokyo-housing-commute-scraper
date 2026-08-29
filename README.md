# Housing Listing & Location Scraper

Automated scraper for housing rent listings from [Xross House](https://x-house.co.jp/en/). It extracts property names, monthly rent, availability dates, and direct Google Maps location links, and calculates the exact **walking distance** and **walking duration** to the **Rakuten Main Office (Rakuten Crimson House, Futako-Tamagawa)** into a CSV file.

---

## Features

- **CLI Search URL Input**: Pass any custom Xross House filter or search URL via `--url`.
- **2-Step Scraping Pipeline**:
  1. Scrapes listing search results (names, rent, availability dates, detail URLs).
  2. Visits each individual property page to extract Google Maps query links.
- **Walking Distance Calculation**:
  - Uses Japan's official GSI (Geospatial Information Authority of Japan) geocoder.
  - Queries OSRM Foot Routing to compute precise pedestrian walking route distance and travel duration to **Rakuten Crimson House** (`35.6104929, 139.6301311`).
  - Generates clickable Google Maps Walking Directions URLs.
- **Headful & Headless Modes**: Run silently in the background or launch a visible browser window with `--headful` to watch the scraping process live.
- **CSV Export**: Outputs clean, structured data in UTF-8 format (`listings.csv`).

---

## Output Data Structure

The generated CSV contains the following fields:

| Column | Description | Example |
| :--- | :--- | :--- |
| `name` | Property / Room Name | `AP408 Saison Futako-Tamagawa Part 1 102` |
| `rent` | Monthly Rent (JPY) | `62,000 yen` |
| `available_from` | Earliest Move-in Date | `2027-03-03` |
| `walking_distance` | Walking Route Distance to Rakuten Office | `1.84 km` |
| `walking_time` | Estimated Walking Duration | `25 mins` |
| `google_map_url` | Direct Google Maps Location Link | `https://www.google.com/maps/search/?api=1&query=...` |
| `google_map_walking_url` | Google Maps Walking Directions Link | `https://www.google.com/maps/dir/?api=1&origin=...&destination=...&travelmode=walking` |
| `detail_url` | Xross House Property URL | `https://x-house.co.jp/en/sharehouse/...` |

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

## How to Run & Scrape Fresh Data

Activate your virtual environment:
```bash
source venv/bin/activate
```

### 1. Standard Scrape with Custom URL
```bash
python scraper.py --url "https://x-house.co.jp/en/fee/?rent_min=&rent_max=&gender=no-female&city=%2C67..."
```

### 2. Headful Mode (Visualize browser actions on screen)
```bash
python scraper.py --url "https://x-house.co.jp/en/fee/..." --headful
```

### 3. Specify Custom CSV Output Path
```bash
python scraper.py --output my_results.csv
```

---

## CLI Options Reference

```text
options:
  -h, --help           Show help message and exit
  --url, -u URL        Target Xross House search URL to scrape (default: predefined search URL)
  --headful            Launch visible browser window to watch scraping in real-time
  --output, -o OUTPUT  Target CSV file path (default: listings.csv)
```
