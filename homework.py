"""
Код для работы Телеграм бота.

Бот проверяет доступность переменных окружения,
запрашивает информацию с эндпойнта сервиса каждые 10 минут,
проверяет корректность ответа сервиса
и отправляет сообщение о статусе домашки в Телеграм пользоваетля
"""

import logging
import os
import sys
import time
from http import HTTPStatus
from os.path import abspath, dirname

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from exceptions import (EmptyAnswerApiError, EnvError, Not200Error,
                        RequestError, SendMessageError)

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


LOG_PATH_FILE = dirname(dirname(abspath(__file__)))

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = {'practicum_token': PRACTICUM_TOKEN,
              'telegram_token': TELEGRAM_TOKEN,
              'telegram_chat_id': TELEGRAM_CHAT_ID}
    token_names = []
    for token, value in tokens.items():
        if not value:
            token_names.append(token)
    if token_names:
        logger.critical('Отсутствует переменная окружения')
        raise EnvError('Нет значений: {token_names}')


def send_message(bot, message):
    """Отправка сообщения в телеграм чат."""
    try:
        logger.info('Отправляем сообщение в телеграмм')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError:
        raise SendMessageError('Сообщение не отправлено')
    else:
        logger.debug('Сообщение отправлено в телеграм')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    request_to_api = {'url': ENDPOINT,
                      'headers': HEADERS,
                      'params': payload}
    try:
        logger.info(
            'Отправка запроса на {url} с параметрами {params}'.format(
                **request_to_api
            )
        )
        homework_statuses = requests.get(**request_to_api)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise Not200Error(homework_statuses)
    except requests.RequestException:
        logger.error('Сбой при запросе к эндпоинту')
        raise RequestError('Сбой при запросе к эндпоинту')
    return homework_statuses.json()


def check_response(response):
    """Проверка соответствия ответа документации API сервиса."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных ответа API отличен от dict')
    if 'homeworks' not in response:
        raise EmptyAnswerApiError('Пустой ответ API')
    value_homework = response.get('homeworks')
    if not isinstance(value_homework, list):
        raise TypeError(
            'Данные под ключом `homeworks` приходят не в виде списка.'
        )
    return value_homework


def parse_status(homework):
    """Извлечение из инфо о конкретной домашней работе её статуса."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе API домашки нет ключа homework_name')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise KeyError(
            'API домашки возвращает недокументированный статус'
        )
    if 'status' not in homework:
        raise KeyError(
            'API домашки возвращает домашку без статуса'
        )
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    current_report = {}
    prev_report = {}
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', timestamp)
            homeworks = check_response(response)
            if homeworks:
                current_report['output'] = parse_status(homeworks[0])
            else:
                current_report['output'] = 'Нет новых статусов'
            if current_report != prev_report:
                send_message(bot, current_report)
                prev_report = current_report.copy()
        except EmptyAnswerApiError as error:
            logger.error(error)
        except SendMessageError as error:
            logger.error(error)
        except Exception as error:
            current_report['output'] = f'Сбой в работе программы: {error}'
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
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    main()
