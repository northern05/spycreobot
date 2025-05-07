import bisect
import requests

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


def check_payments():
    response = requests.post(url="https://affhunter.net/bot/api/v1/projects/status_update")
    if response.status_code == 200:
        return {"ok": True}
    else:
        return {"ok": False}