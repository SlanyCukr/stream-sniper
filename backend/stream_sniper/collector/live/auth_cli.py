"""One-time browser bootstrap for the live chat bot refresh token."""

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

from ..twitch_api import TwitchCredentials
from .secure_files import write_private_text


def _save_token(output: Path, refresh_token: str) -> Path:
    return write_private_text(output, refresh_token)


def _report_success() -> None:
    print("Authorization completed; credential file saved with mode 0600")


async def authenticate(output: Path) -> None:
    credentials = TwitchCredentials.from_env()
    twitch = await Twitch(credentials.client_id, credentials.client_secret)
    try:
        authenticator = UserAuthenticator(twitch, [AuthScope.CHAT_READ])
        _, refresh_token = await authenticator.authenticate()
        await asyncio.to_thread(_save_token, output, refresh_token)
        _report_success()
    finally:
        await twitch.close()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Authorize the read-only Twitch chat bot")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".live-refresh-token"),
        help="Secure file receiving the refresh token",
    )
    args = parser.parse_args()
    asyncio.run(authenticate(args.output))


if __name__ == "__main__":
    main()
