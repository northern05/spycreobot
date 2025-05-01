import requests
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Callable


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

    def refresh_user_token(self):
        url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": self.access_token
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()["access_token"]

    async def _fetch_ads(self, params: dict):
        try:
            response = await self.client.get(self.api_url, params=params)
            if response.status_code == 401:
                # Token expired: refresh and retry
                self.access_token = self.refresh_user_token()
                params["access_token"] = self.access_token
                response = await self.client.get(self.api_url, params=params)

            response.raise_for_status()
            return response.json().get("data", [])
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}") from e
        except Exception as e:
            raise Exception(f"Failed to fetch Facebook Ads: {e}") from e

    async def search_ads(
            self,
            niche_keywords: List[str],
            placements: Optional[List[str]] = None,
            countries: Optional[List[str]] = None,
            ad_type: Optional[str] = None,  # 'image', 'video', 'none', 'meme'
            period: str = "week",
            keyword: Optional[str] = None,
            limit: int = 50
    ):
        search_terms = " ".join(niche_keywords)
        if keyword:
            search_terms += f" {keyword}"

        params = {
            "access_token": self.access_token,
            "search_terms": search_terms,
            "ad_reached_countries": ",".join(countries) if countries else None,
            "ad_active_status": "ALL",
            "media_type": ad_type.upper() if ad_type else "ALL",
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

        # Remove empty params
        params = {k: v for k, v in params.items() if v}

        ads = await self._fetch_ads(params)

        return [self._format_ad(ad, placements) for ad in ads if self._format_ad(ad, placements)]

    def _format_ad(self, ad: dict, placements: Optional[List[str]] = None):
        try:
            ad_platforms = ad.get("publisher_platforms", [])
            if placements and not any(p in ad_platforms for p in placements):
                return None

            start_time = ad.get("ad_delivery_start_time")
            stop_time = ad.get("ad_delivery_stop_time")
            start_dt = datetime.strptime(start_time, "%Y-%m-%d") if start_time else None
            end_dt = datetime.strptime(stop_time, "%Y-%m-%d") if stop_time else datetime.utcnow()
            days_running = (end_dt - start_dt).days if start_dt else 0

            return {
                "title": ad.get("ad_creative_link_titles", [None])[0],
                "description": ad.get("ad_creative_link_descriptions", [None])[0],
                "body": ad.get("ad_creative_bodies", [None])[0],
                "platforms": ad_platforms,
                "snapshot_url": ad.get("ad_snapshot_url"),
                "days_running": days_running,
            }
        except Exception as e:
            print(f"Error formatting ad: {e}")
            return None

    async def close(self):
        await self.client.aclose()


if __name__ == '__main__':
    async def main():

        driver = FacebookAdsLibraryDriver(
            access_token="EAAKCNpvlGQ8BO2MKCB3UOGJiF4kgya3SeWkK7R1uCkD4AlFmqkbD4Ox2AG9xZAbcpR6QkEDnJ6yBJFWrkR8SIU3RWSZAQaP5PMEO6Fi1hAg7pdja79L0vxfFDhFGUag24ls2VvNOQuEJbcbo93qGBI2PW7InOZAe3m2FAl3ZCUMl8nrBIqCgkenlBDRM6XwdQZC2OseS5kwtFRIYBEZCVu2cg55j1IgXEeZAAZDZD",
            app_id = "706121008748815",
            app_secret = "aff7dc896abd538f8e8050102bbbc793"
        )

        ads = await driver.search_ads(
            niche_keywords=["gambling", "slots"],
            placements=["facebook", "instagram"],
            countries=["US", "CA"],
            ad_type="video",
            period="month",
            keyword="blackjack"
        )

        for ad in ads:
            print(ad["title"], ad["snapshot_url"], ad["days_running"])
        await driver.close()


    asyncio.run(main())
