from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.core.models import User
from utils import extra
from utils.paginated_response import Paginator, PaginatedParams

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value,expected", [(-1, None), (10, 10), (15, 10), (20, 20), (100, 30)])
def test_nearest_key(value, expected):
    assert extra.find_nearest_key({30: "c", 10: "a", 20: "b"}, value) == expected


def test_slice_dict_uses_nearest_preceding_key():
    assert extra.slice_dict_from_key({10: "a", 20: "b", 30: "c"}, 25) == {20: "b", 30: "c"}


def test_flatten_preserves_order_and_nonlist_values():
    assert extra.flatten_nested_list([1, [2, [], [3]], None, (4, 5)]) == [1, 2, 3, None, (4, 5)]


@pytest.mark.parametrize("query,expected", [("", None), ("niche__eq=gambling", None),
    ("geo__ilike=UA", "UA"), ("niche__eq=x&geo__ilike%3DPL", "PL")])
def test_extract_geo(query, expected):
    assert extra.extract_geo_from_filter(query) == expected


@pytest.mark.parametrize("status,expected", [(200, True), (500, False)])
def test_scheduled_cache_request_result(monkeypatch, status, expected):
    request = MagicMock(return_value=MagicMock(status_code=status))
    monkeypatch.setattr(extra.requests, "post", request)
    assert extra.cash_ads() == {"ok": expected}
    request.assert_called_once_with(url="https://affhunter.net/bot/api/v1/creatives/update_ads")


@pytest.mark.parametrize("count,size,expected", [(0, 10, 0), (10, 10, 1), (11, 10, 2), (1, 2, 1)])
def test_pagination_page_count(count, size, expected):
    paginator = Paginator(object(), select(User), page_number=2, page_size=size)
    assert paginator._get_number_of_pages(count) == expected
    assert paginator.offset == size
    params = PaginatedParams(2, size)
    assert params.offset == size
    assert params.limit == size
