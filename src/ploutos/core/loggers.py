import sys

from loguru import logger

from ploutos.core.config import settings

_SIMPLE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}"


def setup_logging() -> None:
    logger.remove()

    if settings.LOG_USE_BASIC_FORMAT:
        logger.add(sys.stderr, level=settings.LOG_LEVEL, format=_SIMPLE_FORMAT)
    else:
        logger.add(sys.stderr, level=settings.LOG_LEVEL, serialize=True)
