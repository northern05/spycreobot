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
            api_url: str = "https://graph.facebook.com/v22.0/ads_archive",
    ):
        self.access_token = access_token
        self.api_url = api_url
        self.client = httpx.AsyncClient(timeout=30)
        self.app_id = app_id
        self.app_secret = app_secret
        self.semaphore = asyncio.Semaphore(5)

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
        url = "https://graph.facebook.com/v22.0/oauth/access_token"
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
            "half_year": timedelta(days=180),
            "year": timedelta(days=365)
        }.get(period, timedelta(days=7))
        return (today - delta).strftime("%Y-%m-%d")

    async def _fetch_ads(self, params: dict) -> Dict[str, Any]:
        retries = 3
        retry_delay = 1
        for attempt in range(1, retries + 1):
            async with self.semaphore:
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
                except httpx.PoolTimeout as e:
                    logging.error(f"Connection pool timeout on attempt {attempt}: {e}")
                    if attempt < retries:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.1
                    else:
                        raise Exception(
                            f"PoolTimeout: Failed to get connection from pool after {retries} attempts") from e
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
            "ad_reached_countries": country if country else ",".join(SUPPORTED_COUNTRIES),
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

            media_url, media_type, app_url, cta_text = await self.extract(fb_ad_url=snapshot_url)
            logging.info(
                "=" * 100 + f"\nSNAPSHOT: {snapshot_url}\n MEDIA: {media_url}\n APP: {app_url}\n BUTTON: {cta_text}\n\n" + "=" * 100)
            if not app_url or not cta_text or not self.is_pwa_url(app_url): return None

            return {
                "id": ad_id,
                "title": title,
                "description": description,
                "body": self.remove_emojis_regex(body),
                "platforms": ad_platforms,
                "url": ad.get("ad_snapshot_url"),
                "days_running": days_running,
                "created_at": datetime.strptime(ad.get("ad_delivery_start_time"), "%Y-%m-%d"),
                "raw_ad_data": ad,
                "type": ad.get("ad_creative_media_type") if ad.get("ad_creative_media_type") else media_type,
                "page_id": ad.get("page_id"),
                "media_url": media_url,
                "app_url": app_url,
                "button": cta_text,
            }
        except Exception as e:
            logging.exception(f"Unexpected error in _format_ad for ad ID {ad.get('id')}: {e}")
            return None

    async def close(self):
        await self.client.aclose()

    async def get_ads_page(self, page_size: int = 25, exhaustive: bool = False, **search_params: Any) -> Tuple[
        List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        all_collected_ads: List[Dict[str, Any]] = []

        search_cursor = search_params.pop('search_cursor', None)
        if search_cursor:
            current_keyword_combination_index = search_cursor.get('current_keyword_combination_index', 0)
            current_cursor = search_cursor.get('current_cursor', None)
            seen_ad_ids = set(search_cursor.get('seen_ad_ids', []))
            seen_content_hashes = set(search_cursor.get('seen_content_hashes', []))
            seen_urls = set(search_cursor.get('seen_urls', []))
        else:
            current_keyword_combination_index = 0
            current_cursor = None
            seen_ad_ids = set()
            seen_content_hashes = set()
            seen_urls = set()

        api_fetch_limit = max(page_size, 30)

        while len(all_collected_ads) < page_size or exhaustive:
            ads_chunk, next_cursor_for_term, next_combination_index = await self._orchestrate_search_terms(
                api_call_limit=api_fetch_limit,
                start_combination_index=current_keyword_combination_index,
                start_cursor=current_cursor,
                **search_params
            )

            if not ads_chunk and next_combination_index == -1:
                break

            for ad in ads_chunk:
                content_hash = hashlib.md5(ad.get("body", "").encode('utf-8')).hexdigest()
                if ad["id"] not in seen_ad_ids and content_hash not in seen_content_hashes and ad[
                    "app_url"] not in seen_urls:
                    all_collected_ads.append(ad)
                    seen_ad_ids.add(ad["id"])
                    seen_content_hashes.add(content_hash)
                    seen_urls.add(ad["app_url"])
                    if len(all_collected_ads) >= page_size and not exhaustive:
                        break

            current_cursor = next_cursor_for_term
            current_keyword_combination_index = next_combination_index
            if not current_cursor and current_keyword_combination_index == -1:
                break

        next_search_cursor = None
        if not exhaustive and len(all_collected_ads) >= page_size:
            next_search_cursor = {
                'current_keyword_combination_index': current_keyword_combination_index,
                'current_cursor': current_cursor,
                'seen_ad_ids': list(seen_ad_ids),
                'seen_content_hashes': list(seen_content_hashes),
                'seen_urls': list(seen_urls)
            }

        return all_collected_ads, next_search_cursor

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
        period = "half_year" if period == "halfyear" else period
        generated_terms = []

        for combo in COUNTRY_TO_KEYWORDS.get(country):
            term_string = ' '.join(combo)
            if keyword:
                term_string += f" {keyword}"
            generated_terms.append(term_string)

        current_combination_index = start_combination_index
        current_cursor = start_cursor

        while current_combination_index < len(generated_terms):
            search_term = generated_terms[current_combination_index]
            logging.info(f"[🔍] Searching with term: '{search_term}' (Index {current_combination_index})")

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
                return ads_for_term, next_cursor_for_term, current_combination_index
            else:
                current_combination_index += 1
                current_cursor = None

        return [], None, -1

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

    async def extract(self, fb_ad_url: str) -> tuple[Any, Any, str | None, Any | None]:
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

        def choose_best_media(sources: list[str]) -> tuple | None:
            def is_valid_video(url):
                return ".mp4" in url and "video" in url and "fbcdn.net" in url

            def is_valid_image(url):
                return re.search(r'\.(jpg|jpeg|png)', url) and "fbcdn.net" in url and "s60x60" not in url

            def extract_size_score(url):
                match = re.search(r's(\d+)x(\d+)', url)
                return int(match.group(1)) * int(match.group(2)) if match else 0

            videos = list(filter(is_valid_video, sources))
            if videos:
                return max(videos, key=len), "video"

            images = list(filter(is_valid_image, sources))
            if images:
                return max(images, key=extract_size_score), "image"

            return None

        if not is_snapshot_url_valid(fb_ad_url):
            print(f"[❌] Snapshot URL is not accessible: {fb_ad_url}")
            return None, None, None, None

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
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"[❌] Exception during page.goto: {e}")
            return None, None, None, None

        try:
            await page.evaluate("window.scrollBy(0, 3000)") 
            await page.wait_for_timeout(1000)
            links = await page.query_selector_all('a[href]:not([role="button"])')
            visible_links = [link for link in links if await link.is_visible()]
            for link in visible_links:
                href = await link.get_attribute("href")
                if not href:
                    continue

                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                decoded = unquote(qs.get("u", [""])[0])
                if not decoded:
                    continue

                all_divs = await link.query_selector_all("div")
                possible_texts = set()
                for div in all_divs:
                    text = (await div.inner_text()).strip()
                    if text and 2 <= len(text) <= 30:
                        possible_texts.add(text)
                        if any(k in text.lower() for k in COMMERCIAL_KEYWORDS):
                            cta_text = text
                            break
                if not cta_text and possible_texts:
                    cta_text = next(iter(possible_texts))

                if decoded and cta_text:
                    break

        except Exception as e:
            print(f"[⚠️] Failed to eval links: {e}")

        await page.close()

        best_media, media_type = choose_best_media(media_urls)
        return best_media, media_type, decoded, cta_text

    def is_pwa_url(self, url: str) -> bool:
        url = url.lower()
        parsed = urlparse(url)
        domain = parsed.netloc

        tracking_keywords = [
            "sub_id", "sub1", "sub2", "lead_id", "campaign.name", "ad.id", "offer_id", "aff_id",
            "click_id", "campaign", "adset.name", "placement", "pixel", "fbclid", "open_pwa",
            "key=", "media_source", "pwa"
        ]
        suspicious_tlds = [
            ".shop", ".online", ".click", ".quest", ".vip", ".xyz", ".life", ".site", ".fun", ".casino",
            ".bet", ".game", ".win"
        ]
        pwa_indicators = ["pwa", "webapp", "type=pwa", "open_pwa"]

        if "play.google.com" in domain and "/store/apps/details" in parsed.path:
            query = parse_qs(parsed.query)
            if "id" in query and query["id"][0]:
                return False

        if "apps.apple.com" in domain and "/app/" in parsed.path:
            return False

        score = 0

        if any(domain.endswith(tld) for tld in suspicious_tlds):
            score += 2

        if any(kw in url for kw in tracking_keywords):
            score += 2

        if any(indicator in url for indicator in pwa_indicators):
            score += 3

        if "/pwa" in parsed.path or "lite" in url:
            score += 1

        return score >= 1


if __name__ == '__main__':
    async def run_main():
        driver = FacebookAdsLibraryDriver(
            access_token="EAAKCNpvlGQ8BO9tSmQFnCdultZB4ICpeqZCRVGZCmlJoe5ZA5QZCYNcaqJrwOJ0lEhbBEsrE7HB5jbho2EfVWQzKOOu0NttJLjgV980YtifnLLGC7KKlMwIOM1bmZAixyZARzgDpNZBKGZC6DbfXdyu1oFHGTzJM8HXiuZCZA0kZBZCC958yofyYNeWvOt4l03qIgF39tdurMLRzb8T9Ra2oGVoJG4PwIK1JDoM5ykHsAyVfe9xZAZCb4xZAj9vm",
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
                ad_type="video",
                country="DE",
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
                print(f"  APP URL: {ad.get('app_url')}")
                print("-" * 20)
            print(f"Next search cursor for Page 1: {'exists' if search_cursor_page1 else 'None'}")

            # --- Second Page (if cursor exists) ---
            # if search_cursor_page1:
            #     print("\n--- Page 2 (Gambling, continued) ---")
            #     ads_page2, search_cursor_page2 = await driver.get_ads_page(
            #         page_size=page_size,
            #         search_cursor=search_cursor_page1,  # Pass the cursor from the previous page
            #         niche="gambling",  # Re-pass original search parameters
            #         placements=["facebook", "instagram"],
            #         ad_type="all",
            #         period="month"
            #     )
            #     print(f"Collected {len(ads_page2)} ads for Page 2.")
            #     for i, ad in enumerate(ads_page2):
            #         print(f"--- Ad {i + 1} ---")
            #         print(f"  ID: {ad['id']}")
            #         print(f"  Title: {ad.get('title')}")
            #         print(f"  Body (first 100 chars): {ad.get('body')[:100]}...")
            #         print(f"  URL: {ad.get('url')}")
            #         print(f"  Days Running: {ad.get('days_running')}")
            #         print("-" * 20)
            #     print(f"Next search cursor for Page 2: {'exists' if search_cursor_page2 else 'None'}")

            # You can continue calling get_ads_page in a loop until search_cursor is None

        except Exception as e:
            logging.error(f"Error during main execution: {e}")
        finally:
            await driver.close()


    asyncio.run(run_main())
