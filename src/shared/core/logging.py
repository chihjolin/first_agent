import logging
import sys


def setup_logging() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format=("[%(levelname)s] %(asctime)s %(name)s - %(message)s"),
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        # 接管 root logger
        force=True,
    )
