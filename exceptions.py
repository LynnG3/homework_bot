"""Здесь будут исключения."""


class Not200Error(Exception):
    """Ошибка ответа API."""

    print("Код ответа API не 200")


class SendMessageError(Exception):
    """Ошибка отправки сообщения."""

    pass
