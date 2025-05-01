import os
import re
import requests
import string
from urllib.parse import urlparse
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup

API_URL: str = os.environ.get('BASE_SITE', "https://api.agent.zpoken.dev/portfolio_tracker/api/v1/portfolio")
self_id = 7540334723
WALLET_REGEX = {
    "Ethereum / BSC / Polygon (EVM-based)": r"^0x[a-fA-F0-9]{40}$",
    "Bitcoin": r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$",
    "Solana": r"^[1-9A-HJ-NP-Za-km-z]{32,44}$",
    "Tron (TRC-20)": r"^T[a-zA-Z0-9]{33}$",
    "Ripple (XRP)": r"^r[0-9a-zA-Z]{24,34}$",
    "Dogecoin": r"^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32,34}$",
    "Litecoin": r"^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$",
    "Cardano (ADA)": r"^addr1[a-z0-9]+$",
}


class BotState(StatesGroup):
    entering_wallet = State()
    show_main_menu = State()
    buy_credits = State()
    check_payment = State()


class CreativesState(StatesGroup):
    choose_niche = State()
    choose_placement = State()
    choose_countries = State()
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
    pattern = r'\[0_system\]|\[0_q_\d+\]|0_a_\d+'
    report = re.sub(pattern, '', report)
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
