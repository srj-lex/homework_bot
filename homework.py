import os
import requests
import logging
import time
from http import HTTPStatus

import telegram
from telegram.error import TelegramError
from dotenv import load_dotenv

import exceptions


load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens() -> None:
    """Проверяет доступность переменных окружения."""
    env_var = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return all(env_var)


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    payload = {"from_date": timestamp}
    try:
        logger.debug(f"Запрос к {ENDPOINT}. Параметры: {HEADERS}, {payload}")
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException:
        raise exceptions.APIConnectError(
            "Ошибка при попытке соединения с эндпоинтом"
        )
    if response.status_code != HTTPStatus.OK:
        raise exceptions.APIStatusError(
            f"Код ответа сервера: {response.status_code}"
        )
    return response.json()


def check_response(response: dict) -> dict:
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError("Неверный тип передаваемого аргумента 'response'")

    if "homeworks" not in response:
        raise KeyError("Отсутсвует ключ 'homeworks'")

    if not isinstance(response["homeworks"], list):
        raise TypeError("Неверный тип значения по  ключу 'homeworks'")

    return response.get("homeworks")


def parse_status(homework: dict) -> str:
    """Извлекает статус домашней работы работы."""
    if homework.get("status", None) is None:
        raise KeyError("Отсутсвует ключ 'status'")

    if homework["status"] not in ("reviewing", "approved", "rejected"):
        raise ValueError("Неожиданный статус домашней работы")

    if homework.get("homework_name", None) is None:
        raise KeyError("Отсутсвует ключ 'homework_name'")

    homework_name = homework.get("homework_name")
    verdict = HOMEWORK_VERDICTS.get(homework.get("status"))
    return (
        f'Изменился статус проверки работы "{homework_name}".\n' f"{verdict}"
    )


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except TelegramError:
        logger.error("Произошла ошибка Telegram при отправке сообщения")
    else:
        logger.debug("Бот отправил сообщение:" f"{message}")


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            "Отсутствует обязательная переменная окружения."
            "Программа принудительно остановлена."
        )
        raise exceptions.TokenError("Отсутствует переменная окружения")

    prev_mes = None
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_time = None
    while True:
        try:
            time_resp = timestamp if current_time is None else current_time
            response = get_api_answer(time_resp)
            current_time = response["current_date"]
            homework = check_response(response)
            if homework == []:
                logger.debug("Статус домашней работы не изменился")
            else:
                mes = parse_status(homework[0])
                send_message(bot, mes)
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            if message != prev_mes:
                send_message(bot, message)
                prev_mes = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
