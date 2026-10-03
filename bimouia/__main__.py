"""Point d'entrée : python -m bimouia"""

import discord

from .bot import BimouIA
from .config import load_config


def main() -> None:
    discord.utils.setup_logging()
    config = load_config()
    BimouIA(config).run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
