import requests
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Callable


# NICHE_KEYWORDS = {
#     "gambling": ["casino", "slots", "betting", "poker", "blackjack"],
#     "crypto": ["crypto", "bitcoin", "ethereum", "nft", "web3"],
#     "nutra": ["supplement", "weight loss", "keto", "skincare"],
#     "dating": ["dating", "match", "love", "singles"],
#     "products": ["buy now", "shop", "discount", "shipping"],
#     "gaming": ["game", "mmorpg", "strategy", "mobile game"],
# }


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
        today = datetime.utcnow()
        delta = {
            "week": timedelta(days=7),
            "month": timedelta(days=30),
            "quarter": timedelta(days=90),
            "half_year": timedelta(days=180)
        }.get(period, timedelta(days=7))
        return (today - delta).strftime("%Y-%m-%d")

    async def exchange_token(self) -> str:
        """Exchange short-lived user token for a long-lived token."""
        url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": self.access_token
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            new_token = response.json().get("access_token")
            if not new_token:
                raise Exception("Token exchange failed: empty access_token in response.")
            self.access_token = new_token  # 🔐 Store new token in driver
            return new_token
        except requests.RequestException as e:
            raise Exception(
                f"Token exchange failed: {e.response.status_code if e.response else 'No response'} - {e}") from e

    async def _fetch_ads(self, params: dict) -> List[dict]:
        """Fetches ads from the Facebook Ads Library API, handling token refresh and errors."""
        retries = 2  # Number of retries
        for attempt in range(retries):
            try:
                response = await self.client.get(self.api_url, params=params)
                response.raise_for_status()  # Raise HTTPStatusError for bad status codes
                return response.json().get("data", [])
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 400) and attempt < retries - 1:  # Token expired, retry once
                    try:
                        self.access_token = await self.exchange_token()
                        params["access_token"] = self.access_token
                        print("Access token refreshed. Retrying...")
                    except Exception as refresh_error:
                        print(f"Token refresh failed: {refresh_error}")
                        raise Exception("Failed to refresh access token") from refresh_error
                else:
                    raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}") from e
            except httpx.RequestError as e:  # Catch connection errors
                print(f"Request error: {e}. Attempt {attempt + 1}/{retries}. Retrying...")
                if attempt < retries - 1:
                    await asyncio.sleep(2)  # Add a delay before retrying
                else:
                    raise Exception(f"Failed to fetch Facebook Ads after {retries} attempts: {e}") from e
            except Exception as e:
                raise Exception(f"Failed to fetch Facebook Ads: {e}") from e
        raise Exception("Failed to fetch Facebook Ads after multiple retries.")

    async def search_ads(
            self,
            niche_keywords: List[str],
            placements: Optional[List[str]] = None,
            countries: Optional[List[str]] = None,
            ad_type: Optional[str] = None,
            period: str = "week",
            keyword: Optional[str] = None,
            limit: int = 10,
            after: Optional[str] = None
    ) -> tuple:
        period = "half_year" if period == "halfyear" else period

        params = {
            "access_token": self.access_token,
            "search_terms": f"{keyword},".join(niche_keywords),
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
            ]),
            "limit": limit,
            "start_date": self._calculate_date_filter(period),
        }

        if after:
            params["after"] = after

        params = {k: v for k, v in params.items() if v}

        raw_response = await self.client.get(self.api_url, params=params)
        raw_response.raise_for_status()
        data = raw_response.json()

        raw_ads = data.get("data", [])
        next_cursor = data.get("paging", {}).get("cursors", {}).get("after")

        formatted_ads = []
        for ad in raw_ads:
            formatted = self._format_ad(ad, placements, keyword)
            if formatted:
                formatted_ads.append(formatted)

        return formatted_ads[:limit], next_cursor

    def _format_ad(
            self,
            ad: dict,
            placements: Optional[List[str]],
            keyword: Optional[str] = None
    ) -> Optional[dict]:
        if not ad.get("ad_snapshot_url"):  # ad is likely deleted or restricted
            return None

        start_time = ad.get("ad_delivery_start_time")
        stop_time = ad.get("ad_delivery_stop_time")
        if start_time:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d")
            end_dt = datetime.strptime(stop_time, "%Y-%m-%d") if stop_time else datetime.utcnow()
            days_running = (end_dt - start_dt).days
        else:
            days_running = 0

        if placements:
            ad_platforms = ad.get("publisher_platforms", [])
            if not any(p in ad_platforms for p in placements):
                return None  # filter out ads not on desired platforms
        title = ad.get("ad_creative_link_titles", ["No title"])[0]
        description = ad.get("ad_creative_link_descriptions", [""])[0]
        body = ad.get("ad_creative_bodies", [""])[0]
        content = f"{title} {description} {body}".lower()

        if keyword and keyword.lower() not in content:
            return None

        return {
            "title": title,
            "description": description,
            "body": body,
            "platforms": ad.get("publisher_platforms", []),
            "url": ad.get("ad_snapshot_url"),
            "days_running": days_running,
            "content": content
        }

    async def close(self):
        await self.client.aclose()


if __name__ == '__main__':
    async def main():
        driver = FacebookAdsLibraryDriver(
            access_token="EAAKCNpvlGQ8BO92L4SjM3lcsjukZBrgNfaFeWhstohqZAc4Rbl8idd9ntzDMpwZCe6RhAht4sdAttPaec6a1BreIvz836QirNd1ydoWdJlLzOGZAnW7URV9A3o898aqwvfxa6X2tUC67Jg2ZCujCIIswOgVI0cNLVucTsDyY6joh73ZBMtGyacV8CzZANuFzYqI7xASZBmpgpxISj1yGqZBgly0JRRTHJ1E8joTr5FoLZAZCAZDZD",
            app_id="706121008748815",
            app_secret="aff7dc896abd538f8e8050102bbbc793"
        )

        ads, cursor = await driver.search_ads(
            niche_keywords=["crypto"],
            placements=["facebook", "instagram"],
            countries=["US", "CA", "UA"],
            ad_type="all",
            period="month",
            keyword="solana"
        )
        print(cursor)

        for ad in ads:
            print(ad["title"], ad["url"], ad["days_running"])
        await driver.close()


    asyncio.run(main())
