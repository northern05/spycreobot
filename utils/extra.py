import bisect
import requests
from urllib.parse import unquote, parse_qs

import itertools


def find_nearest_key(d: dict, num: int):
    keys = sorted(d.keys())
    idx = bisect.bisect_right(keys, num)
    return keys[idx - 1] if idx else None


def slice_dict_from_key(d, start_key):
    if start_key not in d:
        start_key = find_nearest_key(d, start_key)
    start_index = list(d.keys()).index(start_key)
    return dict(itertools.islice(d.items(), start_index, None))


def flatten_nested_list(nested_list):
    result = []
    for element in nested_list:
        if isinstance(element, list):
            result.extend(flatten_nested_list(element))
        else:
            result.append(element)
    return result


def cash_ads():
    response = requests.post(url="https://affhunter.net/bot/api/v1/creatives/update_ads")
    if response.status_code == 200:
        return {"ok": True}
    else:
        return {"ok": False}


def extract_geo_from_filter(filter_query: str) -> str | None:
    if not filter_query:
        return None
    decoded = unquote(filter_query)
    pairs = decoded.split('&')
    for pair in pairs:
        if pair.startswith("geo__ilike="):
            return pair.split("=", 1)[1]
    return None
