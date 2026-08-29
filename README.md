# Housing Listing & Location Scraper

Automated scraper for housing rent listings from [Xross House](https://x-house.co.jp/en/). It extracts property names, monthly rent, availability dates, and direct Google Maps location links into a clean CSV file.

---

## Features

- **CLI Search URL Input**: Pass any custom Xross House filter or search URL via `--url`.
- **2-Step Scraping Pipeline**:
  1. Scrapes listing search results (names, rent, availability dates, detail URLs).
  2. Visits each individual property page to extract direct Google Maps query links.
- **Headful & Headless Modes**: Run silently in the background or launch a visible browser window with `--headful` to watch the scraping process live.
- **CSV Export**: Outputs clean, structured data in UTF-8 format (`listings.csv`).

---

## Output Data Structure

The generated CSV contains the following fields:

| Column | Description | Example |
| :--- | :--- | :--- |
| `name` | Property / Room Name | `AP1073 Chronos Kitakarasuyama 205` |
| `rent` | Monthly Rent (JPY) | `73,000 yen` |
| `available_from` | Earliest Move-in Date | `2026-09-05` |
| `google_map_url` | Direct Google Maps Link | `https://www.google.com/maps/search/?api=1&query=...` |
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
python scraper.py --url "https://x-house.co.jp/en/fee/..." --output tokyo_rent.csv
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

---

## Future Extensions

- **Distance Calculation**: Calculate straight-line and walking commute distance to Rakuten Main Office (Rakuten Crimson House, Futako-Tamagawa).
