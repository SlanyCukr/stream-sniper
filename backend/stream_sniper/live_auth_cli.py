"""One-time browser bootstrap for the live chat bot refresh token."""

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope


def _save_token(output: Path, refresh_token: str) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(refresh_token)
    output.chmod(0o600)
    return output.resolve()


async def authenticate(output: Path) -> None:
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET must be set")
    twitch = await Twitch(client_id, client_secret)
    try:
        authenticator = UserAuthenticator(twitch, [AuthScope.CHAT_READ])
        _, refresh_token = await authenticator.authenticate()
        saved_to = await asyncio.to_thread(_save_token, output, refresh_token)
        print(f"Refresh token saved to {saved_to} with mode 0600")
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
