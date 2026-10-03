"""Connexion unique du compte TikTok (à lancer une fois, puis si TikTok demande de se reconnecter).

Usage : docker compose run --rm bot python -m bimouia.tiktok_auth
"""

import asyncio
import secrets
from urllib.parse import parse_qs, urlparse

import aiohttp

from .config import load_config
from .db import Database
from .sources.tiktok import TikTokAuth


async def main() -> None:
    config = load_config()
    if not config.tiktok_videos_enabled:
        raise SystemExit("Renseigne TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET et TIKTOK_REDIRECT_URI dans .env")

    db = await Database.connect(config)
    try:
        async with aiohttp.ClientSession() as session:
            auth = TikTokAuth(session, db, config.tiktok_client_key, config.tiktok_client_secret,
                              config.tiktok_redirect_uri)
            state = secrets.token_urlsafe(16)
            print("\n1. Ouvre ce lien et autorise l'application :\n")
            print(auth.authorize_url(state))
            print("\n2. Tu arrives sur ta page de redirection (même si elle affiche une erreur).")
            redirected = input("   Colle ici l'adresse complète de cette page : ").strip()

            query = parse_qs(urlparse(redirected).query)
            if query.get("state", [""])[0] != state:
                raise SystemExit("Adresse invalide : le paramètre « state » ne correspond pas. Recommence.")
            if "code" not in query:
                raise SystemExit(f"Autorisation refusée : {query.get('error_description', query)}")

            await auth.exchange_code(query["code"][0])
            print("\nCompte TikTok connecté. BimouIA annoncera les prochaines vidéos.")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
