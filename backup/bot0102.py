import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from marzban_backend import MarzbanBackend  # Импортируем ваш класс
import time

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
        username = f"{update.effective_user.username}vpn"
        response = marzban.get_user(username)
        
        if response:
            status = response.get("status", "неизвестно")
            expire = response.get("expire", 0)
            expire_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire)) if expire else "не установлено"
            
            info_text = f"Ваш VPN аккаунт:\n"
            info_text += f"Логин: {username}\n"
            info_text += f"Статус: {status}\n"
            info_text += f"Срок действия до: {expire_str}\n\n"
            
            if 'subscription_links' in response:
                info_text += "Ссылки для подключения:\n\n"
                info_text += "📱 V2rayNG:\n"
                info_text += f"{response['subscription_links']['v2rayng']}\n\n"
                info_text += "📱 Streisand:\n"
                info_text += f"{response['subscription_links']['streisand']}"
            
            await update.message.reply_text(info_text)
        else:
            await request_trial(update, context)
            
    except AttributeError:
        await update.message.reply_text(
            "Для использования бота у вас должен быть установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках профиля и попробуйте снова."
        )

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
        "У вас пока нет VPN аккаунта. Хотите получить пробный доступ на 5 дней?",
        reply_markup=reply_markup
    )

# Обработчик inline кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("trial_yes_"):
        username = query.data.split("_")[2] + "vpn"
        response = marzban.create_user(username, is_trial=True)
        if response:
            subscription_links = marzban.get_subscription_links(
                username, 
                response.get("subscription_url", "")
            )
            
            reply_text = f"✅ Тестовый аккаунт создан!\n\n"
            reply_text += "Ссылки для подключения:\n\n"
            reply_text += "📱 V2rayNG:\n"
            reply_text += f"{subscription_links['v2rayng']}\n\n"
            reply_text += "📱 Streisand:\n"
            reply_text += f"{subscription_links['streisand']}"
            
            await query.edit_message_text(reply_text)
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
        ("get_user", "Получить информацию о вашем VPN аккаунте"),
        ("disable_user", "Отключить пользователя"),
        ("enable_user", "Включить пользователя"),
        ("get_trial", "Получить бесплатный 5-дневный тест"),
    ]
    
    # Синхронная установка команд перед запуском
    application.bot.set_my_commands(commands)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()