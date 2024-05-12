import logging
import logging.config
import os


class CustomFormatter(logging.Formatter):

    format = "%(asctime)s %(levelname)s [%(name)s]: %(message)s"
    level = "INFO"

    green = "\x1b[32;20m"
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)


def setup_logging_config(DEBUG: bool = False):
    "Setup logging configuration"

    log_dir = 'logs'
    filename = 'bot.log'
    os.makedirs(log_dir, exist_ok=True)

    LEVEL = {True: "DEBUG", False: "INFO"}.get(DEBUG, False)

    LOGGING_CFG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "{asctime} {levelname} [{name}]: {message}",
                "datefmt": '%H:%M:%S',
                "style": "{",
                "level": "INFO",
            },
            "detailed": {
                "format": "{asctime} {levelname} [{name}]: {message}",
                "datefmt": "%Y-%m-%d T%H:%M:%S UTC%z",
                "style": "{",
                "level": "DEBUG",
            },
            "colored": {
                "()": 'logging_config.CustomFormatter',
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "simple",
                "level": "INFO",
            },
            "stdout_color": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "colored",
                "level": "INFO",
            },
            "rotating_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": f"{log_dir}/rotating.log",
                "maxBytes": 100_000_000,
                "backupCount": 3,
            },
            "file": {
                "class": "logging.FileHandler",
                "mode": "w",
                "formatter": "detailed",
                "filename": f"{log_dir}/{filename}",
                "level": "DEBUG",
            },
        },
        "loggers": {
            "": {
                "handlers": {
                    "INFO": ["stdout_color"],
                    "DEBUG": ["stdout", "file"],
                }.get(LEVEL, "INFO"),
                "level": LEVEL,
            },
        }
    }

    logging.config.dictConfig(LOGGING_CFG)


def get_logger(base_logger, mod_name):
    """Get logger."""
    try:
        logger = logging.getLogger(f'{base_logger.name}.{mod_name}')
    except TypeError:
        logger = logging.getLogger(mod_name)
    return logger
