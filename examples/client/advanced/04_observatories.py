"""
04 — Observatories
==================

An observatory is the page end users browse: it groups catalogs (05),
products (06), data sources (10) and services (11).

There are two ways to create one:

    setup_observatory()    creates it DISABLED and opens a setup task. You index
                           catalogs/products/data while nobody can see it, then
                           call complete_task(success=True) to publish it.
                           → recommended for real provisioning (12 completes it)

    create_observatory()   creates it ENABLED right away.
                           → fine for quick tests; used here for a second
                             observatory that 05 and 06 share things with.

Run:
    python examples/client/advanced/04_observatories.py
"""

import asyncio

import jub.dto.v2 as DTO

from _common import SUFFIX, build_client, require, save_state, unwrap


async def main() -> None:
    client = await build_client()
    suffix = SUFFIX

    # ── 1. Main observatory: disabled until its setup task is completed ────
    setup = unwrap(
        await client.setup_observatory(DTO.ObservatorySetupDTO(
            observatory_id = f"obs_mortalidad_{suffix}",
            title          = f"Observatorio de Mortalidad — Mexico ({suffix})",
            description    = (
                "Principales causas de muerte en Mexico, su distribucion geografica "
                "y temporal. Fuente: Certificados de Defuncion SINAVE-DGIS."
            ),
            metadata       = {"fuente": "SINAVE-DGIS", "pais": "MX"},
        )),
        "setup observatory",
    )
    task = unwrap(await client.get_task(setup.task_id), "get setup task")
    print("✓ [setup_observatory]  created disabled")
    print(f"  observatory_id : {setup.observatory_id}")
    print(f"  setup task     : {setup.task_id} ({task.current_status}) — completed in 12_review_observatory.py")

    # ── 2. Secondary observatory: enabled immediately ──────────────────────
    secondary = unwrap(
        await client.create_observatory(DTO.ObservatoryCreateDTO(
            observatory_id = f"obs_cancer_{suffix}",
            title          = f"Observatorio de Cancer — Mexico ({suffix})",
            description    = "Incidencia y mortalidad por cancer en Mexico (CIE-10).",
        )),
        "create observatory",
    )
    print("✓ [create_observatory] created enabled")
    print(f"  observatory_id : {secondary.observatory_id}")

    save_state(
        observatory_id           = setup.observatory_id,
        setup_task_id            = setup.task_id,
        secondary_observatory_id = secondary.observatory_id,
    )

    # ── 3. Read it back ───────────────────────────────────────────────────
    obs = unwrap(await client.get_observatory(setup.observatory_id), "get observatory")
    print(f"\n{obs.title}\n  {obs.description}\n  metadata: {obs.metadata}")


if __name__ == "__main__":
    asyncio.run(main())
