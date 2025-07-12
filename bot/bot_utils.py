import asyncio
import logging
import os
import re

from datetime import datetime, timedelta
import httpx
import requests
import string
from urllib.parse import urlparse

from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot

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


async def send_and_update_timer(bot: Bot, chat_id: int, initial_duration: int = 120, interval: int = 1):
    try:
        pinned_message = await bot.send_message(
            chat_id=chat_id,
            text=f"We process your request as soon as possible, but ads are heavy, please wait for quality result.... "
        )
        logging.info(f"Initial timer sent for chat {chat_id}, message_id: {pinned_message.message_id}")
        timer_task = asyncio.create_task(
            _update_timer_task(bot, pinned_message.chat.id, pinned_message.message_id, initial_duration, interval)
        )
        return pinned_message.message_id, timer_task
    except Exception as e:
        logging.error(f"Error sending initial timer message: {e}")
        return None, None


async def _update_timer_task(bot: Bot, chat_id: int, message_id: int, duration: int, interval: int):
    timer_msg = await bot.send_message(
        chat_id=chat_id,
        text=f"Start counting!"
    )
    for remaining_time in range(duration - interval, -1, -interval):
        try:
            if remaining_time > 0:
                text_to_edit = f"Please wait searching ads... ⏳ {remaining_time} seconds"
            else:
                text_to_edit = "The search took longer than expected. Please wait."

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=timer_msg.message_id,
                text=text_to_edit
            )
            logging.debug(f"Updated timer for {chat_id}:{message_id} to {remaining_time}s")

            if remaining_time > 0:
                await asyncio.sleep(interval)
            else:
                break

        except asyncio.CancelledError:
            logging.info(f"Timer task for message {message_id} was cancelled externally.")
            break
        except TelegramBadRequest as e:
            if "message to edit not found" in e.message:
                logging.warning(f"Timer message {message_id} not found on Telegram. Stopping update task.")
                break
            raise
        except Exception as e:
            logging.error(f"Error updating timer message {message_id}: {e}")
            break
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        await bot.delete_message(chat_id=chat_id, message_id=timer_msg.message_id)
    except Exception as e:
        logging.error(f"Msg not exists {str(e.args)}")
    logging.info(f"Timer task for {chat_id}:{message_id} completed its internal countdown.")


def calculate_date_filter(period: str) -> datetime:
    delta = {
        "week": timedelta(days=7),
        "month": timedelta(days=30),
        "quarter": timedelta(days=90),
        "halfyear": timedelta(days=180),
        "year": timedelta(days=365)
    }.get(period, timedelta(days=366))

    date_only = datetime.utcnow().date() - delta
    return datetime.combine(date_only, datetime.min.time())
