# --- START OF FILE bot.py ---

import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from marzban_backend import MarzbanBackend  # Импортируем ваш класс
import time
import asyncio
import hashlib
import secrets

# Словари с переводами
RUSSIAN_TEXTS = {
    "start_greeting": "Привет! Я бот для управления VPN.\n\nМы обновили бот. Теперь все логины шифруются, поэтому по любым вопросам используйте контакт внизу или кнопку Проверить оплату\nВыберите действие внизу страницы:\n\n Или просто нажмите - /get_user для получения информации о вашей подписке\nПока сервер в режиме тестирования, потом подписка 200р/мес\n\n",
    "router_text": "🛜 Купить Роутер и забыть про VPN:\n",
    "support_contact": "💬 Техподдержка, оплата и контакт админа: @AP1int",
    "vpn_account_info": "ℹ️ Ваш VPN аккаунт:",
    "login": "👤 Логин:",
    "status": "🚦 Статус:",
    "expires": "⏳ Срок действия до:",
    "subscription_expired": "⚠️ Ваша подписка истекла!",
    "subscription_expiring": "⏳ Ваша подписка скоро истекает!",
    "payment_instructions": "Нажмите 'Оплатить' для продления или 'Я оплатил' после оплаты.",
    "subscription_links_header": "🔗 Ссылки для подключения:\n\n",
    "subscription_link": "▶️ Ссылка на подписку (для приложений):\n",
    "copy_instructions": "Нажмите на ссылку выше 👆 чтобы скопировать ее в буфер обмена и вставьте в приложение в зависимости от вашего устройства.\n\n",
    "install_apps_header": "Установи одно из приложений для подключения VPN на своё устройство:\n",
    "iphone_ipad": "— iPhone и iPad:",
    "android": "— Android:",
    "windows": "— Windows:",
    "macos_m1": "— macOS (проц. M1–M4):",
    "macos_intel": "— macOS (проц. Intel):",
    "androidtv": "— AndroidTV:",
    "linux": "— Linux:",
    "trial_offer": "У вас еще нет VPN аккаунта. Хотите получить пробный доступ на 10 дней?",
    "trial_created": "✅ Тестовый аккаунт",
    "trial_duration": "⏳ Он будет действовать 10 дней.\n\n",
    "payment_option": "💰 Вы можете оплатить подпипу в любое время:\n",
    "payment_link_not_found": "Ссылка на оплату не найдена.\n\n",
    "trial_questions": "💬 Если возникнут вопросы, пишите в группу @seeyoutubefree",
    "trial_declined": "Хорошо, вы отказались от тестового периода. Если передумаете, просто нажмите кнопку снова.",
    "account_already_exists": "У вас уже есть активный VPN аккаунт.\nИспользуйте команду /get_user или кнопку 'Мой VPN' для получения информации о нем.",
    "account_expired": "⚠️ Срок действия вашего аккаунта истек!\n\n",
    "payment_for_renewal": "Для продления доступа, пожалуйста, оплатите подписку:\n💳",
    "payment_confirmation": "После оплаты нажмите кнопку 'Я оплатил' (если доступна).",
    "payment_sent": "✅ Ваше подтверждение отправлено администратору.\nОжидайте проверки и активации/продления аккаунта.",
    "payment_notification": "💰 Пользователь",
    "payment_time": "⏰ Время:",
    "payment_check_request": "Пожалуйста, проверьте оплату и активируйте/продлите аккаунт:",
    "server_restart": "⏳ Начинаю перезагрузку сервера tf2-server (docker restart)...",
    "server_restarted": "✅ Сервер tf2-server успешно перезагружен!",
    "server_restart_error": "❌ Ошибка при перезагрузке сервера tf2-server:\n",
    "docker_not_found": "❌ Ошибка: команда 'docker' не найдена.",
    "restart_error": "❌ Произошла непредвиденная ошибка при перезагрузке сервера.",
    "no_permission": "❌ У вас нет прав для выполнения этой операции.",
    "user_not_found": "❌ Ошибка: не удалось определить пользователя.",
    "account_error": "❌ Произошла ошибка при получении информации о вашем аккаунте.\nПожалуйста, попробуйте позже или обратитесь в поддержку.",
    "trial_error": "❌ Произошла ошибка при обработке вашего запроса.\nПожалуйста, попробуйте позже или обратитесь в поддержку.",
    "trial_creation_error": "❌ Не удалось создать тестовый аккаунт. Ошибка API:",
    "trial_server_error": "❌ Не удалось создать тестовый аккаунт. Произошла ошибка на сервере. Попробуйте позже или обратитесь в поддержку.",
    "trial_unexpected_error": "❌ Произошла непредвиденная ошибка при создании аккаунта.\nПожалуйста, попробуйте позже или обратитесь в поддержку.",
    "trial_already_exists": "❌ Не удалось создать аккаунт: пользователь",
    "already_exists": "уже существует.",
    "try_later": "Попробуйте позже или обратитесь в поддержку.",
    "account_created_no_links": "✅ Аккаунт",
    "created_but_no_links": "создан, но не удалось получить ссылки для подключения.\nПожалуйста, попробуйте /get_user позже или обратитесь в поддержку.",
    "config_error": "❌ Ошибка конфигурации: не удалось уведомить администратора.\nПожалуйста, обратитесь в поддержку.",
    "admin_notification_error": "❌ Произошла ошибка при отправке уведомления администратору.\nПожалуйста, обратитесь в поддержку.",
    "trial_creating": "⏳ Создаю для вас пробный аккаунт",
    "trial_processing": "Запрос уже обрабатывается...",
    "menu_my_vpn": "📱 Мой VPN",
    "menu_get_trial": "🎁 Получить пробный период",
    "menu_restart_server": "🔄 Перезагрузить сервер",
    "button_pay": "💳 Оплатить",
    "button_payment_confirmed": "✅ Проверка оплаты",
    "button_trial_yes": "✅ Да, хочу!",
    "button_trial_no": "❌ Нет, спасибо",
    "button_payment_confirmed_text": "✅ Я оплатил",
    "commands_start": "🚀 Главное меню",
    "commands_get_user": "📱 Мой VPN",
    "commands_get_trial": "🎁 Получить пробный период"
}

ENGLISH_TEXTS = {
    "start_greeting": "Hello! I'm a VPN management bot.\n\nWe have updated the bot. All logins are now encrypted, so for any questions, use the contact below or the Check payment button.\nChoose an action below:\n\nFor example - /get_user to get information about your subscription\nWhile the server is in testing mode, then subscription 200r/month\n\n",
    "router_text": "🛜 Buy a Router and forget about VPN:\n",
    "support_contact": "💬 Technical support, payment and admin contact: @AP1int",
    "vpn_account_info": "ℹ️ Your VPN account:",
    "login": "👤 Login:",
    "status": "🚦 Status:",
    "expires": "⏳ Expires:",
    "subscription_expired": "⚠️ Your subscription has expired!",
    "subscription_expiring": "⏳ Your subscription expires soon!",
    "payment_instructions": "Click 'Pay' to renew or 'I paid' after payment.",
    "subscription_links_header": "🔗 Connection links:\n\n",
    "subscription_link": "▶️ Subscription link (for applications):\n",
    "copy_instructions": "Click the link above 👆 to copy it to clipboard and paste it into the application depending on your device.\n\n",
    "install_apps_header": "Install one of the VPN applications on your device:\n",
    "iphone_ipad": "— iPhone and iPad:",
    "android": "— Android:",
    "windows": "— Windows:",
    "macos_m1": "— macOS (M1-M4 proc.):",
    "macos_intel": "— macOS (Intel proc.):",
    "androidtv": "— AndroidTV:",
    "linux": "— Linux:",
    "trial_offer": "You don't have a VPN account yet. Want to get a 10-day trial access?",
    "trial_created": "✅ Trial account",
    "trial_duration": "⏳ It will be valid for 10 days.\n\n",
    "payment_option": "💰 You can pay for subscription at any time:\n",
    "payment_link_not_found": "Payment link not found.\n\n",
    "trial_questions": "💬 If you have questions, write to the group @seeyoutubefree",
    "trial_declined": "Okay, you declined the trial period. If you change your mind, just click the button again.",
    "account_already_exists": "You already have an active VPN account.\nUse the /get_user command or 'My VPN' button to get information about it.",
    "account_expired": "⚠️ Your account has expired!\n\n",
    "payment_for_renewal": "To renew access, please pay for the subscription:\n💳",
    "payment_confirmation": "After payment, click the 'I paid' button (if available).",
    "payment_sent": "✅ Your confirmation has been sent to the administrator.\nWait for verification and activation/renewal of the account.",
    "payment_notification": "💰 User",
    "payment_time": "⏰ Time:",
    "payment_check_request": "Please check the payment and activate/renew the account:",
    "server_restart": "⏳ Starting server tf2-server restart (docker restart)...",
    "server_restarted": "✅ Server tf2-server successfully restarted!",
    "server_restart_error": "❌ Error restarting server tf2-server:\n",
    "docker_not_found": "❌ Error: 'docker' command not found.",
    "restart_error": "❌ An unexpected error occurred while restarting the server.",
    "no_permission": "❌ You don't have permission to perform this operation.",
    "user_not_found": "❌ Error: Could not determine user.",
    "account_error": "❌ An error occurred while getting information about your account.\nPlease try again later or contact support.",
    "trial_error": "❌ An error occurred while processing your request.\nPlease try again later or contact support.",
    "trial_creation_error": "❌ Failed to create trial account. API error:",
    "trial_server_error": "❌ Failed to create trial account. Server error occurred. Try again later or contact support.",
    "trial_unexpected_error": "❌ An unexpected error occurred while creating the account.\nPlease try again later or contact support.",
    "trial_already_exists": "❌ Failed to create account: user",
    "already_exists": "already exists.",
    "try_later": "Try again later or contact support.",
    "account_created_no_links": "✅ Account",
    "created_but_no_links": "created but failed to get connection links.\nPlease try /get_user later or contact support.",
    "config_error": "❌ Configuration error: Could not notify administrator.\nPlease contact support.",
    "admin_notification_error": "❌ An error occurred while sending notification to administrator.\nPlease contact support.",
    "trial_creating": "⏳ Creating trial account for you",
    "trial_processing": "Request is already being processed...",
    "menu_my_vpn": "📱 My VPN",
    "menu_get_trial": "🎁 Get trial period",
    "menu_restart_server": "🔄 Restart server",
    "button_pay": "💳 Pay",
    "button_payment_confirmed": "✅ Payment verification",
    "button_trial_yes": "✅ Yes, I want!",
    "button_trial_no": "❌ No, thanks",
    "button_payment_confirmed_text": "✅ I paid",
    "commands_start": "🚀 Main menu",
    "commands_get_user": "📱 My VPN",
    "commands_get_trial": "🎁 Get trial period"
}

# Функция для получения текста на нужном языке
def get_text(language_code: str, key: str) -> str:
    """
    Возвращает текст на нужном языке
    language_code: код языка пользователя (например, 'ru', 'en')
    key: ключ для получения текста
    returns: текст на нужном языке или английский по умолчанию
    """
    logger.debug(f"get_text вызван с language_code='{language_code}', key='{key}'")
    
    if language_code and language_code.startswith('ru'):
        result = RUSSIAN_TEXTS.get(key, ENGLISH_TEXTS.get(key, key))
        logger.debug(f"Выбран русский текст для '{key}': {result[:30]}...")
        return result
    else:
        result = ENGLISH_TEXTS.get(key, key)
        logger.debug(f"Выбран английский текст для '{key}': {result[:30]}...")
        return result

# Настройка логирования с более детальным форматом
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.critical("TELEGRAM_BOT_TOKEN не найден в .env файле!")
    exit("Ошибка: TELEGRAM_BOT_TOKEN не установлен.")

# Получаем секрет для хеширования
SECRET = os.getenv("SECRET")
if not SECRET:
    logger.critical("SECRET не найден в .env файле!")
    exit("Ошибка: SECRET не установлен.")


# Получаем список операторов из .env
OPERATORS = os.getenv("OPERATORS", "").split(",")
OPERATORS = [op.strip() for op in OPERATORS if op.strip()]  # Убираем пустые значения и пробелы
logger.info(f"Загружены операторы из .env: {OPERATORS}")

# Функция для генерации хешированного имени пользователя
def generate_marzban_username(user_id: int) -> str:
    """
    Генерирует хешированное имя пользователя из ID Telegram с солью SECRET
    user_id: ID пользователя Telegram
    returns: 5 символов из A-Z a-z 0-9
    """
    logger.debug(f"generate_marzban_username вызван с user_id={user_id}")
    
    # Создаем строку для хеширования: ID + SECRET
    data_to_hash = f"{user_id}{SECRET}"
    
    # Создаем SHA-256 хеш
    hash_object = hashlib.sha256(data_to_hash.encode())
    hash_hex = hash_object.hexdigest()
    
    # Берем первые 10 символов хеша для большей случайности
    hash_part = hash_hex[:10]
    
    # Создаем маппинг для преобразования в нужные символы
    # 0-9 -> 0-9, a-f -> a-z, остальное -> A-Z
    char_map = {}
    for i in range(10):
        char_map[chr(ord('0') + i)] = chr(ord('0') + i)  # 0-9
    for i in range(6):
        char_map[chr(ord('a') + i)] = chr(ord('a') + i)  # a-f -> a-z
    for i in range(6, 26):
        char_map[chr(ord('a') + i)] = chr(ord('A') + i)  # g-z -> A-Z
    
    # Преобразуем хеш в нужные символы
    result = ""
    for char in hash_part:
        if char in char_map:
            result += char_map[char]
        else:
            # Если символ не в маппинге, используем его как есть
            result += char
    
    # Берем первые 5 символов
    final_result = result[:5]
    logger.debug(f"Сгенерировано имя пользователя: '{final_result}' из хеша '{hash_part}'")
    return final_result

# Инициализация MarzbanBackend
try:
    marzban = MarzbanBackend()
    logger.info("MarzbanBackend успешно инициализирован.")
except Exception as e:
    logger.critical(f"Не удалось инициализировать MarzbanBackend: {e}", exc_info=True)
    exit(f"Критическая ошибка при инициализации MarzbanBackend: {e}")


# Функция для проверки оператора
def is_operator(username: str) -> bool:
    # Логируем только если DEBUG уровень включен, чтобы не спамить
    # logger.debug(f"Проверка, является ли пользователь '{username}' оператором. Список операторов: {OPERATORS}")
    result = username in OPERATORS
    logger.debug(f"Проверка оператора '{username}': {result} (список операторов: {OPERATORS})")
    return result

# Общая функция для форматирования ссылок подписки
def format_subscription_links(links: dict, language_code: str = None) -> str:
    """
    Форматирует ссылки подписки: сначала ссылка на подписку, затем список приложений с кликабельными ссылками
    links: словарь с ссылками подписки
    language_code: код языка пользователя
    returns: отформатированный текст со ссылками
    """
    logger.debug(f"format_subscription_links вызван с language_code='{language_code}'")
    logger.debug(f"Тип language_code: {type(language_code)}, значение: '{language_code}'")
    
    links_text = ""
    if links.get('subuser_url'):
        links_text += (
            f"{get_text(language_code, 'subscription_link')}"
            f"`{links['subuser_url']}`\n"
            f"{get_text(language_code, 'copy_instructions')}"
        )
    links_text += (
        f"{get_text(language_code, 'install_apps_header')}"
        f"{get_text(language_code, 'iphone_ipad')} "
        "[Streisand](https://apps.apple.com/app/id6450534064), "
        "[v2RayTun](https://apps.apple.com/us/app/v2raytun/id6476628951?platform=iphone)\n"
        f"{get_text(language_code, 'android')} "
        "[Happ](https://play.google.com/store/apps/details?id=com.happproxy), "
        "[v2RayTun](https://play.google.com/store/apps/details?id=com.v2raytun.android&hl=ru), "
        "[Hiddify](https://play.google.com/store/apps/details?id=app.hiddify.com)\n"
        "[Инструкция для приложения Happ](https://telegra.ph/Instrukciya-Android-08-11)\n"
        f"{get_text(language_code, 'windows')} "
        "[Hiddify](https://apps.microsoft.com/detail/9PDFNL3QV2S5?hl=neutral&gl=RU&ocid=pdpshare), "
        "[Nekoray (NekoBox)](https://github.com/MatsuriDayo/nekoray/releases/download/4.0.1/nekoray-4.0.1-2024-12-12-windows64.zip)\n"
        f"{get_text(language_code, 'macos_m1')} "
        "[Streisand](https://apps.apple.com/app/id6450534064), "
        "[v2RayTun](https://apps.apple.com/us/app/v2raytun/id6476628951?platform=mac)\n"
        f"{get_text(language_code, 'macos_intel')} "
        "[v2RayTun](https://apps.apple.com/us/app/v2raytun/id6476628951?platform=mac), "
        "[V2Box](https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690)\n"
        f"{get_text(language_code, 'androidtv')} "
        "[Hiddify](https://play.google.com/store/apps/details?id=app.hiddify.com), "
        "[Happ](https://play.google.com/store/apps/details?id=com.happproxy), "
        "[v2RayTun](https://play.google.com/store/apps/details?id=com.v2raytun.android&hl=ru)\n"
        f"{get_text(language_code, 'linux')} "
        "[Hiddify](https://github.com/hiddify/hiddify-app/releases/latest/download/Hiddify-Linux-x64.AppImage)\n"
    )
    
    logger.debug(f"Результат format_subscription_links для языка '{language_code}': {links_text[:100]}...")
    return links_text

# Обновляем функцию start с добавлением кнопок меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        logger.warning("Получен /start от пользователя без effective_user.")
        # Можно отправить сообщение об ошибке или просто ничего не делать
        return

    current_user = update.effective_user.username or str(update.effective_user.id)
    language_code = update.effective_user.language_code
    logger.info(f"Команда /start от пользователя: {current_user} (язык: {language_code})")
    logger.info(f"Тип language_code: {type(language_code)}, значение: '{language_code}'")
    logger.info(f"Проверка is_operator: {is_operator(current_user) if current_user else False}")

    keyboard = [
        [InlineKeyboardButton(get_text(language_code, "menu_my_vpn"), callback_data="menu_get_user")],
        [InlineKeyboardButton(get_text(language_code, "menu_get_trial"), callback_data="menu_get_trial")],
    ]

    if update.effective_user.username and is_operator(update.effective_user.username):
        logger.info(f"Пользователь {current_user} является оператором, добавляем кнопку перезагрузки")
        keyboard.append([InlineKeyboardButton(get_text(language_code, "menu_restart_server"), callback_data="restart_server")])
    # else:
        # logger.debug(f"Пользователь {current_user} не оператор, пропускаем кнопку перезагрузки")

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем текст с роутером
    router_text = ""
    if marzban.router_url:
        router_text = f"{get_text(language_code, 'router_text')}{marzban.router_url}\n\n"
    else:
        router_text = f"{get_text(language_code, 'router_text')}https://ozon.ru/product/2288765942\n\n"
    
    # Логируем тексты для отладки
    start_greeting = get_text(language_code, 'start_greeting')
    router_text_final = router_text
    support_contact = get_text(language_code, 'support_contact')
    logger.info(f"Выбранные тексты для языка '{language_code}':")
    logger.info(f"start_greeting: {start_greeting[:50]}...")
    logger.info(f"router_text: {router_text_final[:50]}...")
    logger.info(f"support_contact: {support_contact[:50]}...")
    
    await update.message.reply_text(
        f"{start_greeting}"
        f"{router_text_final}"
        f"{support_contact}",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

# Общая функция для получения информации о пользователе VPN
async def get_user_vpn_info(user_id: int, username: str = None, message_func=None, language_code: str = None) -> None:
    """
    Общая функция для получения информации о VPN пользователе
    user_id: ID пользователя Telegram
    username: username пользователя Telegram (может быть None)
    message_func: функция для отправки сообщения (update.message.reply_text или query.edit_message_text)
    language_code: код языка пользователя
    """
    # Определяем идентификатор пользователя
    user_identifier = username or str(user_id)
    marzban_username = generate_marzban_username(user_id)
    
    logger.info(f"Получение VPN информации для '{user_identifier}' (Marzban: '{marzban_username}', язык: '{language_code}')")
    logger.info(f"Тип language_code: {type(language_code)}, значение: '{language_code}'")

    try:
        logger.info(f"Вызов marzban.get_user для '{marzban_username}'")
        response = marzban.get_user(marzban_username)
        logger.info(f"Ответ от marzban.get_user для '{marzban_username}': type={type(response)}, is_dict={isinstance(response, dict)}")
        if isinstance(response, dict):
             logger.debug(f"Содержимое ответа (dict keys): {response.keys()}")
        elif response is not None:
             logger.warning(f"Неожиданный тип ответа: {response}")

        if response and isinstance(response, dict): # Убедимся, что это словарь и он не пустой
            status = response.get("status", "неизвестно")
            expire = response.get("expire", 0)
            expire_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire)) if expire else "не установлено"
            current_time = time.time()

            info_text = f"{get_text(language_code, 'vpn_account_info')}\n"
            info_text += f"{get_text(language_code, 'login')} `{marzban_username}`\n" # Используем Markdown для моноширинного шрифта
            info_text += f"{get_text(language_code, 'status')} {status}\n"
            info_text += f"{get_text(language_code, 'expires')} {expire_str}\n\n"

            if 'subscription_links' in response and response['subscription_links']:
                links = response['subscription_links']
                info_text += format_subscription_links(links, language_code)

                # Проверка срока действия для кнопки оплаты
                payment_url = links.get('payment_url')
                # Условие: (истек ИЛИ истекает в ближайшие 29 дней) И есть ссылка на оплату
                if payment_url and expire < (current_time + 29 * 86400):
                    keyboard = [
                        [InlineKeyboardButton(get_text(language_code, "button_pay"), url=payment_url)],
                        [InlineKeyboardButton(get_text(language_code, "button_payment_confirmed"), callback_data=f"payment_confirmed_{user_identifier}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    if expire < current_time:
                        info_text += f"{get_text(language_code, 'subscription_expired')}\n"
                    else:
                         info_text += f"{get_text(language_code, 'subscription_expiring')}\n"
                    info_text += f"{get_text(language_code, 'payment_instructions')}\n"
                    await message_func(info_text, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=True)
                else:
                    await message_func(info_text, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                 logger.warning(f"Отсутствуют 'subscription_links' в ответе для пользователя '{marzban_username}'")
                 await message_func(info_text, parse_mode='Markdown', disable_web_page_preview=True) # Отправляем текст без ссылок

        else:
            # Пользователь не найден ИЛИ Marzban вернул что-то неожиданное (None или не словарь)
            logger.warning(f"Пользователь Marzban '{marzban_username}' не найден или получен некорректный ответ: {response}")
            # Предлагаем триал через общую функцию
            await request_trial_common(user_id, username, message_func, language_code)

    except Exception as e:
        # --- Логирование ошибки ---
        logger.error(f"Ошибка при выполнении get_user_vpn_info для Marzban user '{marzban_username}': {e}", exc_info=True)
        await message_func(
            f"{get_text(language_code, 'account_error')}",
            disable_web_page_preview=True
        )

# Команда /get_user
async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        logger.warning("Получен /get_user от пользователя без effective_user.")
        await update.message.reply_text(
            "❌ Ошибка: не удалось определить пользователя.",
            disable_web_page_preview=True
        )
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    language_code = update.effective_user.language_code
    
    logger.info(f"Команда /get_user от пользователя: {username or user_id} (язык: {language_code})")
    logger.info(f"Тип language_code: {type(language_code)}, значение: '{language_code}'")
    
    await get_user_vpn_info(user_id, username, update.message.reply_text, language_code)

# Общая функция для запроса тестового периода
async def request_trial_common(user_id: int, username: str = None, message_func=None, language_code: str = None) -> None:
    """
    Общая функция для запроса тестового периода
    user_id: ID пользователя Telegram
    username: username пользователя Telegram (может быть None)
    message_func: функция для отправки сообщения
    language_code: код языка пользователя
    """
    user_identifier = username or str(user_id)
    marzban_username = generate_marzban_username(user_id)
    logger.info(f"Запрос триала от '{user_identifier}' (проверяем существование '{marzban_username}', язык: '{language_code}')")
    logger.info(f"Тип language_code: {type(language_code)}, значение: '{language_code}'")

    try:
        logger.info(f"[Trial Check] Вызов marzban.get_user для '{marzban_username}'")
        response = marzban.get_user(marzban_username)
        logger.info(f"[Trial Check] Ответ от marzban.get_user для '{marzban_username}': type={type(response)}, is_dict={isinstance(response, dict)}")

        if response and isinstance(response, dict):
            # Пользователь уже существует
            expire = response.get("expire", 0)
            current_time = time.time()
            logger.info(f"Пользователь '{marzban_username}' уже существует. Expire: {expire}, Current: {current_time}")

            if expire and expire < current_time:
                # Аккаунт просрочен
                logger.info(f"Аккаунт '{marzban_username}' просрочен.")
                payment_url = response.get('subscription_links', {}).get('payment_url')
                keyboard_list = []
                text = f"{get_text(language_code, 'account_expired')}\n\n"
                if payment_url:
                     text += f"{get_text(language_code, 'payment_for_renewal')} {payment_url}\n\n"
                     keyboard_list.append([InlineKeyboardButton(get_text(language_code, "button_payment_confirmed_text"), callback_data=f"payment_confirmed_{user_identifier}")])
                else:
                     text += f"{get_text(language_code, 'payment_link_not_found')}\n"

                text += f"{get_text(language_code, 'payment_confirmation')}"
                reply_markup = InlineKeyboardMarkup(keyboard_list) if keyboard_list else None
                await message_func(text, reply_markup=reply_markup, disable_web_page_preview=True)
            else:
                # Аккаунт активен
                logger.info(f"Аккаунт '{marzban_username}' активен.")
                await message_func(
                    get_text(language_code, "account_already_exists"),
                    disable_web_page_preview=True
                )
        else:
            # Аккаунт не существует или ошибка получения, предлагаем trial
            logger.info(f"Аккаунт '{marzban_username}' не найден или ошибка получения. Предлагаем триал.")
            keyboard = [
                [
                    InlineKeyboardButton(get_text(language_code, "button_trial_yes"), callback_data=f"trial_yes_{user_identifier}"),
                    InlineKeyboardButton(get_text(language_code, "button_trial_no"), callback_data="trial_no"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message_func(
                get_text(language_code, "trial_offer"),
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )

    except Exception as e:
        logger.error(f"Ошибка при проверке/предложении триала для '{user_identifier}': {e}", exc_info=True)
        await message_func(
            f"{get_text(language_code, 'trial_error')}",
            disable_web_page_preview=True
        )

# Функция для запроса тестового периода (вызывается из /get_user или кнопки)
async def request_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Сообщение, которое будет отправлено или отредактировано
    message_func = update.message.reply_text if update.message else update.callback_query.edit_message_text

    if not update.effective_user:
        logger.warning("Пользователь без effective_user попытался запросить триал.")
        await message_func(
            "❌ Ошибка: не удалось определить пользователя.",
            disable_web_page_preview=True
        )
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    language_code = update.effective_user.language_code
    
    logger.info(f"Команда /get_trial от пользователя: {username or user_id} (язык: {language_code})")
    logger.info(f"Тип language_code: {type(language_code)}, значение: '{language_code}'")
    
    await request_trial_common(user_id, username, message_func, language_code)

# Обработчик кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        logger.warning("Получен пустой callback_query.")
        return
    await query.answer() # Отвечаем на коллбэк, чтобы убрать часики у кнопки

    # --- Логирование нажатия кнопки ---
    user = update.effective_user
    if not user:
        logger.warning("Получен callback_query от пользователя без effective_user.")
        await query.edit_message_text("❌ Ошибка: не удалось определить пользователя.", disable_web_page_preview=True)
        return
        
    user_id = user.id
    username_tg = user.username
    user_identifier = username_tg or str(user_id)
    language_code = user.language_code
    logger.info(f"Нажата кнопка '{query.data}' пользователем {user_identifier} (ID: {user_id}, язык: {language_code})")
    logger.info(f"Тип language_code: {type(language_code)}, значение: '{language_code}'")
    logger.info(f"Проверка is_operator: {is_operator(user_identifier) if username_tg else False}")
    # ---

    # ==================
    #  Перезагрузка сервера (Только для операторов)
    # ==================
    if query.data == "restart_server":
        if not username_tg or not is_operator(username_tg):
            logger.warning(f"Неавторизованная попытка перезагрузки сервера от {user_identifier}")
            await query.edit_message_text(get_text(language_code, "no_permission"), disable_web_page_preview=True)
            return

        await query.edit_message_text(get_text(language_code, "server_restart"), disable_web_page_preview=True)
        try:
            # Запускаем команду перезагрузки сервера
            logger.info(f"Оператор {user_identifier} инициировал перезагрузку контейнера 'tf2-server'")
            process = await asyncio.create_subprocess_exec(
                '/usr/bin/docker', 'restart', 'tf2-server', # Убедитесь, что имя контейнера верное
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate() # Ждем завершения команды

            if process.returncode == 0:
                logger.info("Команда 'docker restart tf2-server' успешно выполнена.")
                await query.edit_message_text(get_text(language_code, "server_restarted"), disable_web_page_preview=True)
                # Можно добавить небольшую паузу перед тем, как бот снова будет активно им пользоваться
                # await asyncio.sleep(5)
            else:
                error_msg = stderr.decode().strip() if stderr else "Неизвестная ошибка Docker"
                logger.error(f"Ошибка при перезагрузке сервера tf2-server. Код: {process.returncode}. Ошибка: {error_msg}")
                await query.edit_message_text(f"{get_text(language_code, 'server_restart_error')}`{error_msg}`", parse_mode='Markdown', disable_web_page_preview=True)

        except FileNotFoundError:
             logger.error("Ошибка перезагрузки: команда 'docker' не найдена по пути /usr/bin/docker")
             await query.edit_message_text(get_text(language_code, "docker_not_found"), disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при перезагрузке сервера: {e}", exc_info=True)
            await query.edit_message_text(get_text(language_code, "restart_error"), disable_web_page_preview=True)

    # ==================
    #  Подтверждение оплаты
    # ==================
    elif query.data.startswith("payment_confirmed_"):
        confirmed_user_identifier = query.data.split("_")[2] # Идентификатор пользователя, нажавшего кнопку
        current_time_str = time.strftime('%Y-%m-%d %H:%M:%S')
        marzban_username = generate_marzban_username(user_id)

        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if not admin_chat_id:
            logger.error("ADMIN_CHAT_ID не установлен в .env! Не могу уведомить администратора.")
            await query.edit_message_text(
                get_text(language_code, "config_error"),
                disable_web_page_preview=True
            )
            return

        try:
            admin_chat_id_int = int(admin_chat_id)
            message_text = (f"{get_text(language_code, 'payment_notification')} {user_identifier} (ID: `{user_id}`) "
                            f"нажал кнопку 'Я оплатил'.\n"
                            f"{get_text(language_code, 'payment_time')} {current_time_str}\n"
                            f"{get_text(language_code, 'payment_check_request')} `{marzban_username}`")

            await context.bot.send_message(
                chat_id=admin_chat_id_int,
                text=message_text,
                parse_mode='Markdown'
            )
            logger.info(f"Уведомление об оплате от {user_identifier} успешно отправлено администратору ({admin_chat_id_int}).")
            await query.edit_message_text(
                get_text(language_code, "payment_sent"),
                disable_web_page_preview=True
            )

        except ValueError:
            logger.error(f"Неверный формат ADMIN_CHAT_ID: '{admin_chat_id}'. Должно быть число.")
            await query.edit_message_text(
                get_text(language_code, "config_error"),
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администратору ({admin_chat_id}): {e}", exc_info=True)
            await query.edit_message_text(
                get_text(language_code, "admin_notification_error"),
                disable_web_page_preview=True
            )

    # ==================
    #  Меню: Мой VPN
    # ==================
    elif query.data == "menu_get_user":
        await get_user_vpn_info(user_id, username_tg, query.edit_message_text, language_code)

    # ==================
    #  Меню: Получить триал
    # ==================
    elif query.data == "menu_get_trial":
        await request_trial_common(user_id, username_tg, query.edit_message_text, language_code)

    # ==================
    #  Согласие на триал
    # ==================
    elif query.data.startswith("trial_yes_"):
        trial_user_identifier = query.data.split("_")[2] # Идентификатор пользователя из callback_data
        marzban_username = generate_marzban_username(user_id)
        logger.info(f"Пользователь {user_identifier} согласился на триал. Создаем аккаунт '{marzban_username}'")

        # Небольшая проверка, вдруг пользователь нажал дважды быстро
        if context.user_data.get(f'trial_creating_{trial_user_identifier}', False):
            logger.warning(f"Повторная попытка создания триала для {trial_user_identifier} проигнорирована.")
            await query.answer(get_text(language_code, "trial_processing"), show_alert=True)
            return
        context.user_data[f'trial_creating_{trial_user_identifier}'] = True # Флаг начала создания

        try:
            await query.edit_message_text(f"{get_text(language_code, 'trial_creating')} `{marzban_username}`...", parse_mode='Markdown', disable_web_page_preview=True)
            logger.info(f"Вызов marzban.create_user для '{marzban_username}' (trial=True)")
            response = marzban.create_user(marzban_username, is_trial=True)
            logger.info(f"Ответ от marzban.create_user для '{marzban_username}': {response}")

            if response and isinstance(response, dict) and response.get("username") == marzban_username:
                # Успешно создали, теперь получаем ссылки
                logger.info(f"Аккаунт '{marzban_username}' успешно создан. Получаем ссылки.")
                # Используем subscription_url из ответа создания пользователя
                sub_url = response.get("subscription_url")
                if sub_url:
                     subscription_links = marzban.get_subscription_links(marzban_username, sub_url)

                     reply_text = (
                         f"{get_text(language_code, 'trial_created')} `{marzban_username}` создан!\n\n"
                         f"{get_text(language_code, 'trial_duration')}"
                         f"{format_subscription_links(subscription_links, language_code)}\n\n"
                     )
                     payment_url = subscription_links.get('payment_url')
                     if payment_url:
                         reply_text += f"{get_text(language_code, 'payment_option')}{payment_url}\n\n"
                     else:
                          reply_text += f"{get_text(language_code, 'payment_link_not_found')}"

                     reply_text += f"{get_text(language_code, 'trial_questions')}"
                     await query.edit_message_text(reply_text, parse_mode='Markdown', disable_web_page_preview=True)
                else:
                     logger.error(f"Не удалось получить subscription_url после создания пользователя '{marzban_username}'. Ответ: {response}")
                     await query.edit_message_text(
                         f"{get_text(language_code, 'account_created_no_links')} `{marzban_username}` {get_text(language_code, 'created_but_no_links')}", parse_mode='Markdown', disable_web_page_preview=True
                     )

            elif response and isinstance(response, dict): # Если ответ есть, но не то, что ожидали
                error_detail = response.get("detail", "Нет деталей")
                logger.error(f"Не удалось создать триал для '{marzban_username}'. Ответ API: {response}")
                if "already exists" in str(error_detail).lower():
                     await query.edit_message_text(f"{get_text(language_code, 'trial_already_exists')} `{marzban_username}` {get_text(language_code, 'already_exists')}", parse_mode='Markdown', disable_web_page_preview=True)
                else:
                     await query.edit_message_text(f"{get_text(language_code, 'trial_creation_error')} {error_detail}. {get_text(language_code, 'try_later')}", disable_web_page_preview=True)
            else: # Если ответ None или не словарь
                 logger.error(f"Не удалось создать триал для '{marzban_username}'. Ответ API был None или некорректный.")
                 await query.edit_message_text(f"{get_text(language_code, 'trial_server_error')}", disable_web_page_preview=True)

        except Exception as e:
            logger.error(f"Ошибка при создании триала для '{marzban_username}': {e}", exc_info=True)
            await query.edit_message_text(
                f"{get_text(language_code, 'trial_unexpected_error')}\n{get_text(language_code, 'try_later')}",
                disable_web_page_preview=True
            )
        finally:
             context.user_data[f'trial_creating_{trial_user_identifier}'] = False # Снимаем флаг

    # ==================
    #  Отказ от триала
    # ==================
    elif query.data == "trial_no":
        await query.edit_message_text(get_text(language_code, "trial_declined"), disable_web_page_preview=True)


# Основная функция
def main() -> None:
    logger.info("Запуск бота...")
    logger.info(f"Переменные окружения:")
    logger.info(f"  TELEGRAM_BOT_TOKEN: {'***' if TELEGRAM_BOT_TOKEN else 'НЕ УСТАНОВЛЕН'}")
    logger.info(f"  SECRET: {'***' if SECRET else 'НЕ УСТАНОВЛЕН'}")
    logger.info(f"  OPERATORS: {OPERATORS}")
    
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        logger.info("Приложение Telegram бота создано.")

        # Регистрация команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("get_user", get_user))
        # Добавляем get_trial как алиас для request_trial (хотя лучше через кнопки)
        application.add_handler(CommandHandler("get_trial", request_trial))

        # Регистрация обработчика кнопок (должен идти после команд, если есть пересечения)
        application.add_handler(CallbackQueryHandler(button_callback))
        logger.info("Обработчики команд и кнопок добавлены.")

        # Установка меню команд для удобства пользователей
        commands = [
            ("start", get_text("en", "commands_start")),
            ("get_user", get_text("en", "commands_get_user")),
            ("get_trial", get_text("en", "commands_get_trial")),
        ]
        logger.info(f"Устанавливаем команды меню: {commands}")
        
        # Запускаем установку команд асинхронно в фоне, чтобы не блокировать старт
        # asyncio.create_task(application.bot.set_my_commands(commands))
        # --> Лучше сделать синхронно до запуска, если это возможно в вашей версии PTB
        try:
             loop = asyncio.get_event_loop()
             loop.run_until_complete(application.bot.set_my_commands(commands))
             logger.info("Команды меню успешно установлены.")
        except Exception as e:
             logger.warning(f"Не удалось установить команды меню: {e}")


        # Запуск бота
        logger.info("Запуск обработки обновлений (polling)...")
        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске или работе бота: {e}", exc_info=True)

if __name__ == '__main__':
    main()

# --- END OF FILE bot.py ---