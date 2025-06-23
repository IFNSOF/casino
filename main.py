import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from datetime import datetime, timedelta
import random

BOT_TOKEN = "7566947238:AAHmgbEBcCRN45_KGqRiPHxzO-S0uHyGUjE"
CHANNEL_ID = --1002832455476
ADMIN_ID = 7816374758

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# --- DB ---
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            last_bonus TEXT
        )""")
        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_balance(user_id, amount):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def set_ban(user_id, status):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET banned = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

async def set_last_bonus(user_id, date_str):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (date_str, user_id))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT user_id, username, balance FROM users") as cursor:
            return await cursor.fetchall()

# --- Keyboards ---
def main_menu():
    return types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [types.KeyboardButton(text="👤 Профиль")],
        [types.KeyboardButton(text="🎮 Игры")],
        [types.KeyboardButton(text="🎁 Бонус"), types.KeyboardButton(text="🆘 Помощь")],
        [types.KeyboardButton(text="⚙️ Админ панель")] if False else []  # скрыто
    ])

def game_menu():
    return types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [types.KeyboardButton(text="📈 Трейд"), types.KeyboardButton(text="🎰 Слоты")],
        [types.KeyboardButton(text="🔙 Назад")]
    ])

def subscription_check():
    btn = types.InlineKeyboardMarkup()
    btn.add(types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub"))
    return btn

def admin_menu():
    return types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [types.KeyboardButton("📋 База данных")],
        [types.KeyboardButton("💸 Выдать деньги")],
        [types.KeyboardButton("🔒 Бан"), types.KeyboardButton("🔓 Разбан")],
        [types.KeyboardButton("🔙 Назад")]
    ])

# --- Handlers ---
@dp.message(CommandStart())
async def start(msg: Message):
    user = await get_user(msg.from_user.id)
    if user and user[3]: return await msg.answer("🚫 Вы забанены.")
    await add_user(msg.from_user.id, msg.from_user.username or "Без ника")
    chat = await bot.get_chat_member(CHANNEL_ID, msg.from_user.id)
    if chat.status not in ("member", "administrator", "creator"):
        return await msg.answer("📢 Подпишитесь на канал, чтобы пользоваться ботом", reply_markup=subscription_check())
    await msg.answer("👋 Добро пожаловать в меню!", reply_markup=main_menu())

@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    chat = await bot.get_chat_member(CHANNEL_ID, callback.from_user.id)
    if chat.status in ("member", "administrator", "creator"):
        await callback.message.edit_text("✅ Вы подписаны! Используйте /start")
    else:
        await callback.answer("❌ Вы не подписаны", show_alert=True)

@dp.message(F.text == "👤 Профиль")
async def profile(msg: Message):
    user = await get_user(msg.from_user.id)
    if not user: return
    await msg.answer(f"👤 Ник: @{user[1]}\n🆔 ID: {user[0]}\n💰 Баланс: {user[2]}$", reply_markup=main_menu())

@dp.message(F.text == "🎮 Игры")
async def games(msg: Message):
    await msg.answer("🎮 Выберите игру:", reply_markup=game_menu())

@dp.message(F.text == "📈 Трейд")
async def trade(msg: Message):
    await msg.answer("💸 Введите ставку:")
    dp.message.register(handle_trade_bet)

async def handle_trade_bet(msg: Message):
    try:
        bet = int(msg.text)
        user = await get_user(msg.from_user.id)
        if bet > user[2]:
            await msg.answer("❌ Недостаточно средств")
            return
        await msg.answer("📊 Выберите направление:\n📉 — Вниз\n📈 — Вверх", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[types.KeyboardButton("📉"), types.KeyboardButton("📈")]]))
        dp.message.register(lambda m: handle_trade_direction(m, bet))
    except:
        await msg.answer("⚠️ Введите число")

async def handle_trade_direction(msg: Message, bet):
    direction = msg.text
    result = random.choice(["📈", "📉"])
    if direction == result:
        await update_balance(msg.from_user.id, bet)
        await msg.answer(f"✅ Вы угадали! +{bet}$")
    else:
        await update_balance(msg.from_user.id, -bet)
        await msg.answer(f"❌ Не угадали! -{bet}$\nПравильный ответ: {result}")
    await msg.answer("🎮 Меню игр", reply_markup=game_menu())

@dp.message(F.text == "🎰 Слоты")
async def slots(msg: Message):
    await msg.answer("🎲 Введите ставку:")
    dp.message.register(handle_slots_bet)

async def handle_slots_bet(msg: Message):
    try:
        bet = int(msg.text)
        user = await get_user(msg.from_user.id)
        if bet > user[2]:
            await msg.answer("❌ Недостаточно средств")
            return
        symbols = ["🍒", "🍋", "🍇"]
        result = [random.choice(symbols) for _ in range(3)]
        win = result[0] == result[1] == result[2]
        await update_balance(msg.from_user.id, bet * 3 if win else -bet)
        await msg.answer(f"🎰 {' '.join(result)}\n{'🎉 Победа!' if win else '😢 Не повезло'}")
    except:
        await msg.answer("⚠️ Введите число")

@dp.message(F.text == "🎁 Бонус")
async def bonus(msg: Message):
    user = await get_user(msg.from_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if user[4] == today:
        return await msg.answer("🕒 Бонус уже получен сегодня")
    await update_balance(user[0], 500)
    await set_last_bonus(user[0], today)
    await msg.answer("✅ Вы получили 500$ бонуса!")

@dp.message(F.text == "🆘 Помощь")
async def help_msg(msg: Message):
    await msg.answer("📝 Напишите вашу жалобу или вопрос:")
    dp.message.register(lambda m: forward_to_admin(m, msg.from_user.id))

async def forward_to_admin(msg: Message, user_id):
    await bot.send_message(ADMIN_ID, f"📩 Сообщение от {user_id}:\n{msg.text}", reply_markup=types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✉️ Ответить", callback_data=f"reply:{user_id}")
    ))
    await msg.answer("✅ Отправлено админу")

@dp.callback_query(F.data.startswith("reply:"))
async def admin_reply_callback(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.answer("✏️ Введите ответ пользователю:")
    dp.message.register(lambda m: send_admin_reply(m, user_id))

async def send_admin_reply(msg: Message, user_id):
    await bot.send_message(user_id, f"💬 Ответ администратора:\n{msg.text}")
    await msg.answer("✅ Ответ отправлен")

@dp.message(Command("apanel"))
async def admin_panel(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    await msg.answer("⚙️ Админ-панель", reply_markup=admin_menu())

@dp.message(F.text == "📋 База данных")
async def db_list(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    users = await get_all_users()
    text = "\n".join([f"👤 {u[1]} | ID: {u[0]} | 💰 {u[2]}$" for u in users])
    await msg.answer(text or "Пусто")

@dp.message(F.text == "💸 Выдать деньги")
async def give_money(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    await msg.answer("Введите ID и сумму через пробел:")
    dp.message.register(give_money_input)

async def give_money_input(msg: Message):
    try:
        uid, amount = map(int, msg.text.split())
        await update_balance(uid, amount)
        await msg.answer("✅ Деньги выданы")
    except:
        await msg.answer("❌ Ошибка ввода")

@dp.message(F.text == "🔒 Бан")
async def ban_user(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    await msg.answer("Введите ID для бана:")
    dp.message.register(lambda m: set_ban_and_respond(m, 1))

@dp.message(F.text == "🔓 Разбан")
async def unban_user(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    await msg.answer("Введите ID для разбана:")
    dp.message.register(lambda m: set_ban_and_respond(m, 0))

async def set_ban_and_respond(msg: Message, status):
    try:
        uid = int(msg.text)
        await set_ban(uid, status)
        await msg.answer("✅ Готово")
    except:
        await msg.answer("❌ Ошибка")

@dp.message(F.text == "🔙 Назад")
async def back(msg: Message):
    await msg.answer("⬅️ Возврат в главное меню", reply_markup=main_menu())

# --- MAIN ---
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


