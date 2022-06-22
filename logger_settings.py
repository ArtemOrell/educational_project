import logging.handlers
from datetime import datetime


class CustomFormatter(logging.Formatter):
    """Logging colored formatter,
    adapted from https://alexandra-zaharia.github.io/posts/make-your-own-custom-color-formatter-with-python-logging/"""

    green = '\033[0;32m\033[3m'
    grey = '\x1b[38;21m\033[3m'
    blue = '\x1b[38;5;39m\033[3m'
    yellow = '\x1b[38;5;226m\033[3m'
    red = '\x1b[38;5;196m\033[3m'
    bold_red = '\x1b[31;1m\033[3m'
    reset = '\x1b[0m'

    def __init__(self, fmt: str, datefmt: str, style: str):
        super().__init__()
        self.datefmt = datefmt
        self.style = style
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.green + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt
        }

    def format(self, record: logging.LogRecord):
        log_format = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_format, self.datefmt, self.style)
        return formatter.format(record)


class CustomHandler(logging.handlers.RotatingFileHandler):

    def __init__(self, filename: str, backupCount: int, mode: str, encoding: str, maxBytes: int):
        self.new_filename = datetime.now().strftime(f'%m.%d.%Y_{filename}.log')
        self.mode = mode
        super().__init__(self.new_filename, mode, maxBytes, backupCount, encoding)

    def emit(self, record: logging.LogRecord):
        message = self.format(record)
        if record.levelname == 'INFO':
            message = f'          {message}          '
            lines = ['#' * len(message), '\n\n', message, '\n\n']
            with open(self.new_filename, mode=self.mode) as f:
                f.writelines(lines)
        else:
            lines = [message, '\n\n', len(message.split('\n')[0]) * '-', '\n\n']
            with open(self.new_filename, mode=self.mode) as f:
                f.writelines(lines)


class CustomFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelname in ['INFO', 'DEBUG', 'WARNING']
