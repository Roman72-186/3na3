import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from dotenv import load_dotenv
import os

# Загрузка переменных из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("No BOT_TOKEN provided in .env file!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранение игр
games = {}  # {игрок_1: {player2: ..., field: [...], turn: "X"}}
waiting_users = []  # Очередь игроков, ожидающих оппонента

# Клавиатуры
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать игру", callback_data="create_game")],
        [InlineKeyboardButton(text="Найти игру", callback_data="find_game")]
    ])

def game_keyboard(field):
    keyboard = []
    for i in range(0, 9, 3):  # Формируем строки клавиатуры
        row = [
            InlineKeyboardButton(
                text=field[j] if field[j] else " ",  # Если клетка пуста, отображаем пробел
                callback_data=f"move_{j}"
            )
            for j in range(i, i + 3)
        ]
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Обработчики
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Добро пожаловать в Крестики-Нолики!", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "create_game")
async def create_game(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in games:
        await callback_query.answer("Вы уже создали игру!")
        return

    waiting_users.append(user_id)
    games[user_id] = {"player2": None, "field": [None] * 9, "turn": "X"}
    await callback_query.answer("Игра создана! Ждите оппонента.")
    await bot.send_message(user_id, "Ожидание второго игрока...")

@dp.callback_query(lambda c: c.data == "find_game")
async def find_game(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in games:
        await callback_query.answer("Вы уже участвуете в игре!")
        return

    if not waiting_users:
        await callback_query.answer("Нет доступных игр. Попробуйте позже.")
        return

    opponent_id = waiting_users.pop(0)
    games[opponent_id]["player2"] = user_id
    games[user_id] = games[opponent_id]  # Ссылки на одну игру

    await callback_query.answer("Вы присоединились к игре!")
    await bot.send_message(opponent_id, "Игрок присоединился к вашей игре!")
    await bot.send_message(opponent_id, "Ваш ход!", reply_markup=game_keyboard(games[opponent_id]["field"]))
    await bot.send_message(user_id, "Ожидайте вашего хода.")

@dp.callback_query(lambda c: c.data.startswith("move_"))
async def make_move(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in games:
        await callback_query.answer("Вы не участвуете в игре!")
        return

    game = games[user_id]
    if user_id != game["player2"] and game["turn"] != "X":
        await callback_query.answer("Не ваш ход!")
        return
    if user_id == game["player2"] and game["turn"] != "O":
        await callback_query.answer("Не ваш ход!")
        return

    move = int(callback_query.data.split("_")[1])
    if game["field"][move]:
        await callback_query.answer("Эта клетка уже занята!")
        return

    game["field"][move] = game["turn"]
    game["turn"] = "O" if game["turn"] == "X" else "X"

    # Проверка на победу
    winner = check_winner(game["field"])
    if winner:
        await bot.send_message(user_id, f"Игра окончена! Победил {winner}")
        await bot.send_message(game["player2"] if user_id == game["player2"] else user_id, f"Игра окончена! Победил {winner}")
        # Удаление игры
        games.pop(game["player2"], None)
        games.pop(user_id, None)
        return

    # Отправка обновленного поля
    await callback_query.answer("Ход сделан!")
    opponent_id = game["player2"] if user_id != game["player2"] else user_id
    await bot.send_message(opponent_id, "Ваш ход!", reply_markup=game_keyboard(game["field"]))

def check_winner(field):
    win_patterns = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for pattern in win_patterns:
        if field[pattern[0]] and field[pattern[0]] == field[pattern[1]] == field[pattern[2]]:
            return field[pattern[0]]
    return None if None in field else "Draw"

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
