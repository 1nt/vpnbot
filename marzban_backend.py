# --- START OF FILE marzban_backend.py ---

import requests
import json
import time
import logging
import os
from dotenv import load_dotenv
import urllib.parse # Для кодирования URL в ссылках

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

# Загружаем переменные из .env (если файл существует)
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    logger.info(".env файл загружен для MarzbanBackend.")
else:
    logger.info(".env файл не найден, используются переменные окружения.")


# Отключаем предупреждения о небезопасных запросах (verify=False), но это ПЛОХО!
# Лучше настроить валидный сертификат на сервере Marzban или добавить CA в доверенные.
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.warning("Отключены предупреждения InsecureRequestWarning для HTTPS запросов (verify=False). ЭТО НЕБЕЗОПАСНО!")
except ImportError:
    logger.warning("Не удалось импортировать urllib3 для отключения предупреждений.")


class MarzbanBackend:
    def __init__(self):
        self.base_url = os.getenv("MARZBAN_API_URL")
        self.username = os.getenv("MARZBAN_USER")
        self.password = os.getenv("MARZBAN_PASSWORD")
        self.payment_url = os.getenv("PAYMENT_URL", "") # URL для кнопки оплаты
        self.trial_days = int(os.getenv("TRIAL_DAYS", "5")) # Дней для триала
        self.router_url = os.getenv("ROUTER_URL","https://ozon.ru/product/2288765942") # URL для покупки роутера
        self.default_timeout = 20 # Таймаут для запросов в секундах

        if not self.base_url or not self.username or not self.password:
             logger.critical("MARZBAN_API_URL, MARZBAN_USER или MARZBAN_PASSWORD не установлены!")
             # Вместо падения, можно выбросить исключение, чтобы бот не запустился
             raise ValueError("Ключевые переменные окружения для Marzban API не установлены.")

        logger.info(f"MarzbanBackend инициализирован. API URL: {self.base_url}")
        # Убираем / в конце base_url, если он есть, чтобы избежать двойных //
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]

        self.session = requests.Session()
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json" # Важно для POST/PUT с JSON телом
            }
        # Устанавливаем заголовки для сессии
        self.session.headers.update(self.headers)

        # Авторизуемся при инициализации
        if not self._authorize():
             # Если авторизация не удалась, генерируем исключение
             raise RuntimeError("Не удалось авторизоваться в Marzban API при инициализации.")

        print('DEBUG: router_url from env:', os.getenv('ROUTER_URL'))

    def _make_request(self, method: str, path: str, data=None, params=None, is_auth=False) -> requests.Response | None:
        """Внутренний метод для выполнения запросов к API."""
        full_url = f"{self.base_url}/{path}"
        request_headers = self.session.headers.copy()

        # Для запроса токена Content-Type другой
        if is_auth:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            json_data = None # Данные передаются как form-data
        else:
            # Для остальных запросов кодируем данные в JSON, если они есть
            json_data = json.dumps(data) if data else None
            # Убираем Content-Type для GET запросов, если нет тела
            if method.upper() == "GET" and not data:
                 request_headers.pop("Content-Type", None)


        logger.debug(f"Запрос к Marzban API: {method.upper()} {full_url}")
        if json_data and not is_auth: logger.debug(f"Тело запроса (JSON): {json_data}")
        if data and is_auth: logger.debug(f"Тело запроса (Form): {data}") # Не логгируем пароль в проде
        if params: logger.debug(f"Параметры запроса: {params}")

        try:
            response = self.session.request(
                method=method,
                url=full_url,
                headers=request_headers,
                data=data if is_auth else json_data, # Передаем form-data для auth, json для остального
                params=params,
                verify=False, # !!! НЕБЕЗОПАСНО !!! Используйте True и настройте сертификаты
                timeout=self.default_timeout
            )
            logger.debug(f"Ответ от Marzban API: Статус {response.status_code}")
            # Логируем тело ответа только при ошибке или на DEBUG уровне
            if response.status_code < 200 or response.status_code >= 300:
                logger.warning(f"Код ответа: {response.status_code}. Тело ответа: {response.text[:500]}") # Ограничиваем длину лога
            elif logger.isEnabledFor(logging.DEBUG):
                 logger.debug(f"Тело успешного ответа: {response.text[:500]}")

            # Проверка на 401/403 - возможно, токен истек (хотя Marzban обычно дает долгие токены)
            if response.status_code in [401, 403] and not is_auth:
                logger.warning(f"Получен статус {response.status_code}. Попытка повторной авторизации...")
                if self._authorize():
                    logger.info("Повторная авторизация успешна. Повторяем исходный запрос...")
                    # Повторяем исходный запрос с новым токеном в сессии
                    # Обновляем заголовки для повторного запроса, т.к. сессия уже обновилась
                    request_headers = self.session.headers.copy()
                    if is_auth: # На всякий случай, хотя вряд ли сюда попадем с is_auth=True
                        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
                    else:
                        request_headers["Content-Type"] = "application/json"
                        if method.upper() == "GET" and not data:
                           request_headers.pop("Content-Type", None)

                    response = self.session.request(
                        method=method, url=full_url, headers=request_headers,
                        data=data if is_auth else json_data, params=params,
                        verify=False, timeout=self.default_timeout
                    )
                    logger.info(f"Статус ответа после повторной авторизации: {response.status_code}")
                    if response.status_code < 200 or response.status_code >= 300:
                         logger.error(f"Повторный запрос также неудачен ({response.status_code}): {response.text[:500]}")
                else:
                    logger.error("Повторная авторизация не удалась.")
                    # Возвращаем исходный ошибочный ответ
                    return response

            return response

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут запроса ({self.default_timeout}s) к Marzban API: {method.upper()} {full_url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети/соединения при запросе к Marzban API: {method.upper()} {full_url} - {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при запросе к Marzban API: {method.upper()} {full_url} - {e}", exc_info=True)
            return None

    def _parse_response(self, response: requests.Response | None) -> dict | None:
        """Парсит JSON ответ, обрабатывая ошибки."""
        if response is None:
            return None # Ошибка произошла на уровне запроса

        # Успешные коды (200 OK, 201 Created)
        if 200 <= response.status_code < 300:
            try:
                # Если тело ответа пустое (например, 204 No Content), возвращаем пустой словарь или True?
                if not response.content:
                    logger.debug(f"Успешный ответ ({response.status_code}) без тела.")
                    return {} # Возвращаем пустой словарь как признак успеха без данных
                json_data = response.json()
                logger.debug("Ответ успешно распарсен как JSON.")
                return json_data
            except json.JSONDecodeError:
                logger.error(f"Не удалось декодировать JSON из успешного ответа ({response.status_code}). Тело: {response.text[:500]}")
                return None # Ошибка парсинга JSON
        # Пользователь не найден
        elif response.status_code == 404:
            logger.warning(f"Ресурс не найден (404). URL: {response.url}")
            return None # Явно возвращаем None при 404
        # Другие ошибки клиента или сервера
        else:
            logger.error(f"API Marzban вернул ошибку {response.status_code}. URL: {response.url}. Тело: {response.text[:500]}")
            # Можно попробовать извлечь 'detail' из ошибки, если это JSON
            detail = None
            try:
                 error_json = response.json()
                 detail = error_json.get('detail', 'Нет деталей в JSON')
                 logger.error(f"Детали ошибки из JSON: {detail}")
            except json.JSONDecodeError:
                 logger.error("Тело ошибки не является валидным JSON.")
            # Возвращаем словарь с ошибкой, чтобы вызывающий код мог ее обработать? Или None?
            # Пока возвращаем None для единообразия
            return None

    def _authorize(self) -> bool:
        """Получает токен и сохраняет его в заголовках сессии."""
        path = "api/admin/token"
        auth_data = {
            "username": self.username,
            "password": self.password
        }
        # Логгируем без пароля
        logger.info(f"Попытка авторизации пользователя '{self.username}' в Marzban API...")

        response = self._make_request("POST", path, data=auth_data, is_auth=True)

        if response is not None and response.status_code == 200:
            try:
                token_data = response.json()
                token = token_data.get("access_token")
                token_type = token_data.get("token_type", "Bearer")
                if token:
                    self.session.headers["Authorization"] = f"{token_type} {token}"
                    logger.info(f"Авторизация успешна. Токен типа '{token_type}' получен.")
                    return True
                else:
                    logger.error("Авторизация не удалась: 'access_token' не найден в ответе.")
                    return False
            except json.JSONDecodeError:
                logger.error(f"Авторизация не удалась: не удалось декодировать JSON из ответа. Тело: {response.text[:500]}")
                return False
            except Exception as e:
                 logger.error(f"Непредвиденная ошибка при обработке ответа авторизации: {e}", exc_info=True)
                 return False
        else:
            status = response.status_code if response is not None else "N/A"
            logger.error(f"Авторизация не удалась. Статус ответа: {status}")
            return False

    def create_user(self, name: str, is_trial: bool = False) -> dict | None:
        """Создает нового пользователя."""
        path = "api/user"
        data = {
            "username": name,
            "proxies": { # Конфигурация прокси по умолчанию
                "vless": {"flow": "xtls-rprx-vision"},
                "shadowsocks": {"method": "chacha20-ietf-poly1305"}
            },
            "inbounds": { # В какие инбаунды добавить пользователя
                "vless": ["VLESS TCP REALITY"], # Убедитесь, что эти имена инбаундов существуют в вашей конфигурации Marzban
                "shadowsocks": ["Shadowsocks TCP"]
            },
            # Лимит данных на 5 дней для триала ~ 15GB? Или сделать меньше?
            # Указываем в БАЙТАХ. 15 GiB = 15 * 1024 * 1024 * 1024 bytes
            "data_limit": 15 * (1024**3) if is_trial else 0, # 0 - без лимита для обычных
            "data_limit_reset_strategy": "no_reset", # 'day', 'week', 'month', 'year', 'no_reset'
        }

        if is_trial:
            # Устанавливаем срок действия через trial_days дней (в секундах от эпохи)
            expire_timestamp = int(time.time()) + (self.trial_days * 24 * 60 * 60)
            data["expire"] = expire_timestamp
            # Лимит для триала (примерно 15 Гб)
            data["data_limit"] = 15 * (1024**3)
            data["data_limit_reset_strategy"] = "no_reset" # Не сбрасывать лимит для триала
            logger.info(f"Подготовка к созданию триального пользователя '{name}'. Срок до: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_timestamp))}, Лимит: 15 GiB")
        else:
            # Для обычных пользователей можно не ставить expire и data_limit, или поставить другие значения
            data["expire"] = 0 # 0 - без срока действия
            data["data_limit"] = 0 # 0 - без лимита данных
            logger.info(f"Подготовка к созданию обычного пользователя '{name}'.")


        response = self._make_request("POST", path, data=data)
        parsed_response = self._parse_response(response)

        if parsed_response:
            logger.info(f"Пользователь '{name}' (trial={is_trial}) успешно создан. Ответ: {parsed_response}")
        else:
            # Логирование ошибки уже произошло в _parse_response или _make_request
            logger.error(f"Не удалось создать пользователя '{name}' (trial={is_trial}).")

        return parsed_response # Возвращаем словарь с данными пользователя или None

    def get_subscription_links(self, username: str, subscription_url: str | None) -> dict:
        """Генерирует ссылки для подписки для разных клиентов."""
        links = {
            'v2rayng': "https://github.com/2dust/v2rayNG/releases/download/1.10.5/v2rayNG_1.10.5_universal.apk", # Просто ссылка на приложение
            'streisand': "https://apps.apple.com/app/streisand/id6450534064", # Просто ссылка на приложение
            'subuser_url': None, # URL для импорта подписки
            'payment_url': self.payment_url or None, # URL для оплаты
        
        }
        if not subscription_url:
            logger.warning(f"Не передан subscription_url для пользователя '{username}', ссылка 'subuser_url' будет пустой.")
            return links

        # Формируем полную URL подписки
        full_sub_url = f"{self.base_url}{subscription_url}"
        links['subuser_url'] = full_sub_url

        # Можно добавить генерацию прямых ссылок для импорта, если нужно
        # try:
        #     encoded_sub_url = urllib.parse.quote_plus(full_sub_url)
        #     # links['v2rayng_import'] = f"v2rayng://install-sub/?url={encoded_sub_url}&name={urllib.parse.quote(username)}"
        #     # links['streisand_import'] = f"streisand://import/{full_sub_url}"
        # except Exception as e:
        #     logger.error(f"Ошибка кодирования URL подписки для '{username}': {e}")

        logger.debug(f"Сгенерированы ссылки для пользователя '{username}': {links}")
        return links

    def get_user(self, name: str) -> dict | None:
        """Получает информацию о пользователе."""
        path = f"api/user/{name}"
        logger.info(f"Запрос информации о пользователе '{name}'...")
        response = self._make_request("GET", path)
        user_data = self._parse_response(response)

        if user_data and isinstance(user_data, dict):
            # Добавляем ссылки на подписку, если пользователь найден
            sub_url = user_data.get("subscription_url")
            user_data['subscription_links'] = self.get_subscription_links(name, sub_url)
            logger.info(f"Информация для пользователя '{name}' успешно получена.")
            return user_data
        else:
            # Лог о том, что пользователь не найден или ошибка, уже был в _parse_response
            # logger.info(f"Пользователь '{name}' не найден или произошла ошибка при получении данных.")
            return None

    def _modify_user(self, name: str, data: dict) -> dict | None:
        """Общий метод для изменения пользователя (PUT)."""
        path = f"api/user/{name}"
        logger.info(f"Попытка изменить пользователя '{name}'. Данные: {data}")
        response = self._make_request("PUT", path, data=data)
        return self._parse_response(response)

    def disable_user(self, name: str) -> dict | None:
        """Отключает пользователя."""
        data = {"status": "disabled"}
        logger.info(f"Отключение пользователя '{name}'...")
        response = self._modify_user(name, data)
        if response:
            logger.info(f"Пользователь '{name}' успешно отключен.")
            # Проверка статуса после отключения (опционально)
            # try:
            #     time.sleep(0.5) # Даем время примениться
            #     check_user = self.get_user(name)
            #     if check_user and check_user.get("status") != "disabled":
            #          logger.warning(f"Проверка после отключения '{name}' показала статус '{check_user.get('status')}' вместо 'disabled'.")
            # except Exception as e:
            #      logger.warning(f"Ошибка при проверке статуса пользователя '{name}' после отключения: {e}")
        else:
             logger.warning(f"Не удалось отключить пользователя '{name}'.")
        return response

    def enable_user(self, name: str) -> dict | None:
        """Включает пользователя."""
        data = {"status": "active"}
        logger.info(f"Включение пользователя '{name}'...")
        response = self._modify_user(name, data)
        if response:
            logger.info(f"Пользователь '{name}' успешно включен.")
        else:
             logger.warning(f"Не удалось включить пользователя '{name}'.")
        return response

    # Можно добавить и другие методы API Marzban по аналогии
    # def delete_user(self, name: str) -> bool: ...
    # def modify_user_data_limit(self, name: str, limit_bytes: int) -> dict | None: ...
    # def modify_user_expire(self, name: str, expire_timestamp: int) -> dict | None: ...

# --- END OF FILE marzban_backend.py ---