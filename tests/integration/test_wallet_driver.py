import pytest
import httpx

from utils.wallet_driver import TronWalletDriver

pytestmark = pytest.mark.integration


async def driver_for(payload, status=200):
    driver = TronWalletDriver("https://wallet.test", "usdt-contract")
    await driver.client.aclose()
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, json=payload)

    driver.client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    return driver, requests


@pytest.mark.parametrize("payload,expected", [({"data": []}, 0), ({"data": [{}]}, 0),
    ({"data": [{"balance": 1_500_000}]}, 1.5)])
async def test_trx_balance_decoding(payload, expected):
    driver, requests = await driver_for(payload)
    try:
        assert await driver.get_balance("wallet") == expected
        assert requests[0].url.path == "/v1/accounts/wallet"
    finally:
        await driver.close()


async def test_usdt_incoming_minus_outgoing_balance():
    driver, requests = await driver_for({"data": [
        {"to_address": "wallet", "value": "10000000"},
        {"from_address": "wallet", "value": "2500000"},
        {"to_address": "other", "from_address": "other", "value": "99999999"},
    ]})
    try:
        assert await driver.get_usdt_balance("wallet") == 7.5
        assert requests[0].url.params["contract_address"] == "usdt-contract"
        assert requests[0].url.params["only_confirmed"] == "true"
    finally:
        await driver.close()


async def test_transaction_response_mapping():
    driver, requests = await driver_for({"data": [{
        "transaction_id": "tx", "value": "90000000", "from": "sender", "block_timestamp": 1000000,
        "token_info": {"address": "usdt-contract", "symbol": "USDT", "decimals": 6},
    }]})
    try:
        result = await driver.get_transactions("wallet", limit=20)
        assert len(result) == 1
        assert result[0]["tx_hash"] == "tx"
        assert result[0]["amount"] == 90000000
        assert result[0]["from_address"] == "sender"
        assert result[0]["decimals"] == 6
        assert result[0]["created_at"].timestamp() == 1000
        assert requests[0].url.params["limit"] == "20"
    finally:
        await driver.close()


@pytest.mark.parametrize("method", ["get_balance", "get_usdt_balance", "get_transactions"])
async def test_http_failures_are_not_silently_accepted(method):
    driver, _ = await driver_for({"error": "unavailable"}, status=503)
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await getattr(driver, method)("wallet")
    finally:
        await driver.close()


async def test_close_releases_http_client():
    driver, _ = await driver_for({})
    await driver.close()
    assert driver.client.is_closed
