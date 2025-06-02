import logging
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Tuple, Dict, Any
import itertools
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

NICHE_KEYWORDS = {
    "gambling": ["casino", "slots", "betting", "poker", "blackjack", "sport", "spin", "freespin"],
    "crypto": ["crypto", "bitcoin", "ethereum", "nft", "web3", "blockchain", "cryptocurrency"],
    "nutra": ["supplement", "weight loss", "keto", "skincare", "diet pills", "vitamins", "health supplement"],
    "dating": ["dating app", "match", "love", "singles", "romance", "online dating", "dating site"],
    "products": ["buy now", "shop online", "discount", "shipping", "e-commerce", "online store", "best deals"],
    "gaming": ["game", "mmorpg", "strategy game", "mobile game", "pc game", "console game", "gameplay", "esports"]
}


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

    def _calculate_date_filter(self, period: str) -> str:
        today = datetime.utcnow().date()
        delta = {
            "week": timedelta(days=7),
            "month": timedelta(days=30),
            "quarter": timedelta(days=90),
            "half_year": timedelta(days=180)
        }.get(period, timedelta(days=7))
        return (today - delta).strftime("%Y-%m-%d")

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

    async def _fetch_ads(self, params: dict) -> Dict[str, Any]:
        retries = 3
        retry_delay = 2
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
                    retry_delay *= 2
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
            countries: Optional[List[str]],
            ad_type: Optional[str],
            period: str,
            limit: int,
            after: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:

        params = {
            "access_token": self.access_token,
            "search_terms": search_term,
            "ad_reached_countries": ",".join(countries) if countries else None,
            "ad_active_status": "ALL",
            "media_type": ad_type if ad_type else "ALL",
            "fields": ",".join([
                "ad_creative_bodies",
                "ad_creative_link_titles",
                "ad_creative_link_descriptions",
                "ad_snapshot_url",
                "publisher_platforms",
                "ad_delivery_start_time",
                "ad_delivery_stop_time",
                "id"
            ]),
            "limit": limit,
            "start_date": self._calculate_date_filter(period),
        }
        if after:
            params["after"] = after

        params = {k: v for k, v in params.items() if v}

        try:
            raw_response_data = await self._fetch_ads(params)
            raw_ads = raw_response_data.get("data", [])
            next_cursor = raw_response_data.get("paging", {}).get("cursors", {}).get("after")

            formatted_ads = []
            for ad in raw_ads:
                formatted = self._format_ad(ad, placements)
                if formatted:
                    formatted_ads.append(formatted)
            return formatted_ads, next_cursor
        except Exception as e:
            logging.error(f"Error fetching ads for term '{search_term}': {e}")
            return [], None

    async def search_ads_or(
            self,
            niche_keywords: List[str],
            placements: Optional[List[str]] = None,
            countries: Optional[List[str]] = None,
            ad_type: Optional[str] = None,
            period: str = "week",
            keyword: Optional[str] = None,
            limit: int = 10,
    ) -> List[Dict[str, Any]]:
        keywords = []
        if keyword:
            keywords.append(keyword.lower())
        for niche in niche_keywords:
            keywords.extend([kw.lower() for kw in NICHE_KEYWORDS.get(niche, [])])

        keywords = sorted(list(set(keywords)))

        params = {
            "access_token": self.access_token,
            "search_terms": ",".join(keywords),
            "ad_reached_countries": ",".join(countries) if countries else None,
            "ad_active_status": "ALL",
            "media_type": ad_type if ad_type else "ALL",
            "fields": ",".join([
                "ad_creative_bodies",
                "ad_creative_link_titles",
                "ad_creative_link_descriptions",
                "ad_snapshot_url",
                "publisher_platforms",
                "ad_delivery_start_time",
                "ad_delivery_stop_time",
                "id"
            ]),
            "limit": limit,
            "start_date": self._calculate_date_filter(period),
        }

        params = {k: v for k, v in params.items() if v}

        try:
            data = await self._fetch_ads(params)
            raw_ads = data.get("data", [])
            formatted_ads = []
            for ad in raw_ads:
                formatted = self._format_ad(ad, placements)
                if formatted:
                    formatted_ads.append(formatted)
            return formatted_ads
        except Exception as e:
            logging.error(f"OR search failed: {e}")
            return []

    async def _orchestrate_search_terms(
            self,
            niche_keywords: List[str],
            placements: Optional[List[str]],
            countries: Optional[List[str]],
            ad_type: Optional[str],
            period: str,
            keyword: Optional[str],
            api_call_limit: int,
            start_combination_index: int,
            start_cursor: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], Optional[str], int]:

        period = "half_year" if period == "halfyear" else period

        base_keywords = []
        if keyword:
            base_keywords.append(keyword.lower())
        for niche in niche_keywords:
            base_keywords.extend([kw.lower() for kw in NICHE_KEYWORDS.get(niche, [])])

        base_keywords = sorted(list(set(base_keywords)))

        search_term_combinations = []
        for r in range(2, 5):
            for combo in itertools.combinations(base_keywords, r):
                search_term_combinations.append(" ".join(combo))
        single_words_only = [kw for kw in base_keywords if not any(kw in c for c in search_term_combinations)]
        search_term_combinations.extend(single_words_only)

        unique_term_strings = []
        seen_terms = set()
        for term_str in search_term_combinations:
            words = tuple(sorted(term_str.split()))
            if words not in seen_terms:
                unique_term_strings.append(term_str)
                seen_terms.add(words)
        search_term_combinations = unique_term_strings

        if not search_term_combinations:
            logging.info("No valid search terms generated.")
            return [], None, -1

        current_combination_index = start_combination_index
        current_cursor = start_cursor

        while current_combination_index < len(search_term_combinations):
            search_term = search_term_combinations[current_combination_index]
            logging.info(f"Searching with term: '{search_term}' (Combination Index: {current_combination_index})")

            ads_for_term, next_cursor_for_term = await self._search_single_term_ads(
                search_term=search_term,
                placements=placements,
                countries=countries,
                ad_type=ad_type,
                period=period,
                limit=api_call_limit,
                after=current_cursor
            )

            if ads_for_term:
                return ads_for_term, next_cursor_for_term, current_combination_index
            else:
                logging.info(f"No ads for term '{search_term}'. Moving to next combination.")
                current_combination_index += 1
                current_cursor = None

        logging.info("All search terms and pages exhausted.")
        return [], None, -1

    def _format_ad(self, ad: dict, placements: Optional[List[str]]) -> Optional[Dict[str, Any]]:
        EXCLUDED_TITLE = "This content was removed because it didn't follow our Advertising Standards."

        if not ad.get("id"):
            logging.warning("Ad ID is missing, skipping ad.")
            return None
        if not ad.get("ad_snapshot_url"):
            logging.warning(f"Ad snapshot URL is missing for ad ID {ad.get('id')}, skipping ad.")
            return None

        try:
            title = ad.get("ad_creative_link_titles", [""])[0] if ad.get("ad_creative_link_titles") else ""
            if title == EXCLUDED_TITLE:
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

            description = ad.get("ad_creative_link_descriptions", [""])[0] if ad.get(
                "ad_creative_link_descriptions") else ""
            body = ad.get("ad_creative_bodies", [""])[0] if ad.get("ad_creative_bodies") else ""

            return {
                "id": ad["id"],
                "title": title,
                "description": description,
                "body": body,
                "platforms": ad_platforms,
                "url": ad.get("ad_snapshot_url"),
                "days_running": days_running,
                "raw_ad_data": ad
            }
        except Exception as e:
            logging.exception(f"Unexpected error in _format_ad for ad ID {ad.get('id')}: {e}")
            return None

    async def close(self):
        await self.client.aclose()

    async def get_ads_page(self, page_size: int = 10, **search_params: Any) -> Tuple[
        List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        all_collected_ads: List[Dict[str, Any]] = []

        search_cursor = search_params.pop('after', None)
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

        api_fetch_limit = max(page_size, 25)

        # Initialize ads_chunk and next_combination_index before the loop/try block
        ads_chunk = []
        next_combination_index = current_keyword_combination_index  # Default to current, will be updated

        while len(all_collected_ads) < page_size:
            try:
                ads_chunk, next_cursor_for_term, next_combination_index = await self._orchestrate_search_terms(
                    api_call_limit=api_fetch_limit,
                    start_combination_index=current_keyword_combination_index,
                    start_cursor=current_cursor,
                    **search_params
                )

                # This check is now safe because ads_chunk is always defined
                if not ads_chunk and next_combination_index == -1:
                    logging.info("All search terms and pages exhausted. Cannot get more ads.")
                    break

                for ad in ads_chunk:
                    content_string = f"{ad.get('title', '')}|{ad.get('description', '')}|{ad.get('body', '')}"
                    content_hash = hashlib.md5(content_string.encode('utf-8')).hexdigest()

                    if ad["id"] not in seen_ad_ids and content_hash not in seen_content_hashes:
                        all_collected_ads.append(ad)
                        seen_ad_ids.add(ad["id"])
                        seen_content_hashes.add(content_hash)
                        if len(all_collected_ads) >= page_size:
                            break

                current_cursor = next_cursor_for_term
                current_keyword_combination_index = next_combination_index

                if not next_cursor_for_term and next_combination_index == -1:
                    logging.info("Exhausted all combinations and pages internally.")
                    break

            except Exception as e:
                logging.error(f"Error during overall ad fetching in get_ads_page: {e}. Stopping collection.")
                # If an error occurs, we need to make sure we don't try to access ads_chunk
                # in the loop condition if it wasn't assigned. The break will handle it.
                break

        next_search_cursor = None
        if len(all_collected_ads) >= page_size:
            next_search_cursor = {
                'current_keyword_combination_index': current_keyword_combination_index,
                'current_cursor': current_cursor,
                'seen_ad_ids': list(seen_ad_ids),
                'seen_content_hashes': list(seen_content_hashes)
            }
        elif not ads_chunk and next_combination_index == -1 and len(all_collected_ads) < page_size:
            logging.info("All available unique ads collected. No further pages.")
            next_search_cursor = None

        return all_collected_ads, next_search_cursor


if __name__ == '__main__':
    async def run_main():
        driver = FacebookAdsLibraryDriver(
            access_token="EAAKCNpvlGQ8BO1XXTenZCSzuanZBswZAOlMxZC41gSWfeViZCrV2f3XUnwvfwdPl4jyh7B8ZCSvy79zvCfqSLBpWZCAApHZB6q6tjr2gfKTifAXFsbhnZBkkMsqmbZALqLdZAIrxwffbNAQzRyeV8CDxauyqhKZBowPEGnTebKgcjulsO5DmVR7L9HyIqcIjm0xoVFZAtDBzb4qkazQXZC3IZCWNlZBJsdxotMCQ7JeMxZCZBOCT7y4wZDZD",
            # Use a valid, active token
            app_id="706121008748815",
            app_secret="aff7dc896abd538f8e8050102bbbc793"
        )

        try:
            print("Starting paginated unique ad search...")

            # --- First Page (e.g., 5 ads per page) ---
            print("\n--- Page 1 ---")
            page_size = 5  # Request 5 ads per page
            ads_page1, search_cursor_page1 = await driver.get_ads_page(
                page_size=page_size,
                niche_keywords=["crypto"],
                placements=["facebook", "instagram"],
                countries=["US", "CA"],
                ad_type="all",
                period="month",
                keyword="solana",
                # No 'search_cursor' for the first call
            )

            print(f"Collected {len(ads_page1)} ads for Page 1.")
            for i, ad in enumerate(ads_page1):
                print(f"  Ad {i + 1} ID: {ad['id']}")
            print(f"Next search cursor for Page 1: {'exists' if search_cursor_page1 else 'None'}")

            # --- Second Page (if cursor exists) ---
            if search_cursor_page1:
                print("\n--- Page 2 ---")
                ads_page2, search_cursor_page2 = await driver.get_ads_page(
                    page_size=page_size,
                    search_cursor=search_cursor_page1,  # Pass the cursor from the previous page
                    niche_keywords=["crypto"],  # Re-pass original search parameters
                    placements=["facebook", "instagram"],
                    countries=["US", "CA"],
                    ad_type="all",
                    period="month",
                    keyword="solana",
                )
                print(f"Collected {len(ads_page2)} ads for Page 2.")
                for i, ad in enumerate(ads_page2):
                    print(f"  Ad {i + 1} ID: {ad['id']}")
                print(f"Next search cursor for Page 2: {'exists' if search_cursor_page2 else 'None'}")

            # You can continue calling get_ads_page in a loop until search_cursor is None

        except Exception as e:
            logging.error(f"Error during main execution: {e}")
        finally:
            await driver.close()


    asyncio.run(run_main())