# homework_bot

### Описание

Телеграм-бот работающий с API Яндекс-Практикума,

позволяющий оперативно получать информацию о статусе проверки

домашнего задания.

### Стэк технологий:

- Работа с TelegramBot API: python-telegram-bot = 13.7;
- Логирование: модуль logging;
- Запросы к API: requests = 2.26.0.

### Как запустить проект:

Клонировать репозиторий:
```
git clone git@github.com:srj-lex/homework_bot.git
```

В корне проекта выполнить последовательно команды:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Далее необходимо создать и заполнить файл .env в корне проекта.

Необходимо указать валидные значения для ключей:

PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

Запустить бота:
```
python3 homework.py
```
