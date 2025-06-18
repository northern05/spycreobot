import logging
import re
from playwright.async_api import async_playwright
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
import hashlib
from urllib.parse import urlparse, parse_qs, unquote

from utils.const import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MAX_PLAYWRIGHT_NAV_ATTEMPTS = 2


class FacebookAdsLibraryDriver:
    def __init__(
            self,
            app_id: str,
            app_secret: str,
            access_token: str,
            api_url: str = "https://graph.facebook.com/v19.0/ads_archive",
    ):
        self.access_token = access_token
        self.api_url = api_url
        self.client = httpx.AsyncClient(timeout=30)
        self.app_id = app_id
        self.app_secret = app_secret

        self.browser = None
        self.context = None

    async def init_playwright(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1280, "height": 720}
        )
        await self.context.set_extra_http_headers({
            "Referer": "https://www.facebook.com/",
            "Accept-Language": "en-US,en;q=0.9"
        })

    async def exchange_token(self) -> str:
        url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": self.access_token
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                new_token = response.json().get("access_token")
                if not new_token:
                    raise Exception("Token exchange failed: empty access_token in response.")
                self.access_token = new_token
                return new_token
        except httpx.HTTPStatusError as e:
            logging.error(f"Token exchange failed: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Token exchange failed: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            logging.error(f"Token exchange connection error: {e}")
            raise Exception(f"Token exchange connection error: {e}") from e
        except Exception as e:
            logging.exception("Unexpected error during token exchange")
            raise Exception(f"Token exchange failed: {e}") from e

    def _calculate_date_filter(self, period: str) -> str:
        today = datetime.utcnow().date()
        delta = {
            "week": timedelta(days=7),
            "month": timedelta(days=30),
            "quarter": timedelta(days=90),
            "half_year": timedelta(days=180)  # Changed 'halfyear' to 'half_year' for consistency
        }.get(period, timedelta(days=7))
        return (today - delta).strftime("%Y-%m-%d")

    def is_commercial_tracking_link(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            full_url = url.lower()

            forbidden_domains = [
                "facebook.com", "l.facebook.com", "play.google.com", "apps.apple.com",
                "app.adjust.com", "doubleclick.net"
            ]
            if any(d in domain for d in forbidden_domains):
                return False

            suspicious_tlds = [".shop", ".online", ".click", ".quest", ".vip", ".xyz", ".life"]
            if not any(domain.endswith(tld) for tld in suspicious_tlds):
                return False

            tracking_keywords = [
                "sub_id", "sub1", "sub2", "lead_id", "campaign.name", "ad.id",
                "adset.name", "placement", "pixel", "fbclid", "open_pwa", "key="
            ]
            if not any(kw in full_url for kw in tracking_keywords):
                return False

            return True
        except Exception as e:
            print(f"[⚠️] Error checking URL: {e}")
            return False

    async def _fetch_ads(self, params: dict) -> Dict[str, Any]:
        retries = 3
        retry_delay = 1
        for attempt in range(1, retries + 1):
            try:
                response = await self.client.get(self.api_url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 400) and attempt < retries:
                    try:
                        logging.info(f"HTTP Error {e.response.status_code}. Attempting token refresh and retry...")
                        self.access_token = await self.exchange_token()
                        params["access_token"] = self.access_token
                    except Exception as refresh_error:
                        logging.error(f"Token refresh failed: {refresh_error}")
                        raise Exception("Failed to refresh access token") from refresh_error
                else:
                    logging.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                    raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}") from e
            except httpx.RequestError as e:
                logging.warning(f"Request error: {e}. Attempt {attempt}/{retries}. Retrying in {retry_delay}s...")
                if attempt < retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.1
                else:
                    logging.error(f"Failed to fetch Facebook Ads after {retries} attempts: {e}")
                    raise Exception(f"Failed to fetch Facebook Ads after {retries} attempts: {e}") from e
            except Exception as e:
                logging.exception(f"Unexpected error during _fetch_ads: {e}")
                raise Exception(f"Failed to fetch Facebook Ads: {e}") from e
        raise Exception(f"Failed to fetch Facebook Ads after {retries} attempts.")

    async def _search_single_term_ads(
            self,
            search_term: str,
            placements: Optional[List[str]],
            ad_type: str,
            period: str = "month",
            limit: int = 100,
            country: str = None,
            page_id: str = None,
            after: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:

        params = {
            "access_token": self.access_token,
            "search_terms": search_term,
            "ad_reached_countries": country if country else ",".join(COUNTRY_TO_LANG_CODE.keys()),
            "ad_active_status": "ACTIVE",
            "media_type": ad_type.upper() if ad_type else "ALL",
            "fields": ",".join([
                "ad_creative_bodies",
                "ad_creative_link_titles",
                "ad_creative_link_descriptions",
                "ad_snapshot_url",
                "publisher_platforms",
                "ad_delivery_start_time",
                "ad_delivery_stop_time",
                "ad_creative_link_urls",
                "page_id",
                "ad_creative_media_type"
            ]),
            "limit": limit,
            "start_date": self._calculate_date_filter(period),
        }
        if page_id:
            params["search_page_ids"] = page_id
        if after:
            params["after"] = after

        params = {k: v for k, v in params.items() if v}

        try:
            raw_response_data = await self._fetch_ads(params)
            raw_ads = raw_response_data.get("data", [])
            next_cursor = raw_response_data.get("paging", {}).get("cursors", {}).get("after")

            formatted_ads = []
            for ad in raw_ads:
                formatted = await self._format_ad(ad=ad, placements=placements)
                if formatted:
                    formatted_ads.append(formatted)
            return formatted_ads, next_cursor
        except Exception as e:
            logging.error(f"Error fetching ads for term '{search_term}': {e}")
            return [], None

    async def _orchestrate_search_terms(
            self,
            niche: str,
            placements: Optional[List[str]],
            ad_type: Optional[str],
            period: str,
            api_call_limit: int,
            start_combination_index: int,
            start_cursor: Optional[str],
            country: Optional[str] = None,
            page_id: Optional[str] = None,
            keyword: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
        """
        Orchestrates calls to _search_single_term_ads using generated keyword combinations.
        Returns a chunk of ads, the next cursor for the current search_term, and the
        index of the search_term combination that was being processed.
        """

        period = "half_year" if period == "halfyear" else period

        # Generate ALL potential search terms (including combinations) based on new structure
        generated_terms = []

        # Add all combinations from NICHE_KEYWORDS_COMBINATIONS for each relevant niche
        for i, combo in enumerate(NICHE_KEYWORDS_COMBINATIONS.get(niche)):
            term_string = ''.join([f"%E2%A0%80{word}%20" for word in combo])
            if keyword: term_string += f" %E2%A0%80{keyword}%20"
            generated_terms.append(term_string)

        current_combination_index = start_combination_index
        current_cursor = start_cursor

        while current_combination_index < len(generated_terms):
            search_term = generated_terms[current_combination_index]
            logging.info(f"Searching with term: '{search_term}' (Combination Index: {current_combination_index})")

            ads_for_term, next_cursor_for_term = await self._search_single_term_ads(
                search_term=search_term,
                placements=placements,
                country=country,
                ad_type=ad_type,
                period=period,
                limit=api_call_limit,
                after=current_cursor,
                page_id=page_id
            )

            if ads_for_term:
                # Return ads, the cursor for *this specific term*, and *this term's index*
                return ads_for_term, next_cursor_for_term, current_combination_index
            else:
                # No ads for this term/cursor, move to next combination
                logging.info(f"No ads for term '{search_term}'. Moving to next combination.")
                current_combination_index += 1
                current_cursor = None  # Reset cursor when moving to a new search term

        logging.info("All generated search terms exhausted.")
        return [], None, -1  # Signal exhaustion

    async def _format_ad(
            self,
            ad: dict,
            placements: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        title = ad.get("ad_creative_link_titles", [""])[0] if ad.get("ad_creative_link_titles") else ""
        description = ad.get("ad_creative_link_descriptions", [""])[0] if ad.get(
            "ad_creative_link_descriptions") else ""
        body = ad.get("ad_creative_bodies", [""])[0] if ad.get("ad_creative_bodies") else ""

        EXCLUDED_TITLE = "This content was removed because it didn't follow our Advertising Standards."
        ad_id = ad.get("id")

        if not ad.get("id"):
            logging.warning("Ad ID is missing, skipping ad.")
            return None
        snapshot_url = ad.get("ad_snapshot_url")
        if not snapshot_url:
            logging.warning(f"Ad snapshot URL is missing for ad ID {ad_id}, skipping ad.")
            return None
        try:
            if EXCLUDED_TITLE in title:
                logging.info(f"Excluding ad ID {ad.get('id')} due to removed content title.")
                return None

            ad_platforms = ad.get("publisher_platforms", []) or []
            if placements and not any(p in ad_platforms for p in placements):
                return None

            start_time = ad.get("ad_delivery_start_time")
            stop_time = ad.get("ad_delivery_stop_time")

            start_dt = None
            end_dt = datetime.utcnow().date()

            if start_time:
                try:
                    start_dt = datetime.strptime(start_time, "%Y-%m-%d").date()
                    if stop_time:
                        end_dt = datetime.strptime(stop_time, "%Y-%m-%d").date()
                except ValueError:
                    logging.warning(
                        f"Invalid date format for ad ID {ad.get('id')}: start_time={start_time}, stop_time={stop_time}")
                    start_dt = None

            days_running = (end_dt - start_dt).days if start_dt and end_dt else 0
            if days_running < 0: days_running = 0

            if len(body) >= CONTENT_CHAR_LIMIT:
                logging.info(
                    f"Excluding ad ID {ad.get('id')} due to body length ({len(body)} >= {CONTENT_CHAR_LIMIT}).")
                return None

            media_url, app_url, cta_text = await self.extract(fb_ad_url=snapshot_url)
            logging.info("="*100+f"\nSNAPSHOT: {snapshot_url}\n MEDIA: {media_url}\n APP: {app_url}\n BUTTON: {cta_text}\n\n" + "="*100)
            button = cta_text.encode('latin1').decode('utf-8')
            if not app_url or not button or any(d in app_url for d in ("play.google", "apps.apple")): return None

            return {
                "id": ad_id,
                "title": title,
                "description": description,
                "body": self.remove_emojis_regex(body),
                "platforms": ad_platforms,
                "url": ad.get("ad_snapshot_url"),
                "days_running": days_running,
                "raw_ad_data": ad,
                "type": ad.get("ad_creative_media_type"),
                "page_id": ad.get("page_id"),
                "media_url": media_url,
                "app_url": app_url,
                "button": button,
            }
        except Exception as e:
            logging.exception(f"Unexpected error in _format_ad for ad ID {ad.get('id')}: {e}")
            return None

    async def close(self):
        await self.client.aclose()

    async def get_ads_page(self, page_size: int = 10, **search_params: Any) -> Tuple[
        List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Fetches a single 'page' of unique ads (up to page_size) and returns a cursor
        for the next page. This function manages the internal state of combinations and pagination.

        Args:
            page_size: The desired number of unique ads to return for this "page". Default to 4.
            **search_params: Parameters for the ad search (e.g., niche, placements,
                             country, ad_type, period, keyword).
                             It can also include 'search_cursor' from a previous call
                             to continue the search.

        Returns:
            A tuple:
            - A list of dictionaries, where each dictionary represents a unique ad.
            - A dictionary containing the 'search_cursor' for the next page,
              or None if all ads are exhausted.
              The 'search_cursor' will contain:
                - 'current_keyword_combination_index': The index of the combination being processed.
                - 'current_cursor': The Facebook API 'after' cursor for that combination.
                - 'seen_ad_ids': Set of ad IDs seen so far (for de-duplication).
                - 'seen_content_hashes': Set of content hashes seen so far (for de-duplication).
        """
        all_collected_ads: List[Dict[str, Any]] = []

        search_cursor = search_params.pop('search_cursor', None)
        if search_cursor:
            current_keyword_combination_index = search_cursor.get('current_keyword_combination_index', 0)
            current_cursor = search_cursor.get('current_cursor', None)
            seen_ad_ids = set(search_cursor.get('seen_ad_ids', []))
            seen_content_hashes = set(search_cursor.get('seen_content_hashes', []))
            logging.info(
                f"Resuming search from combination {current_keyword_combination_index}, cursor {current_cursor}, seen {len(seen_ad_ids)} ads.")
        else:
            current_keyword_combination_index = 0
            current_cursor = None
            seen_ad_ids = set()
            seen_content_hashes = set()
            logging.info("Starting new unique ad search from scratch.")

        api_fetch_limit = max(page_size, 100)

        # Initialize ads_chunk and next_combination_index before the loop/try block
        ads_chunk = []
        next_combination_index = current_keyword_combination_index  # Default to current, will be updated

        while len(all_collected_ads) < page_size:
            try:
                # Call _orchestrate_search_terms, which gets a chunk of ads from current state
                ads_chunk, next_cursor_for_term, next_combination_index = await self._orchestrate_search_terms(
                    api_call_limit=api_fetch_limit,
                    start_combination_index=current_keyword_combination_index,
                    start_cursor=current_cursor,
                    **search_params  # Pass all other search parameters
                )

                if not ads_chunk and next_combination_index == -1:
                    logging.info("All search terms and pages exhausted. Cannot get more ads.")
                    break  # Exit the while loop if all possibilities exhausted

                for ad in ads_chunk:
                    # Create a content hash for soft de-duplication
                    content_string = f"{ad.get('title', '')}|{ad.get('description', '')}|{ad.get('body', '')}"
                    content_hash = hashlib.md5(content_string.encode('utf-8')).hexdigest()

                    # Check for uniqueness based on both Facebook ID and content hash
                    if ad["id"] not in seen_ad_ids and content_hash not in seen_content_hashes:
                        all_collected_ads.append(ad)
                        seen_ad_ids.add(ad["id"])
                        seen_content_hashes.add(content_hash)
                        if len(all_collected_ads) >= page_size:
                            break  # Stop collecting if we reached the target page_size for this call

                # Update current state for the next internal iteration
                current_cursor = next_cursor_for_term
                current_keyword_combination_index = next_combination_index  # This will be -1 if exhausted

                # If the current internal search term is exhausted (cursor is None) AND
                # the next_combination_index signals no more terms, then we've truly exhausted all possibilities
                if not next_cursor_for_term and next_combination_index == -1:
                    logging.info("Exhausted all combinations and pages internally.")
                    break  # No more ads to fetch

            except Exception as e:
                logging.error(f"Error during overall ad fetching in get_ads_page: {e}. Stopping collection.")
                break

        # Prepare the cursor for the next call
        next_search_cursor = None
        # Only provide a next_search_cursor if we might have more ads available
        if len(all_collected_ads) >= page_size:
            # We collected enough for this page, so the next state is where we left off
            next_search_cursor = {
                'current_keyword_combination_index': current_keyword_combination_index,
                'current_cursor': current_cursor,
                'seen_ad_ids': list(seen_ad_ids),
                # Convert sets to lists for JSON serialization (if stored in DB/Redis)
                'seen_content_hashes': list(seen_content_hashes)
            }
        elif not ads_chunk and next_combination_index == -1 and len(all_collected_ads) < page_size:
            # We explicitly broke because all ads were exhausted, no next page
            logging.info("All available unique ads collected. No further pages.")
            next_search_cursor = None  # No next page

        return all_collected_ads, next_search_cursor

    def remove_emojis_regex(self, text):
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)

        return emoji_pattern.sub(r'', text)

    async def extract(self, fb_ad_url: str) -> tuple[str | None, str | None, str | None]:
        media_urls = []
        cta_text = None
        decoded = None

        def extract_final_url(fb_link: str) -> str:
            try:
                parsed = urlparse(fb_link)
                query = parse_qs(parsed.query)
                return unquote(query["u"][0]) if "u" in query else fb_link
            except Exception:
                return fb_link

        def is_snapshot_url_valid(url: str) -> bool:
            try:
                r = httpx.head(url, timeout=10, follow_redirects=True)
                return r.status_code == 200
            except Exception:
                return False

        def choose_best_media(sources: list[str]) -> str | None:
            def is_valid_video(url):
                return ".mp4" in url and "video" in url and "fbcdn.net" in url

            def is_valid_image(url):
                return re.search(r'\.(jpg|jpeg|png)', url) and "fbcdn.net" in url and "s60x60" not in url

            def extract_size_score(url):
                match = re.search(r's(\d+)x(\d+)', url)
                return int(match.group(1)) * int(match.group(2)) if match else 0

            videos = list(filter(is_valid_video, sources))
            if videos:
                return max(videos, key=len)

            images = list(filter(is_valid_image, sources))
            if images:
                return max(images, key=extract_size_score)

            return None

        if not is_snapshot_url_valid(fb_ad_url):
            print(f"[❌] Snapshot URL is not accessible: {fb_ad_url}")
            return None, None, None

        page = await self.context.new_page()

        async def handle_response(response):
            url = response.url
            if "l.facebook.com/l.php" in url:
                url = extract_final_url(url)

            if "fbcdn.net" in url and re.search(r'\.(mp4|jpg|jpeg|png)', url):
                media_urls.append(url)

        page.on("response", handle_response)

        try:
            await page.goto(fb_ad_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[❌] Exception during page.goto: {e}")
            return None, None, None

        try:
            links = await page.query_selector_all('a[href*="l.facebook.com/l.php?u="]')
            for link in links:
                href = await link.get_attribute("href")
                if not href:
                    continue

                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                decoded = unquote(qs.get("u", [""])[0])

                all_divs = await link.query_selector_all("div")
                for div in all_divs:
                    text = (await div.inner_text()).strip()
                    if text and 2 <= len(text) <= 30 and any(k in text.lower() for k in COMMERCIAL_KEYWORDS):
                        cta_text = text
        except Exception as e:
                print(f"[⚠️] Failed to eval links: {e}")

        await page.close()

        best_media = choose_best_media(media_urls)
        return best_media, decoded, cta_text


if __name__ == '__main__':
    async def run_main():
        driver = FacebookAdsLibraryDriver(
            access_token="EAAKCNpvlGQ8BO37MyiZCN2Bz7Ld7AEY6vLQdP2fVxkewfnZB9lZBTa9a8BjR6wrEi8yZBkQZC2vsHt2NqchlnRWIwq1ZBsOaUODVcoirqJovY0fVLYNpVZB7ZAunUr1DIfzVrFaazxTrflmW7CpcxJPsqsxEb8QhqoWuTnltFE2NZBRt6mEfLnI2AXN8Arm1OOZAQcveoZAF2gFZCNa8ZCGXqcrulkpK3pQfdxsKpvbi0YtCdpAZDZD",
            # Use a valid, active token
            app_id="706121008748815",
            app_secret="aff7dc896abd538f8e8050102bbbc793"
        )
        await driver.init_playwright()

        try:
            print("Starting paginated unique ad search...")

            # --- First Page (e.g., 4 ads per page) ---
            print("\n--- Page 1 (Gambling) ---")
            page_size = 10  # Request 4 ads per page
            ads_page1, search_cursor_page1 = await driver.get_ads_page(
                page_size=page_size,
                niche="gambling",  # Now specifically gambling
                placements=["facebook", "instagram", "audience_network", "threads", "messenger"],
                ad_type="all",
                period="month",
                # keyword="casino",  # Broad keyword for gambling
            )

            print(f"Collected {len(ads_page1)} ads for Page 1.")
            for i, ad in enumerate(ads_page1):
                print(f"--- Ad {i + 1} ---")
                print(f"  ID: {ad['id']}")
                print(f"  Title: {ad.get('title')}")
                print(f"  Body (first 100 chars): {ad.get('body')[:100]}...")
                print(f"  URL: {ad.get('url')}")
                print(f"  Days Running: {ad.get('days_running')}")
                print(f"  Type: {ad.get('')}")
                print(f"  Media_url {ad.get('media_url')}")
                print(f"  Button: {ad.get('button')}")
                print("-" * 20)
            print(f"Next search cursor for Page 1: {'exists' if search_cursor_page1 else 'None'}")

            # --- Second Page (if cursor exists) ---
            if search_cursor_page1:
                print("\n--- Page 2 (Gambling, continued) ---")
                ads_page2, search_cursor_page2 = await driver.get_ads_page(
                    page_size=page_size,
                    search_cursor=search_cursor_page1,  # Pass the cursor from the previous page
                    niche="gambling",  # Re-pass original search parameters
                    placements=["facebook", "instagram"],
                    ad_type="all",
                    period="month"
                )
                print(f"Collected {len(ads_page2)} ads for Page 2.")
                for i, ad in enumerate(ads_page2):
                    print(f"--- Ad {i + 1} ---")
                    print(f"  ID: {ad['id']}")
                    print(f"  Title: {ad.get('title')}")
                    print(f"  Body (first 100 chars): {ad.get('body')[:100]}...")
                    print(f"  URL: {ad.get('url')}")
                    print(f"  Days Running: {ad.get('days_running')}")
                    print("-" * 20)
                print(f"Next search cursor for Page 2: {'exists' if search_cursor_page2 else 'None'}")

            # You can continue calling get_ads_page in a loop until search_cursor is None

        except Exception as e:
            logging.error(f"Error during main execution: {e}")
        finally:
            await driver.close()


    asyncio.run(run_main())
