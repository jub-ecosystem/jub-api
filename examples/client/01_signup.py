"""
01 — Sign up
============

Creates a new user with a random username and password.

Signup is the only operation that does not need a token, so we use a plain
`JubClient` (username and password empty) instead of `JubClientBuilder`,
which always logs in.

The other examples log in as JUB_USERNAME / JUB_PASSWORD, which default to
invitado / invitado (.env.examples). To use this new user instead, run the
`export` line this script prints — shell variables override .env.examples.

Run:
    python examples/client/01_signup.py
"""

import asyncio
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
import jub.dto.v2 as DTO
from jub.client.v2 import JubClient

load_dotenv(Path(__file__).resolve().parent / ".env.examples")

API_URL = os.environ.get("JUB_API_URL", "http://localhost:5000")


async def main() -> None:
    username = f"demo_{uuid.uuid4().hex[:6]}"
    password = uuid.uuid4().hex

    client = JubClient(API_URL, username="", password="")
    result = await client.signup(DTO.SignUpDTO(
        username   = username,
        email      = f"{username}@example.com",
        password   = password,
        first_name = "Demo",
        last_name  = "User",
        scope      = "jub",   # must exist in Xolo (see create_scope.sh)
    ))
    profile = result.unwrap()

    print(f"User created: {profile.username} ({profile.user_id})")
    print("\nUse it in the next examples:\n")
    print(f"export JUB_USERNAME={username} JUB_PASSWORD={password}")


if __name__ == "__main__":
    asyncio.run(main())
