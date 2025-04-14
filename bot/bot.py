from typing import Union
from datetime import datetime
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram import Router, F, types, Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bot_utils import *

PAYMENT_WALLET: str = os.environ.get('PAYMENT_WALLET', "")
TOKEN: str = os.environ.get('TG_TOKEN', "")
API_URL: str = os.environ.get('BASE_SITE', "")
API_KEY: str = os.environ.get('TG_API_KEY', "tg_api_key")
GIF_URL: str = ""
MAX_BUTTONS_PER_MESSAGE = 10

PAYMENT_PLAN: dict = {5: 10, 50: 90, 250: 450}

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='Markdown'))
dp = Dispatcher()
tg_router = Router()
dp.include_router(tg_router)


@tg_router.startup()
async def on_startup(bot: Bot):
    await set_bot_commands(bot)


async def set_bot_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Start the bot"),
        types.BotCommand(command="add_wallet", description="Authorize with your wallet"),
        types.BotCommand(command="buy_credits", description="Buy credits"),
        types.BotCommand(command="get_report_menu", description="Get a report"),
        types.BotCommand(command="help", description="Show help menu")
    ]
    await bot.set_my_commands(commands)


@tg_router.message(Command("help"))
async def show_commands(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📌 Start", callback_data="cmd_start")],
            [InlineKeyboardButton(text="💼 Add wallet", callback_data="cmd_add_wallet")],
            [InlineKeyboardButton(text="📊 Buy credits", callback_data="cmd_buy_credits")],
            [InlineKeyboardButton(text="📉 Get Report", callback_data="cmd_get_report")],
            [InlineKeyboardButton(text="ℹ️ Help", callback_data="cmd_help")]
        ]
    )
    await message.answer("🔹 Choose a command:", reply_markup=keyboard)


@tg_router.callback_query(F.data.startswith("cmd_"))
async def handle_command_callback(callback: types.CallbackQuery):
    command_map = {
        "cmd_start": "/start - Start the bot",
        "cmd_add_wallet": "/add_coin - Authorize with your wallet",
        "cmd_buy_credits": "/buy_credits - Buy credits",
        "cmd_get_report": "/get_report_menu - Get a report",
        "cmd_help": "/help - Show help message"
    }
    command = command_map.get(callback.data)
    if command:
        await callback.message.answer(f"Executing {command}...")  # Optional message
        await callback.answer()  # Closes the loading animation
        await tg_router.message.dispatch(
            types.Message(chat=callback.message.chat, text=command, from_user=callback.from_user, date=datetime.now()))


@tg_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BotState.entering_wallet)
    await message.answer(
        "Hi! I am a robust ad spy tool designed specifically for marketers, ad creators, and e-commerce sellers. With BigSpy, users can gain deep insights into market trends, optimize ad creatives, and gain a competitive edge.")
    await message.answer("Enter your crypto-wallet to authorize:")


@tg_router.message(BotState.entering_wallet)
async def save_wallet(message: types.Message, state: FSMContext):
    wallet = message.text.strip()
    result, msg = validate_wallet(address=wallet)
    if result:
        response = requests.post(f"{API_URL}/connect_telegram",
                                 json={"telegram_id": str(message.from_user.id), "wallet": wallet})
        if response.status_code == 200:
            await state.set_state(BotState.show_main_menu)
            await message.answer(
                "Wallet saved! Choose action below:")
        else:
            await message.answer("Error wallet adding. Try another one time.")
    else:
        await message.answer(msg)
        await message.answer("Enter your crypto-wallet to create your own portfolio:")
        await state.set_state(BotState.entering_wallet)


@tg_router.message(Command("main_menu"))
async def main_menu(message: types.Message):
    telegram_id = message.from_user.id if message.from_user.id != self_id else message.chat.id
    response = requests.get(f"{API_URL}", params={"telegram_id": str(telegram_id)})

    if response.status_code == 200:
        data = response.json()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Credits", callback_data="credits_menu"),
                 InlineKeyboardButton(text="Favourites", callback_data="favourite_menu")],
                [InlineKeyboardButton(text="Get report", callback_data="get_report_menu")]
            ]
        )

        await message.answer("Your portfolio:", reply_markup=keyboard)
    else:
        await message.answer("Error portfolio getting.")


@tg_router.callback_query(F.data == "credits_menu")
async def show_credits_menu(callback: types.CallbackQuery, state: FSMContext):
    response = requests.get(f"{API_URL}/credits", params={"telegram_id": str(callback.from_user.id)})

    if response.status_code == 200:
        data = response.json()
        credits_count = data.get("credits")
        await callback.message.answer(f"Your balance: {credits_count}")

        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=f"{k} credits - {v}$")] for k, v in PAYMENT_PLAN.items()],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback.message.answer("Choose plan:", reply_markup=keyboard)
        await state.set_state(BotState.buy_credits)
    else:
        await callback.message.answer("Unauthorized.")


@tg_router.callback_query(F.data == "cancel_credits")
async def cancel_delete(callback: types.CallbackQuery):
    await main_menu(callback.message)


@tg_router.message(BotState.buy_credits)
async def buy_credits(message: types.Message, state: FSMContext):
    credits_count = message.text.split()[0]
    await message.answer(f"Make payment {PAYMENT_PLAN.get(credits_count)} to the wallet:")
    await message.answer(f"_*{PAYMENT_WALLET}*_")
    await state.set_state(BotState.check_payment)
    await state.update_data(credits_count=credits_count)


@tg_router.message(BotState.check_payment)
async def buy_credits(message: types.Message, state: FSMContext):
    response = requests.post(f"{API_URL}", json={
        "telegram_id": str(message.from_user.id),
        "credits_count": state.get_state(),
    })
    if response.status_code == 200:
        await message.answer(f"Congratulations! You receive {state.get_state()} credits.")
        await main_menu(message)


if __name__ == "__main__":
    dp.run_polling(bot)
