from typing import Union
from datetime import datetime
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram import Router, F, types, Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bot_utils import *

PAYMENT_WALLET: str = os.environ.get('PAYMENT_WALLET', "")
TOKEN: str = os.environ.get('TG_TOKEN', "7844930689:AAHS0QHld0NXPEflZzMmbbTYr7TSp7Tet_E")
API_URL: str = os.environ.get('BASE_SITE', "https://affhunter.net/bot/api/v1")
API_KEY: str = os.environ.get('TG_API_KEY', "tg_api_key")
GIF_URL: str = "https://affhunter.net/bot/api/v1/portfolio/get-gif"
MAX_BUTTONS_PER_MESSAGE = 10

PAYMENT_PLAN: dict = {5: 10, 50: 90, 250: 450}

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='Markdown'))
dp = Dispatcher()
tg_router = Router()
dp.include_router(tg_router)

user_selection_state = {}


@tg_router.startup()
async def on_startup(_bot: Bot):
    await set_bot_commands(_bot)


async def set_bot_commands(_bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Start the bot"),
        types.BotCommand(command="add_wallet", description="Authorize with your wallet"),
        types.BotCommand(command="buy_credits", description="Buy credits"),
        types.BotCommand(command="credits_menu", description="Credits menu"),
        types.BotCommand(command="get_creatives", description="Get a creatives"),
        types.BotCommand(command="help", description="Show help menu")
    ]
    await _bot.set_my_commands(commands)


@tg_router.message(Command("help"))
async def show_commands(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📌 Start", callback_data="cmd_start")],
            [InlineKeyboardButton(text="💼 Add wallet", callback_data="cmd_add_wallet")],
            [InlineKeyboardButton(text="📊 Buy credits", callback_data="cmd_buy_credits")],
            [InlineKeyboardButton(text="Credits Menu", callback_data="cmd_credits_menu")],
            [InlineKeyboardButton(text="📉 Get Creatives", callback_data="cmd_get_creatives")],
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
        "cmd_get_creatives": "/get_creatives - Get creatives",
        "cmd_credits_menu": "/credits_menu - Credits menu",
        "cmd_help": "/help - Show help message"
    }
    command = command_map.get(callback.data)
    if command:
        await callback.message.answer(f"Executing {command}...")  # Optional message
        await callback.answer()  # Closes the loading animation
        await tg_router.message.dispatch(
            types.Message(
                chat=callback.message.chat,
                text=command,
                from_user=callback.from_user,
                date=datetime.now(),
                message_id=callback.message.message_id
            ))


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
        response = requests.post(f"{API_URL}/auth",
                                 json={"telegram_id": str(message.from_user.id), "wallet": wallet})
        if response.status_code == 200:
            await state.set_state(BotState.show_main_menu)
            await message.answer(
                "Wallet saved! Choose action below:")
        else:
            await message.answer("Error wallet adding. Try another one time.")
    else:
        await message.answer(msg)
        await message.answer("Enter your crypto-wallet to create your own creatives:")
        await state.set_state(BotState.entering_wallet)


@tg_router.message(Command("main_menu"))
async def main_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Credits", callback_data="credits_menu"),
             InlineKeyboardButton(text="Favourites", callback_data="favourite_menu")],
            [InlineKeyboardButton(text="Get report", callback_data="get_report_menu")]
        ]
    )

    await message.answer("Your creatives:", reply_markup=keyboard)


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


@tg_router.callback_query(F.data == "get_creatives")
async def ask_niche_creatives(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CreativesState.choose_niche)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Gambling", callback_data="niche:gambling"),
             InlineKeyboardButton(text="Crypto", callback_data="niche:crypto")],
            [InlineKeyboardButton(text="Nutra", callback_data="niche:nutra"),
             InlineKeyboardButton(text="Dating", callback_data="niche:dating")],
            [InlineKeyboardButton(text="Ecom", callback_data="niche:products"),
             InlineKeyboardButton(text="Gaming", callback_data="niche:gaming")],
            [InlineKeyboardButton(text="✅ Submit", callback_data="niche_submit")]
        ]
    )
    user_selection_state[callback.from_user.id] = {"niches": []}
    await callback.message.answer("Choose niches (multiple allowed):", reply_markup=keyboard)


@tg_router.callback_query(CreativesState.choose_niche)
async def toggle_niche(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    niche = callback.data.split(":")[1]
    selected = user_selection_state[user_id].get("niches", [])
    if niche in selected:
        selected.remove(niche)
    else:
        selected.append(niche)
    user_selection_state[user_id]["niches"] = selected
    await callback.answer(f"Selected niches: {', '.join(selected)}")


@tg_router.callback_query(F.data == "niche_submit")
async def submit_niches(callback: types.CallbackQuery, state: FSMContext):
    selected = user_selection_state.get(callback.from_user.id, {}).get("niches", [])
    await state.set_data({"niches": selected})
    await state.set_state(CreativesState.choose_placement)
    placements = ["Facebook", "Instagram", "TikTok", "Google"]
    buttons = [InlineKeyboardButton(text=p, callback_data=f"placement:{p.lower()}") for p in placements]
    rows = [[buttons[i], buttons[i + 1]] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="✅ Submit", callback_data="placement_submit")])
    user_selection_state[callback.from_user.id]["placements"] = []
    await callback.message.answer("Choose placements:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@tg_router.callback_query(CreativesState.choose_placement)
async def toggle_placement(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    placement = callback.data.split(":")[1]
    selected = user_selection_state[user_id].get("placements", [])
    if placement in selected:
        selected.remove(placement)
    else:
        selected.append(placement)
    user_selection_state[user_id]["placements"] = selected
    await callback.answer(f"Selected placements: {', '.join(selected)}")


@tg_router.callback_query(F.data == "placement_submit")
async def submit_placements(callback: types.CallbackQuery, state: FSMContext):
    selected = user_selection_state.get(callback.from_user.id, {}).get("placements", [])
    await state.update_data({"placements": selected})
    await state.set_state(CreativesState.choose_countries)
    countries = ["US", "UA", "DE", "FR", "UK"]
    buttons = [InlineKeyboardButton(text=country, callback_data=f"country:{country.lower()}") for country in countries]
    rows = [[buttons[i], buttons[i + 1]] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="✅ Submit", callback_data="country_submit")])
    user_selection_state[callback.from_user.id]["countries"] = []
    await callback.message.answer("Choose countries:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@tg_router.callback_query(CreativesState.choose_countries)
async def toggle_country(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    country = callback.data.split(":")[1].upper()
    selected = user_selection_state[user_id].get("countries", [])
    if country in selected:
        selected.remove(country)
    else:
        selected.append(country)
    user_selection_state[user_id]["countries"] = selected
    await callback.answer(f"Selected countries: {', '.join(selected)}")


@tg_router.callback_query(F.data == "country_submit")
async def submit_countries(callback: types.CallbackQuery, state: FSMContext):
    selected = user_selection_state.get(callback.from_user.id, {}).get("countries", [])
    await state.update_data({"countries": selected})
    await state.set_state(CreativesState.choose_type)
    types_ = ["image", "video", "meme", "none"]
    buttons = [InlineKeyboardButton(text=t.capitalize(), callback_data=f"media:{t}") for t in types_]
    rows = [[buttons[i], buttons[i + 1]] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="✅ Submit", callback_data="media_submit")])
    user_selection_state[callback.from_user.id]["media_types"] = []
    await callback.message.answer("Choose ad types:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@tg_router.callback_query(CreativesState.choose_type)
async def toggle_media_type(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    media = callback.data.split(":")[1]
    selected = user_selection_state[user_id].get("media_types", [])
    if media in selected:
        selected.remove(media)
    else:
        selected.append(media)
    user_selection_state[user_id]["media_types"] = selected
    await callback.answer(f"Selected types: {', '.join(selected)}")


@tg_router.callback_query(F.data == "media_submit")
async def submit_media(callback: types.CallbackQuery, state: FSMContext):
    selected = user_selection_state.get(callback.from_user.id, {}).get("media_types", [])
    await state.update_data({"media_types": selected})
    await state.set_state(CreativesState.choose_period)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Week", callback_data="week"),
             InlineKeyboardButton(text="Month", callback_data="month")],
            [InlineKeyboardButton(text="Quarter", callback_data="quarter"),
             InlineKeyboardButton(text="Half year", callback_data="half_year")]
        ]
    )
    await callback.message.answer("Choose creatives period:", reply_markup=keyboard)


@tg_router.message(CreativesState.choose_period)
async def ask_keywords_creatives(callback: types.CallbackQuery, state: FSMContext, message: types.Message):
    period = message.text
    await state.set_data({"period": period})
    await state.set_state(CreativesState.enter_keywords)
    await callback.message.answer("Enter keywords for creatives search:")


@tg_router.message(CreativesState.enter_keywords)
async def get_creatives(callback: types.CallbackQuery, state: FSMContext, message: types.Message):
    keywords = message.text
    await state.set_data({"keywords": keywords})
    await callback.message.answer("✅ All filters selected! Proceeding...")
    response = requests.get(url=f"{API_URL}/", params={})


if __name__ == "__main__":
    dp.run_polling(bot)

# гембла	Gambling	casino, slots, bet, gambling, sportsbook
# крипта	Crypto	crypto, bitcoin, ethereum, NFT, web3, blockchain
# нутра	Nutra (supplements/health offers)	weight loss, skin care, supplement, keto, anti-aging
# дейтинг	Dating	online dating, find love, match, tinder, singles near you
# товарка	Physical products / Ecom	buy now, limited offer, shipping, shop, ecommerce
# гейминг	Gaming (non-casino)	mobile game, free to play, MMORPG, strategy game, play now
