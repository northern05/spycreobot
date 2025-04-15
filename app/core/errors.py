class CreditErrors:
    USER_NOT_EXISTS = "User not exists!"
    USER_NOT_OWNER = "That's not your chat!"
    TELEGRAM_NOT_CONNECTED = "Telegram not connected!"


class Errors:
    credit_errors = CreditErrors()


errors = Errors()
