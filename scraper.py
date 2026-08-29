import argparse
import os
import random
import re
import time
import urllib.parse
import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DEFAULT_SEARCH_URL = (
    "https://x-house.co.jp/en/fee/?rent_min=&rent_max=&gender=no-female&date="
    "&sort=room&vacant_room_flg=1&room_type=%2C5&walk=&station=&city=%2C67"
    "&closest_station_name%5B%5D=&closest_station_distance%5B%5D=30"
    "&closest_station_transfer%5B%5D=&keyword=&campaign=&facility="
)

# Rakuten Crimson House (Futako-Tamagawa, Tokyo)
RAKUTEN_LON = 139.6301311
RAKUTEN_LAT = 35.6104929
RAKUTEN_DEST_STR = "35.6104929,139.6301311"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    "Referer": "https://x-house.co.jp/en/",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}


def calculate_walking_route(address: str, session: requests.Session):
    """
    Geocodes Japanese address using GSI and calculates walking distance/duration via OSRM Foot Routing.
    """
    if not address:
        return None, None
    try:
        # 1. Geocode Japanese address via GSI (Geospatial Information Authority of Japan)
        gsi_url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={urllib.parse.quote(address)}"
        res = session.get(gsi_url, timeout=10)
        data = res.json()
        if not data:
            return None, None
        
        lon, lat = data[0]["geometry"]["coordinates"]
        
        # 2. Query OSRM Foot Routing
        osrm_url = (
            f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/"
            f"{lon},{lat};{RAKUTEN_LON},{RAKUTEN_LAT}?overview=false"
        )
        osrm_res = session.get(osrm_url, timeout=10).json()
        if "routes" in osrm_res and osrm_res["routes"]:
            dist_meters = osrm_res["routes"][0]["distance"]
            dur_seconds = osrm_res["routes"][0]["duration"]
            
            dist_str = f"{dist_meters / 1000.0:.2f} km"
            mins = round(dur_seconds / 60.0)
            dur_str = f"{mins} mins" if mins < 60 else f"{mins // 60} hr {mins % 60} min"
            return dist_str, dur_str
    except Exception as e:
        print(f"    [!] Error calculating walking route for '{address}': {e}")
    return None, None


def scrape_search_results(search_url: str, headful: bool = False, max_retries: int = 3):
    """
    Step 1: Scrape all listing search results with infinite scroll support.
    """
    print(f"[*] Step 1: Fetching listing search results (Headful: {headful})...")
    print(f"[*] Search URL: {search_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headful, 
            slow_mo=100 if headful else 0,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"]
        )
        page = context.new_page()
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"[*] Navigating to search URL (Attempt {attempt}/{max_retries})...")
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector(".result-property-count", timeout=30000)
                break
            except Exception as e:
                if attempt == max_retries:
                    browser.close()
                    raise e
                print(f"  [!] Timeout/Error, retrying in 3 seconds... ({e})")
                time.sleep(3)
        
        # Read total count reported by header
        count_raw = page.inner_text(".result-property-count").strip()
        digits = re.findall(r"\d+", count_raw)
        expected_total = int(digits[0]) if digits else 0
        print(f"[*] Total properties available according to portal: {expected_total}")
        
        # Scroll down progressively to load all batched cards
        print("[*] Scrolling to load all paginated results...")
        max_scroll_attempts = 30
        prev_count = -1
        unchanged_count = 0
        
        for scroll_idx in range(1, max_scroll_attempts + 1):
            current_cards = len(page.query_selector_all("article.c-property-card"))
            
            if expected_total > 0 and current_cards >= expected_total:
                print(f"  [✓] All {current_cards}/{expected_total} listings loaded into DOM.")
                break
                
            if current_cards == prev_count:
                unchanged_count += 1
                if unchanged_count >= 3 and current_cards > 0:
                    print(f"  [*] Reached end of scrollable results ({current_cards} items).")
                    break
            else:
                unchanged_count = 0
                
            prev_count = current_cards
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)
        
        print("[*] Extracting property cards...")
        results = page.evaluate("""() => {
            const cards = document.querySelectorAll('article.c-property-card');
            return Array.from(cards).map(c => {
                const ttl = c.querySelector('.head .ttl') ? c.querySelector('.head .ttl').innerText.trim() : '';
                const link = c.querySelector('a') ? c.querySelector('a').href : '';
                
                const availElem = c.querySelector('.detail-item .room-condition .ib') || c.querySelector('.detail-item .room-condition');
                let avail = availElem ? availElem.innerText.replace('Available from', '').replace('～', '').replace('~', '').trim() : '';
                
                const numElem = c.querySelector('.detail-item .num');
                let rent = '';
                if (numElem) {
                    rent = numElem.innerText.replace('～', '').replace('~', '').trim();
                }
                
                return {
                    name: ttl,
                    rent: rent,
                    available_from: avail,
                    detail_url: link
                };
            });
        }""")
        browser.close()
        
    print(f"[✓] Step 1 Complete: Successfully extracted {len(results)} listings.\n")
    return results


def fetch_detail_page_with_retry(session: requests.Session, url: str, max_retries: int = 3, base_delay: float = 1.5):
    """
    Fetches a property detail page with exponential backoff on 429/403/timeout.
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code in [429, 403]:
                wait_time = base_delay * (2 ** attempt) + random.uniform(1.0, 3.0)
                print(f"    [!] Rate limit/HTTP {resp.status_code} on {url}. Backing off for {wait_time:.1f}s (Attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"    [!] HTTP {resp.status_code} on {url} (Attempt {attempt}/{max_retries})")
                time.sleep(base_delay)
        except Exception as e:
            wait_time = base_delay * attempt
            print(f"    [!] Connection error: {e}. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    return None


def enrich_with_details_and_distance(listings: list, headful: bool = False, delay: float = 1.5):
    """
    Step 2: Visit each property detail page with configurable polite delay to avoid rate limiting.
    """
    print(f"[*] Step 2: Extracting Maps URLs & calculating walking distances (Delay between requests: {delay}s)...")
    
    enriched = []
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    
    if headful:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=150)
            page = browser.new_page()
            
            for i, item in enumerate(listings, 1):
                url = item["detail_url"]
                print(f"  [{i:02d}/{len(listings)}] Visiting: {item['name']}")
                
                # Polite randomized delay between page navigations
                sleep_duration = max(0.5, delay + random.uniform(-0.3, 0.5))
                time.sleep(sleep_duration)
                
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                iframe = soup.find("iframe", src=lambda s: s and "maps.google" in s)
                jp_address = ""
                gmap_url = ""
                if iframe:
                    src = iframe.get("src", "")
                    parsed = urllib.parse.urlparse(src)
                    qs = urllib.parse.parse_qs(parsed.query)
                    jp_address = qs.get("q", [""])[0]
                    if jp_address:
                        gmap_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(jp_address)}"
                
                dist_str, dur_str = calculate_walking_route(jp_address, session)
                walk_dir_url = (
                    f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(jp_address)}"
                    f"&destination={RAKUTEN_DEST_STR}&travelmode=walking"
                ) if jp_address else ""
                
                print(f"         → Walking: {dist_str or 'N/A'} ({dur_str or 'N/A'})")
                
                enriched.append({
                    "name": item["name"],
                    "rent": item["rent"],
                    "available_from": item["available_from"],
                    "walking_distance": dist_str or "N/A",
                    "walking_time": dur_str or "N/A",
                    "google_map_url": gmap_url,
                    "google_map_walking_url": walk_dir_url,
                    "detail_url": url
                })
            browser.close()
    else:
        for i, item in enumerate(listings, 1):
            url = item["detail_url"]
            print(f"  [{i:02d}/{len(listings)}] Processing: {item['name']}")
            
            # Polite randomized delay between page requests
            sleep_duration = max(0.5, delay + random.uniform(-0.2, 0.4))
            time.sleep(sleep_duration)
            
            html_text = fetch_detail_page_with_retry(session, url, max_retries=3, base_delay=delay)
            if html_text:
                soup = BeautifulSoup(html_text, "html.parser")
                
                iframe = soup.find("iframe", src=lambda s: s and "maps.google" in s)
                jp_address = ""
                gmap_url = ""
                if iframe:
                    src = iframe.get("src", "")
                    parsed = urllib.parse.urlparse(src)
                    qs = urllib.parse.parse_qs(parsed.query)
                    jp_address = qs.get("q", [""])[0]
                    if jp_address:
                        gmap_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(jp_address)}"
                
                dist_str, dur_str = calculate_walking_route(jp_address, session)
                walk_dir_url = (
                    f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(jp_address)}"
                    f"&destination={RAKUTEN_DEST_STR}&travelmode=walking"
                ) if jp_address else ""
                
                print(f"         → Walking: {dist_str or 'N/A'} ({dur_str or 'N/A'})")
                
                enriched.append({
                    "name": item["name"],
                    "rent": item["rent"],
                    "available_from": item["available_from"],
                    "walking_distance": dist_str or "N/A",
                    "walking_time": dur_str or "N/A",
                    "google_map_url": gmap_url,
                    "google_map_walking_url": walk_dir_url,
                    "detail_url": url
                })
            else:
                print(f"  [!] Failed to load detail page for: {item['name']}")
                enriched.append({
                    "name": item["name"],
                    "rent": item["rent"],
                    "available_from": item["available_from"],
                    "walking_distance": "N/A",
                    "walking_time": "N/A",
                    "google_map_url": "",
                    "google_map_walking_url": "",
                    "detail_url": url
                })
                
    print(f"\n[✓] Step 2 Complete: Enriched all {len(enriched)} listings.\n")
    return enriched


def resolve_output_path(output_dir: str, filename: str, explicit_output: str = None) -> str:
    """
    Resolves the final target CSV file path and ensures the parent directory exists.
    """
    if explicit_output:
        target_path = explicit_output
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        return target_path

    os.makedirs(output_dir, exist_ok=True)
    if not filename.lower().endswith(".csv"):
        filename = f"{filename}.csv"
    return os.path.join(output_dir, filename)


def main():
    parser = argparse.ArgumentParser(
        description="Housing Scraper for Xross House with Walking Distance calculation to Rakuten Crimson House.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--url", "-u",
        default=DEFAULT_SEARCH_URL,
        help="Target Xross House search URL to scrape."
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Launch visible browser window to watch scraping in real-time."
    )
    parser.add_argument(
        "--delay", "-w",
        type=float,
        default=1.5,
        help="Polite delay in seconds between detail page requests to avoid rate limits."
    )
    parser.add_argument(
        "--dir", "-d",
        default="data",
        help="Directory to save the output CSV."
    )
    parser.add_argument(
        "--name", "-n",
        default="listings.csv",
        help="Filename for the output CSV (e.g. 'setagaya' or 'listings.csv')."
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Optional full output path (overrides --dir and --name)."
    )
    args = parser.parse_args()
    
    target_filepath = resolve_output_path(args.dir, args.name, args.output)
    
    # 1. Scrape listing overview from CLI search URL with infinite scroll
    basic_listings = scrape_search_results(search_url=args.url, headful=args.headful)
    
    # 2. Enrich with detail pages, Google Maps URLs, and walking distances
    full_listings = enrich_with_details_and_distance(
        basic_listings, 
        headful=args.headful, 
        delay=args.delay
    )
    
    # 3. Export to CSV
    df = pd.DataFrame(full_listings)
    df.to_csv(target_filepath, index=False, encoding="utf-8-sig")
    print(f"[✓] Successfully wrote {len(df)} records to '{target_filepath}'.\n")
    
    print("--- Summary Sample (First 5 records) ---")
    print(df[["name", "rent", "available_from", "walking_distance", "walking_time"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
