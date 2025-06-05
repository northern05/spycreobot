import logging
import os
import re

import httpx
import requests
import string
from urllib.parse import urlparse
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from playwright.async_api import async_playwright

API_URL: str = os.environ.get('BASE_SITE', "https://api.agent.zpoken.dev/portfolio_tracker/api/v1/portfolio")
WALLET_REGEX = {
    "Tron (TRC-20)": r"^T[a-zA-Z0-9]{33}$"
}


class BotState(StatesGroup):
    entering_wallet = State()
    show_main_menu = State()
    buy_credits = State()
    check_payment = State()


class CreativesState(StatesGroup):
    choose_niche = State()
    choose_placement = State()
    choose_country = State()
    choose_type = State()
    choose_period = State()
    enter_keywords = State()


def get_similar_tokens(symbol: str, token_id: str = None):
    params = {"asset_symbol": symbol}
    if token_id:
        params.update({"token_id": token_id})
    result = requests.get(f"{API_URL}/similar_assets", params=params)
    return result.json()


def validate_wallet(address: str):
    for blockchain, pattern in WALLET_REGEX.items():
        if re.match(pattern, address):
            return True, f"✅ Valid {blockchain} wallet!"
    return False, "❌ Invalid wallet address."


def format_market_cap(market_cap):
    """Formats the market cap to a human-readable format (B, M, K)."""
    if market_cap >= 1_000_000_000:  # Billion
        return f"MCap {market_cap / 1_000_000_000:.1f}B"
    elif market_cap >= 1_000_000:  # Million
        return f"MCap {market_cap / 1_000_000:.1f}M"
    elif market_cap >= 1_000:  # Thousand
        return f"MCap {market_cap / 1_000:.1f}K"
    else:
        return f"MCap {market_cap}"


def escape_markdown(text):
    """
    Escapes special characters for Telegram MarkdownV2 formatting.
    """
    try:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        result = re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text).replace("</s>", "")
    except Exception as e:
        return None
    return result


def format_urls_in_report(report):
    report = re.sub(r'\s*,\s*', ' ', report).strip()

    # Regular expression pattern to match URLs
    url_pattern = re.compile(r'https?://\S+')

    # Find all URLs in the report
    urls = url_pattern.findall(report)
    translator = str.maketrans('', '', string.punctuation)

    # Replace each URL with a numbered Markdown link
    for index, url in enumerate(urls, start=1):
        markdown_link = f'[{extract_domain(url)}]({url})\n'.replace(f"({url})", "")
        report = report.replace(url, markdown_link, 1)

    return report


def extract_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


def build_multi_select_keyboard(options: list[str], selected: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in options:
        is_selected = "✅ " if option in selected else ""
        builder.button(
            text=f"{is_selected}{option}",
            callback_data=f"toggle:{option}"
        )
    builder.button(text="✅ Submit", callback_data="submit")
    builder.adjust(2)  # 2 columns
    return builder.as_markup()


async def download_file(url: str, save_path: str) -> bool:
    """Завантажує файл за URL і зберігає його за вказаним шляхом."""
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', url, follow_redirects=True, timeout=60) as response:
                response.raise_for_status()
                with open(save_path, 'wb') as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            return True
    except httpx.RequestError as e:
        logging.error(f"Помилка завантаження файлу з {url}: {e}")
        return False
    except Exception as e:
        logging.error(f"Неочікувана помилка при завантаженні файлу з {url}: {e}")
        return False


async def extract_media_from_network(fb_ad_url: str) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        media_urls = []

        async def handle_response(response):
            url = response.url
            if re.search(r'\.(mp4|jpg|jpeg|png)', url) and "fbcdn.net" in url:
                media_urls.append(url)

        def choose_best_media(sources: list[str]) -> str | None:
            def is_valid_video(url):
                return ".mp4" in url and "video" in url and "fbcdn.net" in url

            def is_valid_image(url):
                return re.search(r'\.(jpg|jpeg|png)', url) and "fbcdn.net" in url and "s60x60" not in url

            def extract_size_score(url: str) -> int:
                # s640x640 → площа 640*640 = 409600
                match = re.search(r's(\d+)x(\d+)', url)
                if match:
                    return int(match.group(1)) * int(match.group(2))
                return 0

            # 🔍 Всі відео
            video_urls = list(filter(is_valid_video, sources))
            if video_urls:
                # Пріоритет: відео з найбільшою довжиною URL (як проксі на розмір)
                video_urls.sort(key=len, reverse=True)
                best_video = video_urls[0]
                return best_video

            # 🖼 Всі зображення
            image_urls = list(filter(is_valid_image, sources))
            if image_urls:
                # Пріоритет: зображення з найбільшою вказаною роздільною здатністю
                image_urls.sort(key=extract_size_score, reverse=True)
                best_image = image_urls[0]
                return best_image
            return None

        page.on("response", handle_response)

        await page.goto(fb_ad_url)
        await page.wait_for_timeout(100)  # зачекати на завантаження ресурсів

        # await browser.close()

        if media_urls:
            best_media = choose_best_media(media_urls)
            return best_media
        else:
            return None


if __name__ == '__main__':
    extract_media_from_network(
        "https://www.facebook.com/ads/archive/render_ad/?id=1066136002063331&access_token=EAAKCNpvlGQ8BOwMCBMOxrRWpLsyH5wTOhSbgMZCEMsrmzmT8E47RZAMmHA5Go9ZAHd996yGHmV4fDZA3blQy7tcY0DGwNmtCcEYIyRz6AwqNsRl3BSZCHbkNMQ72cBaGxwj4TLRwvWHv5eO2Nfmf5uZCnD2vpjOZB5iolVRD7zk4BCH5ZBYU2QGYMRbsJ7Df1S6EOitO")
