import logging
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Tuple, Dict, Any
import itertools
import hashlib  # Import hashlib for hashing content

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

NICHE_KEYWORDS = {
    "gambling": ["casino", "slots", "betting", "poker", "blackjack", "online casino", "sports betting"],
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
            limit: int,  # Limit per API call
            after: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Internal helper to search for ads for a single search term/combination.
        Returns (formatted_ads, next_cursor).
        """
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

    async def _orchestrate_search_terms(
            self,
            niche_keywords: List[str],
            placements: Optional[List[str]],
            countries: Optional[List[str]],
            ad_type: Optional[str],
            period: str,
            keyword: Optional[str],
            api_call_limit: int,  # Limit per *internal* API call
            start_combination_index: int,  # To continue overall search
            start_cursor: Optional[str]  # To continue overall search
    ) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
        """
        Generates and searches ads using keyword combinations, managing pagination and term advancement.
        Returns (ads_chunk, next_cursor_for_term, next_combination_index).
        """
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
            return [], None, -1  # Indicates no more combinations

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
        # Define the specific title to exclude
        EXCLUDED_TITLE = "This content was removed because it didn't follow our Advertising Standards."

        if not ad.get("id"):
            logging.warning("Ad ID is missing, skipping ad.")
            return None
        if not ad.get("ad_snapshot_url"):
            logging.warning(f"Ad snapshot URL is missing for ad ID {ad.get('id')}, skipping ad.")
            return None

        try:
            # Safely get the title, defaulting to an empty string to prevent errors
            title = ad.get("ad_creative_link_titles", [""])[0] if ad.get("ad_creative_link_titles") else ""

            # NEW: Exclude ads with the specific title
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

            # Use the already obtained 'title' variable
            description = ad.get("ad_creative_link_descriptions", [""])[0] if ad.get(
                "ad_creative_link_descriptions") else ""
            body = ad.get("ad_creative_bodies", [""])[0] if ad.get("ad_creative_bodies") else ""

            return {
                "id": ad["id"],
                "title": title,  # Use the title that was already checked
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

    async def get_unique_ads(self, target_limit: int = 10, **search_params: Any) -> List[Dict[str, Any]]:
        """
        Fetches a specified target_limit of unique ads across multiple search term combinations
        and pagination pages. Ads are de-duplicated by Facebook ID and content hash.

        Args:
            target_limit: The total number of unique ads to collect.
            **search_params: Parameters for the ad search (e.g., niche_keywords, placements,
                             countries, ad_type, period, keyword, limit).
                             'limit' here will be passed as api_call_limit to internal methods.

        Returns:
            A list of dictionaries, where each dictionary represents a unique ad.
        """
        all_collected_ads: List[Dict[str, Any]] = []
        seen_ad_ids: set = set()
        seen_content_hashes: set = set()

        # Extract initial state from search_params, clean up for passing to _orchestrate_search_terms
        current_keyword_combination_index = search_params.pop('start_combination_index', 0)
        current_cursor = search_params.pop('start_cursor', None)
        api_call_limit = search_params.pop('limit', 10)  # API call limit (e.g., 10 or 25 ads per FB request)

        logging.info(f"Starting to fetch {target_limit} unique ads with API limit {api_call_limit} per call.")

        while len(all_collected_ads) < target_limit:
            try:
                ads_chunk, next_cursor_for_term, next_combination_index = await self._orchestrate_search_terms(
                    api_call_limit=api_call_limit,  # Pass the specific API call limit here
                    start_combination_index=current_keyword_combination_index,
                    start_cursor=current_cursor,
                    **search_params  # Pass all other search parameters
                )

                if not ads_chunk and next_combination_index == -1:
                    logging.info("No more ads available from any search combination.")
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
                        if len(all_collected_ads) >= target_limit:
                            logging.info(f"Target limit of {target_limit} ads reached.")
                            return all_collected_ads[:target_limit]  # Return exactly target_limit ads

                # --- Pagination and Combination Advancement Logic ---
                if next_cursor_for_term:
                    # More pages for the current combination term
                    current_cursor = next_cursor_for_term
                    current_keyword_combination_index = next_combination_index  # Stay on current combination index
                    logging.info(
                        f"Continuing pagination for combination index {current_keyword_combination_index}. Next cursor: {current_cursor}")
                else:
                    # Current combination term exhausted, move to the next combination
                    current_keyword_combination_index = next_combination_index + 1
                    current_cursor = None  # Reset cursor for the new combination term
                    logging.info(
                        f"Finished combination index {next_combination_index}. Moving to next: {current_keyword_combination_index}")

            except Exception as e:
                logging.error(f"Error during overall ad fetching: {e}. Stopping collection.")
                break

        logging.info(f"Collected {len(all_collected_ads)} ads, which is less than the target of {target_limit}.")
        return all_collected_ads

if __name__ == '__main__':
    async def run_main():
        driver = FacebookAdsLibraryDriver(
            access_token="EAAKCNpvlGQ8BO1XXTenZCSzuanZBswZAOlMxZC41gSWfeViZCrV2f3XUnwvfwdPl4jyh7B8ZCSvy79zvCfqSLBpWZCAApHZB6q6tjr2gfKTifAXFsbhnZBkkMsqmbZALqLdZAIrxwffbNAQzRyeV8CDxauyqhKZBowPEGnTebKgcjulsO5DmVR7L9HyIqcIjm0xoVFZAtDBzb4qkazQXZC3IZCWNlZBJsdxotMCQ7JeMxZCZBOCT7y4wZDZD",
            # Use a valid, active token
            app_id="706121008748815",
            app_secret="aff7dc896abd538f8e8050102bbbc793"
        )

        try:
            print("Starting combined and unique ad search...")
            # Example search for 'crypto' niche, and additional keyword 'solana'
            final_ads_list = await driver.get_unique_ads(  # Call the new method directly
                target_limit=10,  # Request a total of 10 unique ads
                niche_keywords=["crypto"],
                placements=["facebook", "instagram"],
                countries=["US", "CA"],
                ad_type="all",
                period="month",
                keyword="solana"
            )

            print(f"\nFinal collected {len(final_ads_list)} unique ads (up to target_limit).")
            for i, ad in enumerate(final_ads_list):
                print(f"--- Ad {i + 1} ---")
                print(f"  ID: {ad['id']}")
                print(f"  Title: {ad.get('title')}")
                print(f"  URL: {ad.get('url')}")
                print(f"  Platforms: {', '.join(ad.get('platforms'))}")
                print(f"  Days Running: {ad.get('days_running')}")
                print("-" * 20)

        except Exception as e:
            logging.error(f"Error during main execution: {e}")
        finally:
            await driver.close()

    asyncio.run(run_main())