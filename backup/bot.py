import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from marzban_backend import MarzbanBackend  # Импортируем ваш класс
import time
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Получаем список операторов из .env
OPERATORS = os.getenv("OPERATORS", "").split(",")
OPERATORS = [op.strip() for op in OPERATORS if op.strip()]  # Убираем пустые значения и пробелы
logger.info(f"Loaded operators from env: {OPERATORS}")

# Инициализация MarzbanBackend
marzban = MarzbanBackend()

# Функция для проверки оператора
def is_operator(username: str) -> bool:
    logger.info(f"Checking if user '{username}' is operator. Operators list: {OPERATORS}")
    return username in OPERATORS

# Обновляем функцию start с добавлением кнопок меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("📱 Мой VPN", callback_data="menu_get_user")],
        [InlineKeyboardButton("🎁 Получить пробный период", callback_data="menu_get_trial")],
    ]
    
    # Добавляем кнопку перезагрузки сервера для операторов
    current_user = update.effective_user.username
    logger.info(f"Checking operator status for user: {current_user}")
    
    if current_user and is_operator(current_user):
        logger.info(f"User {current_user} is operator, adding restart button")
        keyboard.append([InlineKeyboardButton("🔄 Перезагрузить сервер", callback_data="restart_server")])
    else:
        logger.info(f"User {current_user} is not operator, skipping restart button")
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Привет! Я бот для управления VPN.\n\n'
        'Выберите действие внизу страницы:\n\n'
        'Например - /get_user для получения информации о вашей подписке\n'
        'Пока сервер в режиме тестирования, потом подписка 200р/мес\n\n'
        '🛜 Купить Роутер и забыть про VPN:\n'
        'https://ozon.ru/product/1902614243\n\n'
        '💬 Техподдержка и обсуждение в группе: @seeyoutubefree',
        reply_markup=reply_markup
    )

# Команда /get_user
async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        username = f"{update.effective_user.username}vpn"
        response = marzban.get_user(username)
        
        if response:
            status = response.get("status", "неизвестно")
            expire = response.get("expire", 0)
            expire_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire)) if expire else "не установлено"
            current_time = time.time()
            
            info_text = f"Ваш VPN аккаунт:\n"
            info_text += f"Логин: {username}\n"
            info_text += f"Статус: {status}\n"
            info_text += f"Срок действия до: {expire_str}\n\n"
            
            if 'subscription_links' in response:
                info_text += "📱 Сылка для подписку VPN:\n"
                info_text += f"{response['subscription_links']['subuser_url']}\n\n"
                info_text += "Ссылки на приложения:\n\n"
                info_text += "📱 V2rayNG:\n"
                info_text += f"{response['subscription_links']['v2rayng']}\n\n"
                info_text += "📱 Streisand:\n"
                info_text += f"{response['subscription_links']['streisand']}\n\n"
                
                # Check if subscription is expired or about to expire (within 24 hours)
                if expire and expire < current_time + 86400:  # 86400 seconds = 24 hours
                    keyboard = [
                        [InlineKeyboardButton("💳 Оплатить", url=response['subscription_links']['payment_url'])],
                        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{update.effective_user.username}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    info_text += "⚠️ Ваша подписка истекает или уже истекла!\n"
                    info_text += "Нажмите 'Оплатить' для продления или 'Я оплатил' после оплаты.\n\n"
                    await update.message.reply_text(info_text, reply_markup=reply_markup)
                else:
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
    try:
        username = f"{update.effective_user.username}vpn"
        response = marzban.get_user(username)
        
        if response and isinstance(response, dict):
            expire = response.get("expire", 0)
            current_time = time.time()
            
            if expire and expire < current_time:
                # Аккаунт просрочен
                keyboard = [
                    [InlineKeyboardButton("Я оплатил", callback_data=f"payment_confirmed_{update.effective_user.username}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "⚠️ Срок действия вашего аккаунта истек!\n\n"
                    "Для продления доступа, пожалуйста, оплатите подписку:\n"
                    f"💳 {response['subscription_links'].get('payment_url', 'URL не доступен')}\n\n"
                    "После оплаты нажмите кнопку 'Я оплатил'",
                    reply_markup=reply_markup
                )
            else:
                # Аккаунт активен
                await update.message.reply_text(
                    "У вас уже есть активный VPN аккаунт.\n"
                    "Используйте команду /get_user для получения информации о нем."
                )
        else:
            # Аккаунт не существует, предлагаем trial
            keyboard = [
                [
                    InlineKeyboardButton("Да", callback_data=f"trial_yes_{update.effective_user.username}"),
                    InlineKeyboardButton("Нет", callback_data="trial_no"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Хотите получить пробный VPN на 5 дней?",
                reply_markup=reply_markup
            )
    except AttributeError:
        await update.message.reply_text(
            "Для использования бота у вас должен быть установлен username в Telegram.\n"
            "Пожалуйста, установите username в настройках профиля и попробуйте снова."
        )

# Обновляем обработчик кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "restart_server":
        # Проверяем, является ли пользователь оператором
        if not update.effective_user.username or not is_operator(update.effective_user.username):
            await query.edit_message_text("❌ У вас нет прав для выполнения этой операции.")
            return
            
        try:
            # Запускаем команду перезагрузки сервера
            process = await asyncio.create_subprocess_exec(
                '/usr/bin/docker', 'restart', 'amazing_curran',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                await query.edit_message_text("✅ Сервер успешно перезагружен!")
            else:
                error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
                await query.edit_message_text(f"❌ Ошибка при перезагрузке сервера:\n{error_msg}")
                
        except Exception as e:
            logger.error(f"Error restarting server: {str(e)}")
            await query.edit_message_text("❌ Произошла ошибка при перезагрузке сервера.")
    
    elif query.data.startswith("payment_confirmed_"):
        username = query.data.split("_")[2]
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get admin chat ID from environment variable
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        
        if not admin_chat_id:
            logger.error("ADMIN_CHAT_ID not set in environment variables")
            await query.edit_message_text(
                "❌ Ошибка: не настроен ADMIN_CHAT_ID. Пожалуйста, обратитесь к администратору."
            )
            return
            
        try:
            # Convert chat_id to integer
            admin_chat_id = int(admin_chat_id)
            
            # Send message to admin using chat ID
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=f"💰 Пользователь @{username} подтвердил оплату\n"
                     f"⏰ Время: {current_time}"
            )
            logger.info(f"Successfully sent admin notification to chat_id: {admin_chat_id}")
            
        except ValueError:
            logger.error(f"Invalid ADMIN_CHAT_ID format: {admin_chat_id}")
            await query.edit_message_text(
                "❌ Ошибка: неверный формат ADMIN_CHAT_ID. Пожалуйста, обратитесь к администратору."
            )
            return
        except Exception as e:
            logger.error(f"Failed to send admin notification: {str(e)}")
            logger.error(f"Admin chat ID: {admin_chat_id}")
            await query.edit_message_text(
                "❌ Ошибка при отправке уведомления администратору.\n"
                "Пожалуйста, обратитесь к администратору."
            )
            return
        
        await query.edit_message_text(
            "✅ Информация об оплате отправлена администратору.\n"
            "Ожидайте подтверждения и активации аккаунта."
        )
    
    if query.data == "menu_get_user":
        # Добавляем логирование
        logger.info(f"Processing menu_get_user for user: {update.effective_user.username}")
        
        # Проверяем наличие username
        if not update.effective_user.username:
            await query.edit_message_text(
                "Для использования бота у вас должен быть установлен username в Telegram.\n"
                "Пожалуйста, установите username в настройках профиля и попробуйте снова."
            )
            return
            
        username = f"{update.effective_user.username}vpn"
        logger.info(f"Attempting to get user info for: {username}")
        
        try:
            response = marzban.get_user(username)
            logger.info(f"Marzban response: {response}")
            
            if response and isinstance(response, dict):
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
                    info_text += f"{response['subscription_links']['streisand']}\n\n"
                    info_text += "📱 Ссылка для оплаты:\n"
                    info_text += f"{response['subscription_links']['payment_url']}\n\n"
                
                await query.edit_message_text(info_text)
            else:
                logger.warning(f"User not found or invalid response: {response}")
                # Если пользователь не найден, предлагаем trial
                keyboard = [
                    [
                        InlineKeyboardButton("Да", callback_data=f"trial_yes_{update.effective_user.username}"),
                        InlineKeyboardButton("Нет", callback_data="trial_no"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "У вас пока нет VPN аккаунта. Хотите получить пробный доступ на 5 дней?",
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error processing menu_get_user: {str(e)}")
            await query.edit_message_text("Произошла ошибка при получении данных. Попробуйте позже.")

    elif query.data == "menu_get_trial":
        keyboard = [
            [
                InlineKeyboardButton("Да", callback_data=f"trial_yes_{update.effective_user.username}"),
                InlineKeyboardButton("Нет", callback_data="trial_no"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Хотите получить пробный VPN на 5 дней?",
            reply_markup=reply_markup
        )
        
    elif query.data.startswith("trial_yes_"):
        username = query.data.split("_")[2] + "vpn"
        response = marzban.create_user(username, is_trial=True)
        if response:
            subscription_links = marzban.get_subscription_links(
                username, 
                response.get("subscription_url", "")
            )
            
            reply_text = (
                f"✅ Тестовый аккаунт создан!\n\n"
                f"🔑 Ваш логин: {username}\n\n"
                f"🔗 Ссылки для скачивания приложений:\n\n"
                f"📱 Android - V2rayNG:\n{subscription_links['v2rayng']}\n\n"
                f"📱 iPhone - Streisand:\n{subscription_links['streisand']}\n\n"
                f"⚠️ Аккаунт действителен 5 дней\n\n"
                f"💳 Ссылка для оплаты:\n{subscription_links['payment_url']}\n\n"
                f"🔗 Ссылка на подписку VPN:\n{subscription_links['subuser_url']}\n\n"
            )
            
            await query.edit_message_text(reply_text)
        else:
            await query.edit_message_text("❌ Не удалось создать тестовый аккаунт. Попробуйте позже.")
    elif query.data == "trial_no":
        await query.edit_message_text("Вы отказались от тестового периода.")

# Обновляем main() с новым набором команд
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get_user", get_user))
    application.add_handler(CommandHandler("get_trial", request_trial))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Установка меню команд
    commands = [
        ("start", "Открыть главное меню"),
        ("get_user", "Получить информацию о вашем VPN"),
        ("get_trial", "Получить пробный период"),
    ]
    
    # Синхронная установка команд перед запуском
    application.bot.set_my_commands(commands)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()