from types import SimpleNamespace
from datetime import datetime
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardButton
from aiogram import Router, F, types, Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bot_utils import *

PAYMENT_WALLET: str = os.environ.get("MASTER_WALLET", "TPFzv2TnCZCML8ubjxCEPKYqjMxzqZ3Eya")
TOKEN: str = os.environ.get('TG_TOKEN', "7844930689:AAHS0QHld0NXPEflZzMmbbTYr7TSp7Tet_E")
API_URL: str = os.environ.get('BASE_SITE', "https://affhunter.net/bot/api/v1")
API_KEY: str = os.environ.get('TG_API_KEY', "tg_api_key")
GIF_URL: str = "https://affhunter.net/bot/api/v1/creatives/get-gif"
MAX_BUTTONS_PER_MESSAGE = 10
SELF_ID = '7844930689'

PAYMENT_PLAN: dict = {5: 10, 50: 90, 250: 450}

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='Markdown'))
dp = Dispatcher()
tg_router = Router()
dp.include_router(tg_router)

user_selection_state = {}


@tg_router.startup()
async def on_startup(bot: Bot):
    await set_bot_commands(bot)


async def delete_previous_message(bot: Bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Error deleting message: {e}")


async def set_bot_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Start the bot"),
        types.BotCommand(command="add_wallet", description="Authorize with your wallet"),
        types.BotCommand(command="main_menu", description="Main menu"),
        types.BotCommand(command="buy_credits", description="Buy credits"),
        types.BotCommand(command="credits_menu", description="Credits menu"),
        types.BotCommand(command="get_creatives", description="Get a creatives"),
        types.BotCommand(command="help", description="Show help menu")
    ]
    await bot.set_my_commands(commands)


@tg_router.message(Command("help"))
async def show_commands(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📌 Start", callback_data="cmd_start")],
            [InlineKeyboardButton(text="💼 Add wallet", callback_data="cmd_add_wallet")],
            [InlineKeyboardButton(text="📊 Main menu", callback_data="cmd_main_menu")],
            [InlineKeyboardButton(text="💳 Credits menu", callback_data="cmd_credits_menu")],
            [InlineKeyboardButton(text="📉 Get Creatives", callback_data="cmd_get_creatives")],
            [InlineKeyboardButton(text="ℹ️ Help", callback_data="cmd_help")]
        ]
    )
    await message.answer("🔹 Choose a command:", reply_markup=keyboard)


@tg_router.callback_query(F.data.startswith("cmd_"))
async def handle_command_callback(callback: types.CallbackQuery):
    command_map = {
        "cmd_start": cmd_start,
        "cmd_main_menu": main_menu,
        "cmd_add_wallet": cmd_start,
        "cmd_get_creatives": ask_niche_creatives,
        "cmd_credits_menu": show_credits_menu,
        "cmd_help": show_commands,
    }

    command_func = command_map.get(callback.data)
    if not command_func:
        await callback.answer("Unknown command.", show_alert=True)
        return

    await callback.answer()
    fake_message = SimpleNamespace(
        chat=callback.message.chat,
        from_user=callback.from_user,
        text="/fake",
        date=datetime.now(),
        message_id=callback.message.message_id,
        answer=callback.message.answer
    )
    await command_func(fake_message)


@tg_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BotState.entering_wallet)
    await message.answer(
        "Hi! I am a robust ad spy tool designed specifically for marketers, ad creators, and e-commerce sellers. "
        "With BigSpy, users can gain deep insights into market trends, optimize ad creatives, and gain a competitive edge.")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Already added", callback_data="main_menu")]])
    await message.answer("Enter your crypto-wallet to authorize:", reply_markup=keyboard)


@tg_router.message(BotState.entering_wallet)
async def save_wallet(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id if str(message.from_user.id) != SELF_ID else message.chat.id
    wallet = message.text.strip()
    result, msg = validate_wallet(address=wallet)
    if result:
        response = requests.post(f"{API_URL}/auth",
                                 json={"telegram_id": str(telegram_id), "wallet": wallet})
        if response.status_code == 200:
            await state.set_state(BotState.show_main_menu)
            await message.answer(
                "Wallet saved! Choose action below:")
            await main_menu(message)
            await delete_previous_message(bot, message.chat.id, message.message_id)
        else:
            await message.answer("Error wallet adding. Try another one time.")
    else:
        await message.answer(msg)
        await message.answer("Enter your crypto-wallet to create your own creatives:")
        await state.set_state(BotState.entering_wallet)


@tg_router.message(Command("main_menu"))
@tg_router.callback_query(F.data == "main_menu")
async def main_menu(event: types.Message | types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Credits", callback_data="credits_menu")],
            [InlineKeyboardButton(text="Get creatives", callback_data="get_creatives")],
            [InlineKeyboardButton(text="Pinned", callback_data="get_fav_creatives")]
        ]
    )
    if isinstance(event, types.Message):
        await event.answer("Main menu:", reply_markup=keyboard)
    else:
        await event.message.answer("Main menu:", reply_markup=keyboard)


@tg_router.message(Command("credits_menu"))
@tg_router.callback_query(F.data == "credits_menu")
async def show_credits_menu(event: types.Message | types.CallbackQuery, bot: Bot):
    telegram_id = event.from_user.id if str(event.from_user.id) != SELF_ID else event.chat.id
    chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id

    response = requests.get(f"{API_URL}/credits", params={"telegram_id": str(telegram_id)})

    if response.status_code == 200:
        data = response.json()
        credits_count = data.get("credits")

        if isinstance(event, types.Message):
            await event.answer(f"Your balance: {credits_count}")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Show me the prices", callback_data="buy_credits")]]
            )
            await bot.send_message(chat_id, "Do you want to top up your balance?", reply_markup=keyboard)
        elif isinstance(event, types.CallbackQuery):
            await event.message.answer(f"Your balance: {credits_count}")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Show me the prices", callback_data="buy_credits")]]
            )
            await bot.send_message(chat_id, "Do you want to top up your balance?", reply_markup=keyboard)
            await event.answer()

    else:
        if isinstance(event, types.Message):
            await event.answer("Unauthorized.")
        elif isinstance(event, types.CallbackQuery):
            await event.message.answer("Unauthorized.")
            await event.answer()


@tg_router.callback_query(F.data == "buy_credits")
async def buy_credits_menu(callback: types.CallbackQuery, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=f"{k} credits - {v}$")] for k, v in PAYMENT_PLAN.items()],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback.message.answer("Choose plan:", reply_markup=keyboard)
    await state.set_state(BotState.buy_credits)
    await delete_previous_message(bot, callback.message.chat.id, callback.message.message_id)
    await callback.answer()


@tg_router.callback_query(F.data == "cancel_credits")
async def cancel_credits(callback: types.CallbackQuery):
    await main_menu(callback.message)


@tg_router.message(BotState.buy_credits)
async def buy_credits(message: types.Message, state: FSMContext):
    credits_count = message.text.split()[0]
    await message.answer(f"Make payment {PAYMENT_PLAN.get(int(credits_count))} USDC to the wallet:")
    await message.answer(f"_*{PAYMENT_WALLET}*_", parse_mode='MarkdownV2')
    await state.set_data({"credits": credits_count})
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Check payment", callback_data="check_payment")]]
    )
    await message.answer("Approve transaction when it will be successful", reply_markup=keyboard)


@tg_router.message(Command("check_payment"))
@tg_router.callback_query(F.data == "check_payment")
async def buy_credits(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id if str(callback.from_user.id) != SELF_ID else callback.message.chat.id
    credits_count = await state.get_data()
    response = requests.post(f"{API_URL}/credits", json={
        "telegram_id": str(telegram_id),
        "credits": int(credits_count.get("credits")),
    })
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            await callback.message.answer(f"Congratulations! You receive {credits_count.get('credits')} credits.")
        else:
            await callback.message.answer("New transactions not exists!")
        await main_menu(callback.message)
    elif isinstance(callback.message, types.CallbackQuery):
        await callback.answer()


@tg_router.message(Command("get_creatives"))
@tg_router.callback_query(F.data == "get_creatives")
async def ask_niche_creatives(event: types.Message | types.CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(CreativesState.choose_niche)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Gambling", callback_data="niche:gambling"),
             InlineKeyboardButton(text="Crypto", callback_data="niche:crypto")],
            [InlineKeyboardButton(text="Nutra", callback_data="niche:nutra"),
             InlineKeyboardButton(text="Dating", callback_data="niche:dating")],
            [InlineKeyboardButton(text="Ecom", callback_data="niche:products"),
             InlineKeyboardButton(text="Gaming", callback_data="niche:gaming")]
        ]
    )
    if isinstance(event, types.Message):
        await event.answer("Choose one niche:", reply_markup=keyboard)
    elif isinstance(event, types.CallbackQuery):
        await event.message.answer("Choose one niche:", reply_markup=keyboard)
        await delete_previous_message(bot, event.message.chat.id, event.message.message_id)
        await event.answer()


@tg_router.callback_query(CreativesState.choose_niche, F.data.startswith("niche:"))
async def handle_niche_selection(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    niche = callback.data.split(":")[1]
    await state.set_data({"niche": niche})
    await state.set_state(CreativesState.choose_placement)

    placements = ["Facebook", "Instagram", "Messenger", "Audience_network"]
    buttons = [InlineKeyboardButton(text=p, callback_data=f"placement:{p.lower()}") for p in placements]
    rows = [[buttons[i], buttons[i + 1]] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="✅ Submit", callback_data="placement_submit")])

    user_selection_state[user_id] = {
        "niche": niche,
        "placements": []
    }

    await callback.message.answer(f"Niche selected: {niche.capitalize()}\nNow choose placements:",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await delete_previous_message(bot, callback.message.chat.id, callback.message.message_id)
    await callback.answer()


@tg_router.callback_query(CreativesState.choose_placement)
async def toggle_placement(callback: types.CallbackQuery, state: FSMContext):
    if callback.data.startswith("placement_submit"):
        await submit_placements(callback, state)
        return
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
    await delete_previous_message(bot, callback.message.chat.id, callback.message.message_id)
    geo_msg = await callback.message.answer("🌍 Enter geo code:")
    await state.update_data({"last_msg_id": geo_msg.message_id})
    await state.set_state(CreativesState.choose_country)


@tg_router.message(CreativesState.choose_country)
async def submit_country(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except Exception:
            pass
    await delete_previous_message(bot, message.chat.id, message.message_id)
    text = message.text.strip().upper()
    if len(text) < 2 or len(text) > 4:
        await message.answer("❌ Wrong geo code format. Please enter valid country code (e.g. US,CA,UA).")
        return
    await state.update_data({"country": text})
    await state.set_state(CreativesState.choose_type)
    types_ = ["image", "video", "all"]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t.capitalize(), callback_data=f"media:{t}") for t in types_]]
    )
    await message.answer("Choose ad types:", reply_markup=keyboard)


@tg_router.callback_query(CreativesState.choose_type)
async def toggle_media_type(callback: types.CallbackQuery, state: FSMContext):
    media = callback.data.split(":")[1]
    user_selection_state[callback.from_user.id]["ad_type"] = media
    await callback.answer(f"Selected type: {media.capitalize()}")
    await submit_media(callback, state)


@tg_router.callback_query(F.data == "media_submit")
async def submit_media(callback: types.CallbackQuery, state: FSMContext):
    selected = user_selection_state.get(callback.from_user.id, {}).get("ad_type", [])
    await state.update_data({"ad_type": selected})
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Week", callback_data="period:week"),
             InlineKeyboardButton(text="Month", callback_data="period:month")],
            [InlineKeyboardButton(text="Quarter", callback_data="period:quarter"),
             InlineKeyboardButton(text="Half year", callback_data="period:halfyear")]
        ]
    )
    await callback.message.answer("Choose creatives period:", reply_markup=keyboard)
    await state.set_state(CreativesState.choose_period)
    await delete_previous_message(bot, callback.message.chat.id, callback.message.message_id)


@tg_router.callback_query(F.data.startswith("period:"))
async def handle_period_selection(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data.split(":")[1]
    await state.update_data({"period": period})
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔽 Skip keyword", callback_data="skip_keyword")]
    ])

    await callback.message.answer(
        f"You selected period: {period}\n\n🔤 Please enter a keyword to filter creatives, or press *Skip* to continue without it:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    await state.set_state(CreativesState.enter_keywords)
    await delete_previous_message(bot, callback.message.chat.id, callback.message.message_id)


@tg_router.message(CreativesState.enter_keywords)
async def handle_keyword_input(message: types.Message, state: FSMContext):
    keyword = message.text.strip()
    await delete_previous_message(bot, message.chat.id, message.message_id)
    await state.update_data({"keyword": keyword})
    await proceed_creative_search(message, state)


@tg_router.callback_query(F.data == "skip_keyword")
async def handle_skip_keyword(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.update_data({"keyword": None})

    await proceed_creative_search(callback.message, state)


async def proceed_creative_search(message: types.Message, state: FSMContext):
    processing_message = await message.answer_animation(animation=GIF_URL,
                                                        caption="Processing your request...")

    telegram_id = message.from_user.id if str(message.from_user.id) != SELF_ID else message.chat.id
    data = await state.get_data()

    json = {
        "telegram_id": str(telegram_id),
        "niche": data.get("niche"),
        "placements": data.get("placements"),
        "country": data.get("country"),
        "ad_type": data.get("ad_type"),
        "period": data.get("period"),
        "keyword": data.get("keyword")  # може бути None
    }

    await send_creos(json=json, message=message, state=state, processing_message=processing_message)


@tg_router.callback_query(F.data == "next_ads_search")
async def next_ads_search(callback: types.CallbackQuery, state: FSMContext):
    processing_message = await callback.message.answer_animation(animation=GIF_URL,
                                                                 caption="Processing your request...")
    state_data = await state.get_data()
    json = {
        "telegram_id": str(callback.message.chat.id),
        "niche": state_data.get("niche"),
        "placements": state_data.get("placements"),
        "country": state_data.get("country"),
        "ad_type": state_data.get("ad_type"),
        "period": state_data.get("period"),
        "keyword": state_data.get("keyword"),
        "search_cursor": state_data.get("search_cursor")
    }
    await send_creos(json=json, message=callback.message, state=state, processing_message=processing_message)


@tg_router.callback_query(F.data == "pin_search")
async def pin_search(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id if str(message.from_user.id) != SELF_ID else message.chat.id
    data = await state.get_data()
    json = {
        "niche": data.get("niche"),
        "placements": data.get("placements"),
        "country": data.get("country"),
        "ad_type": data.get("ad_type"),
        "period": data.get("period"),
        "keyword": data.get("keyword"),
    }
    response = requests.post(url=f"{API_URL}/pins", json=json, params={"telegram_id": str(telegram_id)})
    if response.status_code == 200:
        await message.answer("Search successfully pins!")
    else:
        await message.answer("Something went wrong, try later :(")
    await main_menu(message)


@tg_router.callback_query(F.data == "get_fav_creatives")
async def get_fav_creatives(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id if str(callback.from_user.id) != SELF_ID else callback.message.chat.id
    response = requests.get(url=f"{API_URL}/pins", params={"telegram_id": str(telegram_id)})

    if response.status_code == 200:
        data = response.json()
        if not data:
            await callback.message.answer("No favorite pins found")
            return
        user_pins_data = {}

        for pin in data:
            pin_id = pin.get("id")
            user_pins_data[pin_id] = pin
            niche = pin.get("niche")
            placements = pin.get("placements")
            country = pin.get("country")
            ad_type = pin.get("ad_type")
            period = pin.get("period")
            keyword = pin.get("keyword")

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 Run search", callback_data=f"pin_run:{pin_id}")],
                    [InlineKeyboardButton(text="Delete search", callback_data=f"pin_delete:{pin_id}")]
                ]
            )
            msg = (
                f"*Niche:* {niche}\n"
                f"*Placements:* {placements}\n"
                f"*Country:* {country}\n"
                f"*Type:* {ad_type}\n"
                f"*Period:* {period}\n"
            )
            if keyword: msg += f"*Keyword:* {keyword}"
            await callback.message.answer(
                msg,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        await state.update_data(user_pins=user_pins_data)
    else:
        await callback.message.answer("Something went wrong!")
        await main_menu(callback.message)


@tg_router.callback_query(F.data.startswith("pin_run:"))
async def run_saved_pin(callback: types.CallbackQuery, state: FSMContext):
    # ⏳ Optional loading message
    processing_message = await callback.message.answer_animation(
        animation=GIF_URL,
        caption="Processing your saved search..."
    )
    pin_id_from_callback = callback.data.split(":")[1]
    user_data = await state.get_data()
    user_pins = user_data.get("user_pins", {})

    selected_pin = user_pins.get(int(pin_id_from_callback))

    if not selected_pin:
        await callback.message.answer("Error: Pin data not found \n Please try again or start over")
        await callback.answer()
        return

    niche = selected_pin.get("niche", [])
    placements = selected_pin.get("placements", [])
    country = selected_pin.get("country", [])
    ad_type = selected_pin.get("ad_type", "all")  # Default 'all'
    period = selected_pin.get("period", "week")  # Default 'week'
    keyword = selected_pin.get("keyword")
    data = {
        "telegram_id": str(callback.from_user.id),
        "niche": niche,
        "placements": placements,
        "country": country,
        "ad_type": ad_type,
        "period": period,
        "keyword": keyword,
    }
    await state.update_data(data)
    await send_creos(json=data, message=callback.message, state=state, processing_message=processing_message)


@tg_router.callback_query(F.data.startswith("pin_delete:"))
async def delete_saved_pin(callback: types.CallbackQuery, state: FSMContext):
    pin_id_from_callback = callback.data.split(":")[1]
    response = requests.delete(url=f"{API_URL}/pins/{pin_id_from_callback}")
    if response.status_code == 200:
        await callback.message.answer("Search successfully deleted!")
    else:
        await callback.message.answer("Something went wrong.")
        await main_menu(callback.message)


@tg_router.callback_query(F.data.startswith("get_similar:"))
async def similar_search(callback: types.CallbackQuery, state: FSMContext):
    page_name = callback.data.split(":")[1]
    user_data = await state.get_data()
    processing_message = await callback.message.answer_animation(animation=GIF_URL,
                                                                 caption="Processing your request...")

    telegram_id = callback.message.from_user.id if str(
        callback.message.from_user.id) != SELF_ID else callback.message.chat.id

    json = {
        "telegram_id": str(telegram_id),
        "country": user_data.get("country"),
        "page_name": page_name,
    }

    await state.update_data(json)

    await send_similar_creos(
        json=json,
        message=callback.message,
        processing_message=processing_message,
        state=state
    )


@tg_router.callback_query(F.data == "next_similar_search")
async def next_ads_search(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = callback.message.from_user.id if str(
        callback.message.from_user.id) != SELF_ID else callback.message.chat.id
    processing_message = await callback.message.answer_animation(animation=GIF_URL,
                                                                 caption="Processing your request...")
    user_data = await state.get_data()
    state_data = await state.get_data()
    json = {
        "telegram_id": str(telegram_id),
        "country": user_data.get("country"),
        "page_name": user_data.get("page_name"),
        "search_cursor": state_data.get("search_cursor")
    }
    await send_similar_creos(json=json, message=callback.message, state=state, processing_message=processing_message)


async def send_similar_creos(
        json: dict,
        message: types.Message,
        state: FSMContext,
        processing_message: types.Message
):
    response = requests.get(url=f"{API_URL}/creatives/similar", json=json)
    if response.status_code == 402:
        await message.answer("You have not enough credits to get creatives! \nTo continue - buy credits!")
        await show_credits_menu(event=message, bot=bot)
    elif response.status_code == 200:
        data = response.json()

        if not data.get("ads"):
            await message.answer("No ads by your query", parse_mode='MarkdownV2')

        ads = data.get("ads")
        search_cursor = data.get("after")
        await state.update_data({"search_cursor": search_cursor})
        await bot.delete_message(
            chat_id=processing_message.chat.id,
            message_id=processing_message.message_id
        )
        for creative in ads:
            url = creative.get('url')
            media_url = creative.get('media_url')
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔗 Open Ad in Browser", url=url)]]
            )

            if media_url and "video" in media_url:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=media_url,
                    reply_markup=keyboard
                )
            elif media_url and any(ext in media_url for ext in [".jpg", ".jpeg", ".png"]):
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=media_url,
                    reply_markup=keyboard
                )
            else:
                # fallback якщо немає медіа, лише лінк
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"🔗 [Open media]({url})",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Next", callback_data="next_similar_search")],
                             [InlineKeyboardButton(text="Main menu", callback_data="main_menu")]]
        )
        await message.answer("Do you want to get next 10 creatives?", reply_markup=keyboard)
    else:
        await message.answer("Something went wrong!")
        await main_menu(event=message)


async def send_creos(
        json: dict,
        message: types.Message,
        state: FSMContext,
        processing_message: types.Message
):
    response = requests.get(url=f"{API_URL}/creatives", json=json)
    if response.status_code == 402:
        await message.answer("You have not enough credits to get creatives! \nTo continue - buy credits!")
        await show_credits_menu(event=message, bot=bot)
    elif response.status_code == 200:
        data = response.json()

        if not data.get("ads"):
            await message.answer("No ads by your query", parse_mode='MarkdownV2')

        ads = data.get("ads")
        search_cursor = data.get("after")
        await state.update_data({"search_cursor": search_cursor})
        await bot.delete_message(
            chat_id=processing_message.chat.id,
            message_id=processing_message.message_id
        )
        for creative in ads:
            url = creative.get('url')
            media_url = creative.get('media_url')
            page_name = creative.get("page_name")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔗 Open Ad in Browser", url=url),
                    InlineKeyboardButton(text="Get similar", callback_data=f"get_similar:{page_name}")
                ]]
            )

            if media_url and "video" in media_url:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=media_url,
                    reply_markup=keyboard
                )
            elif media_url and any(ext in media_url for ext in [".jpg", ".jpeg", ".png"]):
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=media_url,
                    reply_markup=keyboard
                )
            else:
                # fallback якщо немає медіа, лише лінк
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"🔗 [Open media]({url})",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Next", callback_data="next_ads_search")],
                             [InlineKeyboardButton(text="Main menu", callback_data="main_menu")],
                             [InlineKeyboardButton(text="Pin search", callback_data="pin_search")]]
        )
        await message.answer("Do you want to get next 10 creatives?", reply_markup=keyboard)
    else:
        await message.answer("Something went wrong!")
        await main_menu(event=message)


if __name__ == "__main__":
    dp.run_polling(bot)
