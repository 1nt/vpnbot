import requests
import json
import time
import logging
import os
from dotenv import load_dotenv

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем переменные из .env
load_dotenv()

class MarzbanBackend:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {"accept": "application/json"}
        self.base_url = os.getenv("MARZBAN_API_URL")  # Замените на ваш URL API Marzban
        self.payment_url = os.getenv("PAYMENT_URL")
        if not self.headers.get("Authorization"):
            self.authorize()

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}/{path}"
        response = self.session.request("GET", url, verify=False, headers=self.headers)
        if response.status_code == 200:
            return response.json()

    def _post(self, path: str, data=None) -> dict:
        url = f"{self.base_url}/{path}"
        if not path == "api/admin/token":
            data = json.dumps(data)
        response = self.session.request("POST", url, verify=False, headers=self.headers, data=data)
        if response.status_code == 201 or response.status_code == 200:
            return response.json()

    def _put(self, path: str, data=None) -> dict:
        url = f"{self.base_url}/{path}"
        json_data = json.dumps(data)
        response = self.session.put(url, verify=False, headers=self.headers, data=json_data)

        if response.status_code == 200:
            logger.info(f"cmd xray PUT {path}, data: {data}")
            return response.json()
        else:
            logger.error(f"cmd xray PUT not 200 status_code! {path}, data: {data}")

    def authorize(self) -> None:
        data = {
            "username": os.getenv("MARZBAN_USER"),  # Замените на ваше имя пользователя
            "password": os.getenv("MARZBAN_PASSWORD")  # Замените на ваш пароль
        }
        response = self._post("api/admin/token", data=data)
        token = response.get("access_token")
        self.headers["Authorization"] = f"Bearer {token}"

    def create_user(self, name: str, is_trial: bool = False) -> dict:
        data = {
            "username": name,
            "proxies": {
                "vless": {
                    "flow": "xtls-rprx-vision",
                },
                "shadowsocks": {
                    "method": "chacha20-ietf-poly1305"
                }
            },
            "inbounds": {
                "vless": ["VLESS TCP REALITY"],
                "shadowsocks": ["Shadowsocks TCP"]
            },
            "data_limit": 15 * 1024 * 1024 * 1024,
            "data_limit_reset_strategy": "day",
        }
        
        if is_trial:
            # Устанавливаем срок действия через 5 дней
            expire_time = int(time.time()) + (5 * 24 * 60 * 60)
            data["expire"] = expire_time
            logger.info(f"Creating trial user {name} with expire time: {expire_time}")
        
        response = self._post("api/user", data=data)
        if response:
            logger.info(f"User created: {name}, trial: {is_trial}")
        else:
            logger.error(f"Failed to create user: {name}")
        return response

    def get_subscription_links(self, username: str, subscription_url: str) -> dict:
        """Generate subscription links for different VPN clients"""
        return {
            'v2rayng': f"https://play.google.com/store/apps/details?id=com.v2ray.ang&hl=ru",
            'streisand': f"https://apps.apple.com/ru/app/streisand/id6450534064",
            'subuser_url': f"{self.base_url}{subscription_url}",
            'payment_url': f"{self.payment_url}",
        }

    def get_user(self, name: str) -> dict:
        try:
            response = self._get(f"api/user/{name}")
            if response:
                user = response.get("username")
                status = response.get("status")
                subscription_url = response.get("subscription_url")
                
                if subscription_url:
                    response['subscription_links'] = self.get_subscription_links(user, subscription_url)
                
                logger.info(f"get user: {user}, status: {status}")
                return response
            else:
                logger.info(f"User not found: {name}")
                return None
        except Exception as e:
            logger.error(f"Error getting user {name}: {str(e)}")
            return None

    def disable_user(self, name: str) -> dict:
        data = {
            "status": "disabled"
        }
        response = self._put(f"api/user/{name}", data=data)
        if response:
            logger.info(f"Disable xray user: {name} success, {response.get('username', 'unknown username')}")
            check = self.get_user(name)
            time.sleep(0.25)
            if check.get("status") != data.get("status"):
                logger.error(f"After disable user {name}, user is not disabled!")
            return response
        else:
            logger.warning(f"xray user {name} not found")
            return {}

    def enable_user(self, name: str) -> dict:
        data = {
            "status": "active"
        }
        response = self._put(f"api/user/{name}", data=data)
        if response:
            logger.info(f"Enable xray user: {name} success, {response.get('username', 'unknown username')}")
            return response
        else:
            logger.warning(f"xray user {name} not found")
            return {}

