"""Кастомные исключения для проекта."""

from telegram.error import TelegramError


class Not200Error(Exception):
    """Ошибка ответа API. Код ответа отличен от 200."""

    pass


class SendMessageError(TelegramError):
    """Ошибка отправки сообщения."""

    pass


class EmptyAnswerApiError(Exception):
    """Пустой ответ API. Домашек не найдено."""

    pass


class EnvError(EnvironmentError):
    """Отсутствие переменной/переменных окружения."""

    pass


class RequestError(Exception):
    """Сбой при запросе к эндпойнту."""

    pass
