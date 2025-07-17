# --- START OF FILE bot.py ---

import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from marzban_backend import MarzbanBackend  # Импортируем ваш класс
import time
import asyncio

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


# Получаем список операторов из .env
OPERATORS = os.getenv("OPERATORS", "").split(",")
OPERATORS = [op.strip() for op in OPERATORS if op.strip()]  # Убираем пустые значения и пробелы
logger.info(f"Загружены операторы из .env: {OPERATORS}")

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
    return username in OPERATORS

# Общая функция для форматирования ссылок подписки
def format_subscription_links(links: dict) -> str:
    """
    Форматирует ссылки подписки в единый текст
    links: словарь с ссылками подписки
    returns: отформатированный текст со ссылками
    """
    links_text = "🔗 Ссылки для подключения:\n\n"
    
    if links.get('subuser_url'):
        links_text += f"▶️ Ссылка на подписку (для приложений):\n`{links['subuser_url']}`\n\n"
        links_text += f"Скопируйте ссылку в буфер обмена и вставьте в приложение в зависимости от вашего устройства.\n\n"
    
    if links.get('v2rayng'):
        links_text += f"[📱 Android (V2rayNG)]({links['v2rayng']})\n\n"
    if links.get('v2rayng_help'):
        links_text += f"[📱 Помощь по приложению V2rayNG]({links['v2rayng_help']})\n\n"
        
    if links.get('streisand'):
        links_text += f"[📱 iOS (Streisand)]({links['streisand']})\n\n"
    
    return links_text

# Обновляем функцию start с добавлением кнопок меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("📱 Мой VPN", callback_data="menu_get_user")],
        [InlineKeyboardButton("🎁 Получить пробный период", callback_data="menu_get_trial")],
    ]

    if not update.effective_user:
        logger.warning("Получен /start от пользователя без effective_user.")
        # Можно отправить сообщение об ошибке или просто ничего не делать
        return

    current_user = update.effective_user.username or str(update.effective_user.id)
    logger.info(f"Команда /start от пользователя: {current_user}")

    if update.effective_user.username and is_operator(update.effective_user.username):
        logger.info(f"Пользователь {current_user} является оператором, добавляем кнопку перезагрузки")
        keyboard.append([InlineKeyboardButton("🔄 Перезагрузить сервер", callback_data="restart_server")])
    # else:
        # logger.debug(f"Пользователь {current_user} не оператор, пропускаем кнопку перезагрузки")

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем текст с роутером
    router_text = ""
    if marzban.router_url:
        router_text = f'🛜 Купить Роутер и забыть про VPN:\n{marzban.router_url}\n\n'
    else:
        router_text = '🛜 Купить Роутер и забыть про VPN:\nhttps://ozon.ru/product/2288765942\n\n'
    
    await update.message.reply_text(
        'Привет! Я бот для управления VPN.\n\n'
        'Выберите действие внизу страницы:\n\n'
        'Например - /get_user для получения информации о вашей подписке\n'
        'Пока сервер в режиме тестирования, потом подписка 200р/мес\n\n'
        f'{router_text}'
        '💬 Техподдержка, оплата и контакт админа: @AP1int',
        reply_markup=reply_markup
    )

# Общая функция для получения информации о пользователе VPN
async def get_user_vpn_info(user_id: int, username: str = None, message_func=None) -> None:
    """
    Общая функция для получения информации о VPN пользователе
    user_id: ID пользователя Telegram
    username: username пользователя Telegram (может быть None)
    message_func: функция для отправки сообщения (update.message.reply_text или query.edit_message_text)
    """
    # Определяем идентификатор пользователя
    user_identifier = username or str(user_id)
    marzban_username = f"{user_identifier}vpn"
    
    logger.info(f"Получение VPN информации для '{user_identifier}' (Marzban: '{marzban_username}')")

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

            info_text = f"ℹ️ Ваш VPN аккаунт:\n"
            info_text += f"👤 Логин: `{marzban_username}`\n" # Используем Markdown для моноширинного шрифта
            info_text += f"🚦 Статус: {status}\n"
            info_text += f"⏳ Срок действия до: {expire_str}\n\n"

            if 'subscription_links' in response and response['subscription_links']:
                links = response['subscription_links']
                info_text += format_subscription_links(links)

                # Проверка срока действия для кнопки оплаты
                payment_url = links.get('payment_url')
                # Условие: (истек ИЛИ истекает в ближайшие 5 дней) И есть ссылка на оплату
                if payment_url and expire < (current_time + 5 * 86400):
                    keyboard = [
                        [InlineKeyboardButton("💳 Оплатить", url=payment_url)],
                        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{user_identifier}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    if expire < current_time:
                        info_text += "⚠️ Ваша подписка истекла!\n"
                    else:
                         info_text += "⏳ Ваша подписка скоро истекает!\n"
                    info_text += "Нажмите 'Оплатить' для продления или 'Я оплатил' после оплаты.\n"
                    await message_func(info_text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await message_func(info_text, parse_mode='Markdown')
            else:
                 logger.warning(f"Отсутствуют 'subscription_links' в ответе для пользователя '{marzban_username}'")
                 await message_func(info_text, parse_mode='Markdown') # Отправляем текст без ссылок

        else:
            # Пользователь не найден ИЛИ Marzban вернул что-то неожиданное (None или не словарь)
            logger.warning(f"Пользователь Marzban '{marzban_username}' не найден или получен некорректный ответ: {response}")
            # Предлагаем триал через общую функцию
            await request_trial_common(user_id, username, message_func)

    except Exception as e:
        # --- Логирование ошибки ---
        logger.error(f"Ошибка при выполнении get_user_vpn_info для Marzban user '{marzban_username}': {e}", exc_info=True)
        await message_func(
            "❌ Произошла ошибка при получении информации о вашем аккаунте.\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )

# Команда /get_user
async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        logger.warning("Получен /get_user от пользователя без effective_user.")
        await update.message.reply_text(
            "❌ Ошибка: не удалось определить пользователя."
        )
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    
    await get_user_vpn_info(user_id, username, update.message.reply_text)

# Общая функция для запроса тестового периода
async def request_trial_common(user_id: int, username: str = None, message_func=None) -> None:
    """
    Общая функция для запроса тестового периода
    user_id: ID пользователя Telegram
    username: username пользователя Telegram (может быть None)
    message_func: функция для отправки сообщения
    """
    user_identifier = username or str(user_id)
    marzban_username = f"{user_identifier}vpn"
    logger.info(f"Запрос триала от '{user_identifier}' (проверяем существование '{marzban_username}')")

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
                text = "⚠️ Срок действия вашего аккаунта истек!\n\n"
                if payment_url:
                     text += f"Для продления доступа, пожалуйста, оплатите подписку:\n💳 {payment_url}\n\n"
                     keyboard_list.append([InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{user_identifier}")])
                else:
                     text += "Ссылка на оплату не найдена. Обратитесь в поддержку.\n"

                text += "После оплаты нажмите кнопку 'Я оплатил' (если доступна)."
                reply_markup = InlineKeyboardMarkup(keyboard_list) if keyboard_list else None
                await message_func(text, reply_markup=reply_markup)
            else:
                # Аккаунт активен
                logger.info(f"Аккаунт '{marzban_username}' активен.")
                await message_func(
                    "У вас уже есть активный VPN аккаунт.\n"
                    "Используйте команду /get_user или кнопку 'Мой VPN' для получения информации о нем."
                )
        else:
            # Аккаунт не существует или ошибка получения, предлагаем trial
            logger.info(f"Аккаунт '{marzban_username}' не найден или ошибка получения. Предлагаем триал.")
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, хочу!", callback_data=f"trial_yes_{user_identifier}"),
                    InlineKeyboardButton("❌ Нет, спасибо", callback_data="trial_no"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message_func(
                "У вас еще нет VPN аккаунта. Хотите получить пробный доступ на 5 дней?",
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Ошибка при проверке/предложении триала для '{user_identifier}': {e}", exc_info=True)
        await message_func(
            "❌ Произошла ошибка при обработке вашего запроса.\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )

# Функция для запроса тестового периода (вызывается из /get_user или кнопки)
async def request_trial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Сообщение, которое будет отправлено или отредактировано
    message_func = update.message.reply_text if update.message else update.callback_query.edit_message_text

    if not update.effective_user:
        logger.warning("Пользователь без effective_user попытался запросить триал.")
        await message_func(
            "❌ Ошибка: не удалось определить пользователя."
        )
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    
    await request_trial_common(user_id, username, message_func)

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
        await query.edit_message_text("❌ Ошибка: не удалось определить пользователя.")
        return
        
    user_id = user.id
    username_tg = user.username
    user_identifier = username_tg or str(user_id)
    logger.info(f"Нажата кнопка '{query.data}' пользователем {user_identifier} (ID: {user_id})")
    # ---

    # ==================
    #  Перезагрузка сервера (Только для операторов)
    # ==================
    if query.data == "restart_server":
        if not username_tg or not is_operator(username_tg):
            logger.warning(f"Неавторизованная попытка перезагрузки сервера от {user_identifier}")
            await query.edit_message_text("❌ У вас нет прав для выполнения этой операции.")
            return

        await query.edit_message_text("⏳ Начинаю перезагрузку сервера tf2-server (docker restart)...")
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
                await query.edit_message_text("✅ Сервер tf2-server успешно перезагружен!")
                # Можно добавить небольшую паузу перед тем, как бот снова будет активно им пользоваться
                # await asyncio.sleep(5)
            else:
                error_msg = stderr.decode().strip() if stderr else "Неизвестная ошибка Docker"
                logger.error(f"Ошибка при перезагрузке сервера tf2-server. Код: {process.returncode}. Ошибка: {error_msg}")
                await query.edit_message_text(f"❌ Ошибка при перезагрузке сервера tf2-server:\n`{error_msg}`", parse_mode='Markdown')

        except FileNotFoundError:
             logger.error("Ошибка перезагрузки: команда 'docker' не найдена по пути /usr/bin/docker")
             await query.edit_message_text("❌ Ошибка: команда 'docker' не найдена.")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при перезагрузке сервера: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла непредвиденная ошибка при перезагрузке сервера.")

    # ==================
    #  Подтверждение оплаты
    # ==================
    elif query.data.startswith("payment_confirmed_"):
        confirmed_user_identifier = query.data.split("_")[2] # Идентификатор пользователя, нажавшего кнопку
        current_time_str = time.strftime('%Y-%m-%d %H:%M:%S')

        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if not admin_chat_id:
            logger.error("ADMIN_CHAT_ID не установлен в .env! Не могу уведомить администратора.")
            await query.edit_message_text(
                "❌ Ошибка конфигурации: не удалось уведомить администратора.\n"
                "Пожалуйста, обратитесь в поддержку."
            )
            return

        try:
            admin_chat_id_int = int(admin_chat_id)
            message_text = (f"💰 Пользователь {user_identifier} (ID: `{user_id}`) "
                            f"нажал кнопку 'Я оплатил'.\n"
                            f"⏰ Время: {current_time_str}\n"
                            f"Пожалуйста, проверьте оплату и активируйте/продлите аккаунт: `{confirmed_user_identifier}vpn`")

            await context.bot.send_message(
                chat_id=admin_chat_id_int,
                text=message_text,
                parse_mode='Markdown'
            )
            logger.info(f"Уведомление об оплате от {user_identifier} успешно отправлено администратору ({admin_chat_id_int}).")
            await query.edit_message_text(
                "✅ Ваше подтверждение отправлено администратору.\n"
                "Ожидайте проверки и активации/продления аккаунта."
            )

        except ValueError:
            logger.error(f"Неверный формат ADMIN_CHAT_ID: '{admin_chat_id}'. Должно быть число.")
            await query.edit_message_text(
                "❌ Ошибка конфигурации: не удалось уведомить администратора.\n"
                "Пожалуйста, обратитесь в поддержку."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администратору ({admin_chat_id}): {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Произошла ошибка при отправке уведомления администратору.\n"
                "Пожалуйста, обратитесь в поддержку."
            )

    # ==================
    #  Меню: Мой VPN
    # ==================
    elif query.data == "menu_get_user":
        await get_user_vpn_info(user_id, username_tg, query.edit_message_text)

    # ==================
    #  Меню: Получить триал
    # ==================
    elif query.data == "menu_get_trial":
        await request_trial_common(user_id, username_tg, query.edit_message_text)

    # ==================
    #  Согласие на триал
    # ==================
    elif query.data.startswith("trial_yes_"):
        trial_user_identifier = query.data.split("_")[2] # Идентификатор пользователя из callback_data
        marzban_username = f"{trial_user_identifier}vpn"
        logger.info(f"Пользователь {trial_user_identifier} согласился на триал. Создаем аккаунт '{marzban_username}'")

        # Небольшая проверка, вдруг пользователь нажал дважды быстро
        if context.user_data.get(f'trial_creating_{trial_user_identifier}', False):
            logger.warning(f"Повторная попытка создания триала для {trial_user_identifier} проигнорирована.")
            await query.answer("Запрос уже обрабатывается...", show_alert=True)
            return
        context.user_data[f'trial_creating_{trial_user_identifier}'] = True # Флаг начала создания

        try:
            await query.edit_message_text(f"⏳ Создаю для вас пробный аккаунт `{marzban_username}`...", parse_mode='Markdown')
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
                         f"✅ Тестовый аккаунт `{marzban_username}` создан!\n\n"
                         f"⏳ Он будет действовать 5 дней.\n\n"
                         f"{format_subscription_links(subscription_links)}\n\n"
                     )
                     payment_url = subscription_links.get('payment_url')
                     if payment_url:
                         reply_text += f"💰 Вы можете оплатить подписку в любое время:\n{payment_url}\n\n"
                     else:
                          reply_text += "Ссылка на оплату не найдена.\n\n"

                     reply_text += "💬 Если возникнут вопросы, пишите в группу @seeyoutubefree"
                     await query.edit_message_text(reply_text, parse_mode='Markdown')
                else:
                     logger.error(f"Не удалось получить subscription_url после создания пользователя '{marzban_username}'. Ответ: {response}")
                     await query.edit_message_text(
                         f"✅ Аккаунт `{marzban_username}` создан, но не удалось получить ссылки для подключения.\n"
                         "Пожалуйста, попробуйте /get_user позже или обратитесь в поддержку.", parse_mode='Markdown'
                     )

            elif response and isinstance(response, dict): # Если ответ есть, но не то, что ожидали
                error_detail = response.get("detail", "Нет деталей")
                logger.error(f"Не удалось создать триал для '{marzban_username}'. Ответ API: {response}")
                if "already exists" in str(error_detail).lower():
                     await query.edit_message_text(f"❌ Не удалось создать аккаунт: пользователь `{marzban_username}` уже существует.", parse_mode='Markdown')
                else:
                     await query.edit_message_text(f"❌ Не удалось создать тестовый аккаунт. Ошибка API: {error_detail}. Попробуйте позже или обратитесь в поддержку.")
            else: # Если ответ None или не словарь
                 logger.error(f"Не удалось создать триал для '{marzban_username}'. Ответ API был None или некорректный.")
                 await query.edit_message_text("❌ Не удалось создать тестовый аккаунт. Произошла ошибка на сервере. Попробуйте позже или обратитесь в поддержку.")

        except Exception as e:
            logger.error(f"Ошибка при создании триала для '{marzban_username}': {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Произошла непредвиденная ошибка при создании аккаунта.\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )
        finally:
             context.user_data[f'trial_creating_{trial_user_identifier}'] = False # Снимаем флаг

    # ==================
    #  Отказ от триала
    # ==================
    elif query.data == "trial_no":
        await query.edit_message_text("Хорошо, вы отказались от тестового периода. Если передумаете, просто нажмите кнопку снова.")


# Основная функция
def main() -> None:
    logger.info("Запуск бота...")
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
            ("start", "🚀 Главное меню"),
            ("get_user", "📱 Мой VPN"),
            ("get_trial", "🎁 Получить пробный период"),
        ]
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