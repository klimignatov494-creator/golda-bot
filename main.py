import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8266056689:AAFhfKvRcG_vZhqbAprUAGHA9tY8jSp-naE"
ADMIN_CHAT_ID = -1003657327895  # <-- ID группы/чата для админа
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- База данных ---
users = {}  # user_id: {"balance":10000, "pending_msg_id": None}

# --- FSM ---
class WithdrawStates(StatesGroup):
    waiting_for_amount = State()

# --- Главное меню ---
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton(text="💰 Кликать голду", callback_data="clicker")],
            [InlineKeyboardButton(text="💸 Вывод голды", callback_data="withdraw")],
            [InlineKeyboardButton(text="ℹ️ Информация о боте", callback_data="info")]
        ]
    )

# --- Назад в меню ---
def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")]
        ]
    )

# --- Кнопки кликера ---
def clicker_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Клик! +250 голды", callback_data="click_gold")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back")]
        ]
    )

# --- Старт ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"balance": 10000, "pending_msg_id": None}
    await message.answer("Добро пожаловать! Выберите действие:", reply_markup=main_menu())

# --- Обработка кнопок ---
@dp.callback_query(lambda c: True)
async def process_menu(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    if user_id not in users:
        users[user_id] = {"balance": 10000, "pending_msg_id": None}

    # Профиль
    if callback_query.data == "profile":
        username = callback_query.from_user.username or callback_query.from_user.full_name
        balance = users[user_id]["balance"]
        await callback_query.message.answer(
            f"👤 Профиль:\nUsername: {username}\nБаланс: {balance} голды",
            reply_markup=back_menu()
        )

    # Кликер
    elif callback_query.data == "clicker":
        balance = users[user_id]["balance"]
        await callback_query.message.answer(
            f"Ваш баланс составляет {balance} голды",
            reply_markup=clicker_buttons()
        )

    elif callback_query.data == "click_gold":
        users[user_id]["balance"] += 250
        balance = users[user_id]["balance"]
        await callback_query.message.edit_text(
            f"Ваш баланс составляет {balance} голды",
            reply_markup=clicker_buttons()
        )

    # Назад в меню
    elif callback_query.data == "back":
        await callback_query.message.answer("Вы вернулись в главное меню:", reply_markup=main_menu())

    # Информация о боте
    elif callback_query.data == "info":
        await callback_query.message.answer(
            "ℹ️ Версия бота: 1.1",
            reply_markup=back_menu()
        )

    # Вывод голды
    elif callback_query.data == "withdraw":
        await callback_query.message.answer("Введите сумму для вывода (мин. 5000):")
        await state.set_state(WithdrawStates.waiting_for_amount)

    # Принятие вывода админом
    elif callback_query.data.startswith("approve_withdraw_"):
        parts = callback_query.data.split("_")
        user_id_to_approve = int(parts[2])
        await bot.send_message(
            user_id_to_approve,
            "✅ Ваш вывод подтвержден, пишите мне за выводом @E23gfgd",
            reply_markup=back_menu()
        )
        await callback_query.message.edit_text(
            callback_query.message.text + "\n✅ Вывод принят"
        )

# --- Ввод суммы для вывода ---
@dp.message(WithdrawStates.waiting_for_amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"balance": 10000, "pending_msg_id": None}

    try:
        amount = int(message.text)

        # Проверка минимальной суммы
        if amount < 5000:
            await message.answer("Минимальная сумма вывода 5000. Введите сумму снова:")
            return

        # Проверка баланса
        if amount > users[user_id]["balance"]:
            await message.answer("❌ У вас недостаточно голды для вывода. Введите корректную сумму:")
            return

        # Списываем баланс только после проверки
        users[user_id]["balance"] -= amount
        total_amount = int(amount * 1.2)  # +20%

        # Отправляем в админ-группу
        approve_button = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Принять вывод",
                    callback_data=f"approve_withdraw_{user_id}"
                )]
            ]
        )
        username = message.from_user.username or message.from_user.full_name
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"Пользователь @{username} хочет вывести {total_amount} голды",
            reply_markup=approve_button
        )

        # Сообщение пользователю
        msg = await message.answer("Ваш вывод на рассмотрении...", reply_markup=back_menu())
        users[user_id]["pending_msg_id"] = msg.message_id

        await state.clear()

    except ValueError:
        await message.answer("Введите корректное число")

# --- Запуск бота ---
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
