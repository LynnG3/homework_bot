"""
Описание скриптов.

Нужны зачем-то.
"""
import logging
import os
import requests
import sys
import time


from telegram import Bot

from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import Not200Error

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


TOKENS_LIST = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(tokens):
        logger.critical('Отсутствует переменная окружения:')
        sys.exit()


def send_message(bot, message):
    """Отправка сообщения в телеграм чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено в телеграм')
    except Exception as error:
        logger.error('Ошибка отправки сообщения', error)


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    try:
        payload = {'from_date': timestamp}
        logger.info(f'Отправка запроса на {ENDPOINT} с параметрами {payload}')
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise Not200Error(homework_statuses)
    except requests.RequestException:
        logger.error(
            'Сбой при запросе к эндпоинту '
            )
    return homework_statuses.json()


def check_response(response):
    """Проверка соответствия ответа документации API сервиса."""
    if not isinstance(response, dict):
        logger.error(
            'Возвращаемый ответ имеет тип данных, отличный от dict'
            )
        raise TypeError
    else:
        value_homework = response.get('homeworks')
    if not isinstance(value_homework, list):
        logger.error(
            'Данные под ключом `homeworks` приходят не в виде списка.'
            )
        raise TypeError
    else:
        return value_homework


def parse_status(homework):
    """Извлечение из инфо о конкретной домашней работе её статуса."""
    if ('homework_name' in homework) and (
        'status' in homework) and (
            homework['status'] in HOMEWORK_VERDICTS):
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        verdict = HOMEWORK_VERDICTS.get(homework_status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    elif not homework:
        raise KeyError('В ответе API домашки нет ключа homework_name')
    else:
        raise KeyError('В ответе API домашки нет ключа homework_name')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time() - RETRY_PERIOD - 50000)
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        else:
            if message:
                send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
