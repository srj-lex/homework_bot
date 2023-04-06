import os
import requests
import logging
import time

import telegram
from dotenv import load_dotenv

from exceptions import TokenError


load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
DEBUG_VAR = 2600000


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
    for i in env_var:
        if i is None:
            logger.critical(
                "Отсутствует обязательная "
                f"переменная окружения: {i} "
                "Программа принудительно остановлена."
            )
            raise TokenError("Отсутствует переменная окружения")


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    payload = {"from_date": timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception:
        logger.error("Упс, интерент кончился")
    if response.status_code != 200:
        logger.error(
            "API Яндекса недоступен."
            f"Код ответа сервера: {response.status_code}"
        )
        raise requests.RequestException

    return response.json()


def check_response(response: dict) -> dict:
    """Проверяет ответ API на соответствие документации."""
    if type(response) is not dict:
        raise TypeError("Неверный тип передаваемого аргумента response")

    if "homeworks" not in response:
        logger.error("Ключ 'homeworks' отсутствует в ответе от API")
        raise KeyError("Отсутсвует ключ 'homeworks'")

    if type(response["homeworks"]) is not list:
        raise TypeError("Неверный тип значения по  ключу 'homeworks'")

    if response.get("homeworks") == []:
        logger.debug("Статус домашней работы не изменился")
    else:
        return response.get("homeworks")[0]


def parse_status(homework: dict) -> str:
    """Извлекает статус домашней работы работы."""
    if homework.get("status", None) is None:
        logger.error("Статус отсутствует")
        raise KeyError("Отсутсвует ключ 'status'")

    if homework["status"] not in ("reviewing", "approved", "rejected"):
        logger.error("Неожиданный статус домашней работы")
        raise ValueError("Неожиданный статус домашней работы")

    if homework.get("homework_name", None) is None:
        logger.error("Нет ключа 'homework_name'")
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
        logger.debug("Бот отправил сообщение:" f"{message}")
    except Exception:
        logger.exception("Произошла ошибка при отправке сообщения")


def main():
    """Основная логика работы бота."""
    prev_mes = []
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework is not None:
                mes = parse_status(homework)
                send_message(bot, mes)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            if message not in prev_mes:
                send_message(bot, message)
                prev_mes.append(message)


if __name__ == "__main__":
    main()
