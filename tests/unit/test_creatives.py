from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.api.creatives import crud, dependencies as dp
from app.api.creatives.schemas import CreativeRequest
from app.core.models import Creative
from utils.paginated_response import PaginatedParams

pytestmark = pytest.mark.unit


def ad_payload():
    return dict(id=1, title="ad", platforms=["facebook"], facebook_url="https://example.com/ad",
                media_url="https://example.com/video", days_running=2, type="video", geo=["ua"])


@pytest.mark.parametrize("has_ads", [True, False])
async def test_live_search_charges_only_for_results(monkeypatch, external_services, has_ads):
    external_services.fb_driver.get_ads_page.return_value = ([ad_payload()] if has_ads else [], {"next": "cursor"})
    spend = AsyncMock()
    monkeypatch.setattr(dp.credits_dp, "process_users_credits", spend)
    session = object()
    result = await dp.get_creatives(CreativeRequest(telegram_id="123", niche="gambling"), session)
    assert len(result["ads"]) == int(has_ads)
    assert result["after"] == {"next": "cursor"}
    assert "telegram_id" not in external_services.fb_driver.get_ads_page.call_args.kwargs
    if has_ads:
        spend.assert_awaited_once_with(session=session, telegram_id="123")
    else:
        spend.assert_not_awaited()


async def test_live_search_service_failure_does_not_charge(monkeypatch, external_services):
    external_services.fb_driver.get_ads_page.side_effect = RuntimeError("facebook offline")
    spend = AsyncMock()
    monkeypatch.setattr(dp.credits_dp, "process_users_credits", spend)
    with pytest.raises(RuntimeError, match="facebook offline"):
        await dp.get_creatives(CreativeRequest(telegram_id="123", niche="gambling"), object())
    spend.assert_not_awaited()


@pytest.mark.parametrize("days,expected", [(4, 4), (-2, 0)])
async def test_cached_result_computes_nonnegative_days(monkeypatch, days, expected):
    ad = Creative(**{k: v for k, v in ad_payload().items() if k != "days_running"},
                  created_at=datetime.utcnow() - timedelta(days=days))
    monkeypatch.setattr(crud, "paginate", AsyncMock(return_value=({"total_items": 1}, [ad])))
    result = await crud.get_all(object(), "", PaginatedParams(1, 10))
    assert result["ads"][0].days_running == expected
    assert result["total_items"] == 1


async def test_invalid_filter_returns_400_before_query(monkeypatch):
    filter_instance = MagicMock()
    filter_instance.get_query.side_effect = ValueError("bad filter")
    monkeypatch.setattr(crud, "CreativeFilter", MagicMock(return_value=filter_instance))
    paginate = AsyncMock()
    monkeypatch.setattr(crud, "paginate", paginate)
    with pytest.raises(HTTPException) as error:
        await crud.get_all(object(), "invalid", PaginatedParams(1, 10))
    assert error.value.status_code == 400
    paginate.assert_not_awaited()


@pytest.mark.parametrize("operator", ["array_eq", "array_ilike", "in_", "between"])
def test_filter_list_values_are_trimmed(operator):
    filter_instance = crud.CreativeFilter(Creative, crud.creative_query_filters)
    assert filter_instance._format_expression(Creative.geo, operator, " ua, pl ") == {"geo": ["ua", "pl"]}


def test_filter_datetime_and_invalid_date():
    filter_instance = crud.CreativeFilter(Creative, crud.creative_query_filters)
    assert filter_instance._format_expression(Creative.created_at, "gte", "2026-01-02")["created_at"] == datetime(2026, 1, 2)
    with pytest.raises(ValueError, match="Invalid datetime"):
        filter_instance._format_expression(Creative.created_at, "gte", "nonsense")


def test_array_ilike_compiles_for_postgres():
    filter_instance = crud.CreativeFilter(Creative, crud.creative_query_filters)
    expression = filter_instance._get_orm_for_field(Creative.geo, "array_ilike", ["UA", "PL"])
    compiled = expression.compile(dialect=postgresql.dialect())
    assert "ANY (creatives.geo)" in str(compiled)
    assert set(compiled.params.values()) == {"ua", "pl"}


async def test_cache_job_stops_when_no_cursor(monkeypatch, external_services):
    monkeypatch.setattr(dp, "COUNTRY_TO_KEYWORDS", {"UA": []})
    session = MagicMock()
    session.commit = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(dp.db_helper, "session_factory", MagicMock(return_value=context))
    assert await dp.update_all_creatives() == {"ok": True}
    assert external_services.fb_driver.get_ads_page.await_count == 2
    assert session.commit.await_count == 2
