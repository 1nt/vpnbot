import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from marzban_backend import MarzbanBackend  # Импортируем ваш класс

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Инициализация MarzbanBackend
marzban = MarzbanBackend()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Я бот для управления пользователями Marzban.')

# Команда /create_user
async def create_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        username = context.args[0]  # Получаем имя пользователя из аргументов команды
        response = marzban.create_user(username)  # Создаем пользователя
        if response:
            await update.message.reply_text(f"Пользователь {username} успешно создан!")
        else:
            await update.message.reply_text("Не удалось создать пользователя.")
    except IndexError:
        await update.message.reply_text("Использование: /create_user <username>")

# Команда /get_user
async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        username = context.args[0]  # Получаем имя пользователя из аргументов команды
        response = marzban.get_user(username)  # Получаем информацию о пользователе
        if response:
            await update.message.reply_text(f"Информация о пользователе {username}: {response}")
        else:
            await update.message.reply_text("Пользователь не найден.")
    except IndexError:
        await update.message.reply_text("Использование: /get_user <username>")

# Команда /disable_user
async def disable_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        username = context.args[0]  # Получаем имя пользователя из аргументов команды
        response = marzban.disable_user(username)  # Отключаем пользователя
        if response:
            await update.message.reply_text(f"Пользователь {username} отключен.")
        else:
            await update.message.reply_text("Не удалось отключить пользователя.")
    except IndexError:
        await update.message.reply_text("Использование: /disable_user <username>")

# Команда /enable_user
async def enable_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        username = context.args[0]  # Получаем имя пользователя из аргументов команды
        response = marzban.enable_user(username)  # Включаем пользователя
        if response:
            await update.message.reply_text(f"Пользователь {username} включен.")
        else:
            await update.message.reply_text("Не удалось включить пользователя.")
    except IndexError:
        await update.message.reply_text("Использование: /enable_user <username>")

# Добавляем новую команду для запроса тестового периода
async def request_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=f"trial_yes_{user.username}"),
            InlineKeyboardButton("Нет", callback_data="trial_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Хотите получить тестовый VPN на 5 дней? + {user.username}?",
        reply_markup=reply_markup
    )

# Обработчик inline кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("trial_yes_"):
        username = query.data.split("_")[2] + "vpn"
        response = marzban.create_user(username)
        if response:
            await query.edit_message_text(f"Тестовый аккаунт создан! Ваш логин: {username}")
        else:
            await query.edit_message_text("Не удалось создать тестовый аккаунт. Попробуйте позже.")
    elif query.data == "trial_no":
        await query.edit_message_text("Вы отказались от тестового периода.")

# Основная функция для запуска бота
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create_user", create_user))
    application.add_handler(CommandHandler("get_user", get_user))
    application.add_handler(CommandHandler("disable_user", disable_user))
    application.add_handler(CommandHandler("enable_user", enable_user))
    application.add_handler(CommandHandler("get_trial", request_trial))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Установка меню команд
    commands = [
        ("start", "Начать работу с ботом"),
        ("create_user", "Создать нового пользователя"),
        ("get_user", "Получить информацию о пользователе"),
        ("disable_user", "Отключить пользователя"),
        ("enable_user", "Включить пользователя"),
        ("get_trial", "Получить бесплатный 5-дневный тест"),
    ]

    # Устанавливаем команды в меню бота
    application.bot.set_my_commands(commands)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()