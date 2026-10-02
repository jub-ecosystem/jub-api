"""
02 — Authentication
===================

`JubClientBuilder(...).build()` logs in (POST /users/auth) and returns a
`Result`: `Ok(client)` holding the JWT issued by Xolo, or `Err(exception)`.
Every call made with that client is authenticated automatically.

Run (as invitado by default, see .env.examples):
    python examples/client/02_authentication.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from jub.client.v2 import JubClientBuilder

load_dotenv(Path(__file__).resolve().parent / ".env.examples")

API_URL  = os.environ.get("JUB_API_URL", "http://localhost:5000")
USERNAME = os.environ["JUB_USERNAME"]
PASSWORD = os.environ["JUB_PASSWORD"]


async def main() -> None:
    # 1. Correct credentials → Ok(client)
    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()

    me = (await client.get_current_user()).unwrap()
    print(f"Logged in as {me.username} ({me.user_id})")

    # 2. Wrong password → Err(...). build() never raises: check the Result.
    result = await JubClientBuilder(API_URL, USERNAME, "wrong-password").build()
    if result.is_err:
        print(f"Wrong password rejected: {result.unwrap_err()}")


if __name__ == "__main__":
    asyncio.run(main())
