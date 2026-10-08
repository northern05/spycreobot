from datetime import datetime, timedelta

from app.api.creatives.schemas import CreativeCreate

PIN_DATA = dict(niche="gambling", placements=["facebook", "instagram"], country="UA",
                ad_type="video", period="month", keyword="casino")



def creative_data(**overrides):
    values = dict(niche="gambling", facebook_id="fb-1", title="Ad", description="Text",
                  platforms=["facebook"], geo=["ua"], facebook_url="https://example.com/ad",
                  created_at=datetime.utcnow() - timedelta(days=3), type="video", page_id="page-1",
                  media_url="https://example.com/video", app_url="https://example.com", score=1,
                  media_unique_identifier="media-1", button="Learn more")
    values.update(overrides)
    return CreativeCreate(**values)

