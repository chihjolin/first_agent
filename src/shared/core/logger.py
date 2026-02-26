import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    建立標準化 Logger，輸出至 stdout 確保 Docker logs 能順利捕捉
    """
    logger = logging.getLogger(name)

    # 避免重複綁定handler
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "[%(levelname)s] %(asctime)s %(name)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
