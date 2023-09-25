"""
Код для работы Телеграм бота.

Бот проверяет доступность переменных окружения,
запрашивает информацию с эндпойнта сервиса каждые 10 минут,
проверяет корректность ответа сервиса
и отправляет сообщение о статусе домашки в Телеграм пользоваетля
"""

import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from os.path import dirname, abspath
from telegram import Bot
from telegram.error import TelegramError

from exceptions import (Not200Error, SendMessageError, EmptyAnswerApiError,
                        EnvError, RequestError
                        )

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

LOG_PATH_FILE = dirname(dirname(abspath(__file__)))

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    TOKENS_LIST = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    # без переопределения этого списка тесты не проходят,
    # т.к. в тестах проставляется None
    if not all(TOKENS_LIST):
        logger.critical('Отсутствует переменная окружения')
        raise EnvError


def send_message(bot, message):
    """Отправка сообщения в телеграм чат."""
    try:
        logger.info('Отправляем сообщение в телеграмм')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError:
        logger.error('Ошибка отправки сообщения в телеграмм')
        raise SendMessageError
    else:
        logger.debug('Сообщение отправлено в телеграм')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    request_to_api = {'endpoint': ENDPOINT,
                      'headers': HEADERS,
                      'params': payload}
    try:
        logger.info(f'Программа начала запрос {request_to_api}')
        logger.info(f'Отправка запроса на {ENDPOINT} с параметрами {payload}')
        homework_statuses = requests.get(request_to_api)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise Not200Error(homework_statuses)
    except requests.RequestException:
        logger.error('Сбой при запросе к эндпоинту')
        raise RequestError
    return homework_statuses.json()


def check_response(response):
    """Проверка соответствия ответа документации API сервиса."""
    if not isinstance(response, dict):
        logger.error(
            'Возвращаемый ответ имеет тип данных, отличный от dict'
        )
        raise TypeError('Тип данных ответа API отличен от dict')
    if 'homeworks' not in response:
        raise EmptyAnswerApiError
    value_homework = response.get('homeworks')
    if not isinstance(value_homework, list):
        logger.error(
            'Данные под ключом `homeworks` приходят не в виде списка.'
        )
        raise TypeError(
            'Данные под ключом `homeworks` приходят не в виде списка.'
        )
    return value_homework


def parse_status(homework):
    """Извлечение из инфо о конкретной домашней работе её статуса."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе API домашки нет ключа homework_name')
    if ('status' not in homework) or (
            homework['status'] not in HOMEWORK_VERDICTS):
        raise KeyError(
            'API домашки возвращает недокументированный статус'
            'домашней работы,'
            'либо домашку без статуса'
        )
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    # timestamp = int(time.time() - RETRY_PERIOD)
    timestamp = 0
    while True:
        try:
            current_report = {}
            prev_report = {}
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', timestamp)
            homeworks = check_response(response)
            if homeworks:
                current_report = parse_status(homeworks[0])
            else:
                current_report = 'Нет новых статусов'

            if current_report != prev_report:
                send_message(bot, current_report)
                prev_report = current_report.copy()

        except Exception as error:
            current_report = f'Сбой в работе программы: {error}'
            logger.error(current_report)
            if current_report != prev_report:
                send_message(bot, current_report)
                prev_report = current_report.copy()
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(LOG_PATH_FILE)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    main()
