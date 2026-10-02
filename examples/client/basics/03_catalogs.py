"""
03 — Catalogs, items and aliases
================================

Catalogs are the vocabularies used to describe observatories, products and
data. We build them from the car images in source/cars, named
brand_model_color_year (e.g. toyota_corolla_red_2022.jpg):

    CAR_BRAND  INTEREST  TOYOTA → COROLLA, …   (models are children of their brand)
    CAR_COLOR  INTEREST  RED, BLUE, …          (with Spanish aliases: ROJO, AZUL, …)
    CAR_YEAR   TEMPORAL  Y2022, Y2023, …
    COUNTRY    SPATIAL   MX, US, JP, DE, KR    (cars are tagged by brand origin in 08; data source in 10)

Each item has a `value` (used in queries), a numeric `code`, optional
`aliases` (other names for the same item) and optional `children`.

We choose the ids ourselves (`catalog_id`, `catalog_item_id`) so the next
examples can use them without looking them up.

Run:
    python examples/client/basics/03_catalogs.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import jub.dto.v2 as DTO
from jub.client.v2 import JubClientBuilder

load_dotenv(Path(__file__).resolve().parents[1] / ".env.examples")

API_URL  = os.environ.get("JUB_API_URL", "http://localhost:5000")
USERNAME = os.environ.get("JUB_USERNAME","invitado")
PASSWORD = os.environ.get("JUB_PASSWORD", "invitado")
CARS_DIR = Path(__file__).resolve().parents[3] / "source" / "cars"

COLOR_ALIASES = {
    "RED": "ROJO", "BLUE": "AZUL", "BLACK": "NEGRO", "WHITE": "BLANCO", "SILVER": "PLATA",
    "GRAY": "GRIS", "GREY": "GRIS", "GREEN": "VERDE", "YELLOW": "AMARILLO", "ORANGE": "NARANJA",
}
COUNTRIES = {"MX": "Mexico", "US": "United States", "JP": "Japan", "DE": "Germany", "KR": "South Korea"}


def item_id(value: str) -> str:
    return f"{value}_{USERNAME}"


def parse(image: Path) -> tuple[str, str, str, int]:
    """toyota_corolla_red_2022.jpg → ("TOYOTA", "COROLLA", "RED", 2022)"""
    brand, model, color, year = (part.upper().replace("-", "_") for part in image.stem.split("_"))
    return brand, model, color, int(year)


def item(value: str, code: int, name: str = "", **extra) -> DTO.CatalogItemCreateDTO:
    return DTO.CatalogItemCreateDTO(
        catalog_item_id = item_id(value),
        name            = name or value.replace("_", " ").title(),
        value           = value,
        code            = code,
        value_type      = "STRING",
        **extra,
    )


async def main() -> None:
    images = sorted(p for p in CARS_DIR.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".avif"})
    bad = [p.name for p in images if len(p.stem.split("_")) != 4 or not p.stem.split("_")[3].isdigit()]
    if not images or bad:
        sys.exit(f"Expected images named brand_model_color_year in {CARS_DIR}. Wrong names: {bad or 'no images'}")

    cars = [parse(image) for image in images]
    brands = sorted({brand for brand, _, _, _ in cars})
    colors = sorted({color for _, _, color, _ in cars})
    years  = sorted({year for _, _, _, year in cars})

    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()

    # ── Brands, with their models as children ────────────────────────────
    brand_items = []
    for code, brand in enumerate(brands, start=1):
        models = sorted({model for b, model, _, _ in cars if b == brand})
        children = [item(model, code * 100 + i) for i, model in enumerate(models, start=1)]
        brand_items.append(item(brand, code, children=children))

    await client.create_catalog(DTO.CatalogCreateDTO(
        catalog_id   = f"brands_{USERNAME}",
        name         = "Car brands",
        value        = "CAR_BRAND",
        catalog_type = "INTEREST",
        items        = brand_items,
    ))

    # ── Colors, with an alias in Spanish ─────────────────────────────────
    color_items = []
    for code, color in enumerate(colors, start=1):
        aliases = []
        if color in COLOR_ALIASES:
            aliases.append(DTO.CatalogItemAliasCreateDTO(value=COLOR_ALIASES[color], value_type="STRING", description="Spanish"))
        color_items.append(item(color, code, aliases=aliases))

    await client.create_catalog(DTO.CatalogCreateDTO(
        catalog_id   = f"colors_{USERNAME}",
        name         = "Car colors",
        value        = "CAR_COLOR",
        catalog_type = "INTEREST",
        items        = color_items,
    ))

    # ── Years: temporal items carry a date ───────────────────────────────
    await client.create_catalog(DTO.CatalogCreateDTO(
        catalog_id   = f"years_{USERNAME}",
        name         = "Model years",
        value        = "CAR_YEAR",
        catalog_type = "TEMPORAL",
        items        = [
            DTO.CatalogItemCreateDTO(
                catalog_item_id = item_id(f"Y{year}"),
                name            = str(year),
                value           = f"Y{year}",
                code            = year,
                value_type      = "DATETIME",
                temporal_value  = f"{year}-01-01T00:00:00Z",
            )
            for year in years
        ],
    ))

    # ── Countries ────────────────────────────────────────────────────────
    await client.create_catalog(DTO.CatalogCreateDTO(
        catalog_id   = f"countries_{USERNAME}",
        name         = "Countries",
        value        = "COUNTRY",
        catalog_type = "SPATIAL",
        items        = [item(code, i, name) for i, (code, name) in enumerate(COUNTRIES.items(), start=1)],
    ))

    # ── Adding an item and an alias to an existing catalog ───────────────
    await client.create_catalog_item(DTO.CatalogItemStandaloneCreateDTO(
        catalog_id      = f"colors_{USERNAME}",
        catalog_item_id = item_id("GOLD"),
        name            = "Gold",
        value           = "GOLD",
        code            = 99,
        value_type      = "STRING",
    ))
    await client.add_catalog_item_alias(
        item_id("GOLD"),
        DTO.CatalogItemAliasCreateDTO(value="DORADO", value_type="STRING", description="Spanish"),
    )

    # ── Result ───────────────────────────────────────────────────────────
    for catalog_id in (f"brands_{USERNAME}", f"colors_{USERNAME}", f"years_{USERNAME}", f"countries_{USERNAME}"):
        catalog = (await client.get_catalog(catalog_id)).unwrap()
        print(f"{catalog.value:<10} {catalog.catalog_type:<9} {len(catalog.items):>2} items  ({catalog_id})")
        for it in catalog.items:
            aliases  = f"  aliases: {', '.join(a.value for a in it.aliases)}" if it.aliases else ""
            children = f"  children: {', '.join(c.value for c in it.children)}" if it.children else ""
            print(f"    {it.value}{aliases}{children}")


if __name__ == "__main__":
    asyncio.run(main())
