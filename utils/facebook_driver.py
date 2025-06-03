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

    async def search_ads_or(
            self,
            niche_keywords: List[str],
            placements: Optional[List[str]] = None,
            countries: Optional[str] = None,
            ad_type: Optional[str] = None,
            period: str = "week",
            keyword: Optional[str] = None,
            limit: int = 10,
            after: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Returns:
            - ads: List of ads (max `limit`)
            - cursor: 'after' string for pagination (or None)
        """
        keywords = []
        if keyword:
            keywords.append(keyword.lower())
        for niche in niche_keywords:
            keywords.extend([kw.lower() for kw in NICHE_KEYWORDS.get(niche, [])])
        keywords = sorted(list(set(keywords)))

        params = {
            "access_token": self.access_token,
            "search_terms": ",".join(keywords),  # OR-style search
            "ad_reached_countries": countries,
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

        data = await self._fetch_ads(params)
        raw_ads = data.get("data", [])
        next_cursor = data.get("paging", {}).get("cursors", {}).get("after")

        formatted_ads = []
        for ad in raw_ads:
            formatted = self._format_ad(ad, placements)
            if formatted:
                formatted_ads.append(formatted)

        return formatted_ads, next_cursor

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


        except Exception as e:
            logging.error(f"Error during main execution: {e}")
        finally:
            await driver.close()


    asyncio.run(run_main())
