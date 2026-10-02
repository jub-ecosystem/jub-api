"""
12 — Review the observatory (and publish it)
============================================

Collects everything the previous steps attached to the observatory:

    get_observatory()               details + snapshots of services/data sources + rating
    get_observatories_stats()       the same stats for several observatories at once
    list_observatory_catalogs()     05
    list_observatory_products()     06 (+ get_product_tags per product, 08)
    list_observatory_datasources()  10
    list_observatory_services()     11
    list_my_tasks()                 setup task (04) and upload tasks (07, 09)

The observatory was created disabled by setup_observatory() in 04. If the
checklist passes, this script completes the setup task with
complete_task(success=True), which enables the observatory for end users.

Run:
    python examples/client/advanced/12_review_observatory.py
    python examples/client/advanced/12_review_observatory.py --no-publish   # review only
"""

import argparse
import asyncio

import jub.dto.v2 as DTO

from _common import build_client, require, unwrap


def section(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, 60 - len(title)))


async def main(args: argparse.Namespace) -> None:
    client        = await build_client()
    obs_id        = require("observatory_id", "04_observatories.py")
    secondary_id  = require("secondary_observatory_id", "04_observatories.py")
    setup_task_id = require("setup_task_id", "04_observatories.py")

    obs = unwrap(await client.get_observatory(obs_id), "get observatory")
    print(f"{obs.title}\n{obs.observatory_id}\n{obs.description}")
    print(f"metadata {obs.metadata}  ·  rating {obs.avg_rating:.1f} ({obs.review_count} reviews)")

    # ── Catalogs ─────────────────────────────────────────────────────────
    catalogs = unwrap(await client.list_observatory_catalogs(obs_id), "list catalogs")
    section(f"Catalogs ({len(catalogs)})")
    for c in sorted(catalogs, key=lambda c: c.level):
        print(f"  level {c.level}  {c.catalog_type:<8}  {c.name}")

    # ── Products ─────────────────────────────────────────────────────────
    products = unwrap(await client.list_observatory_products(obs_id), "list products")
    section(f"Products ({len(products)})")
    untagged = []
    for p in products:
        tags = unwrap(await client.get_product_tags(p.product_id), f"get tags of {p.product_id}")
        if not tags.catalog_item_ids:
            untagged.append(p.product_id)
        print(f"  {p.product_id}  {p.name:<45} {len(tags.catalog_item_ids):>3} tags")

    # ── Data sources & services ──────────────────────────────────────────
    sources = unwrap(await client.list_observatory_datasources(obs_id), "list data sources")
    section(f"Data sources ({len(sources)})")
    for s in sources:
        print(f"  {s.source_id}  {s.name}  [{s.format}]")

    services = unwrap(await client.list_observatory_services(obs_id), "list services")
    section(f"Services ({len(services)})")
    for s in services:
        print(f"  {s.service_id}  {s.name:<28} provider={s.provider}")

    # ── Tasks ────────────────────────────────────────────────────────────
    tasks = [t for t in unwrap(await client.list_my_tasks(limit=100), "list tasks") if t.observatory_id == obs_id]
    section(f"Tasks ({len(tasks)})")
    for t in tasks:
        print(f"  {t.task_id}  {t.operation:<6} {t.current_status:<8} {t.title}")

    # ── Both observatories side by side ──────────────────────────────────
    section("Stats")
    for st in unwrap(await client.get_observatories_stats([obs_id, secondary_id]), "get stats"):
        print(f"  {st.observatory_id:<28} services={len(st.services)}  data_sources={len(st.data_sources)}  rating={st.avg_rating:.1f}")

    # ── Checklist → publish ──────────────────────────────────────────────
    checks = {
        "has catalogs":              bool(catalogs),
        "has products":              bool(products),
        "every product is tagged":   not untagged,
        "has a data source":         bool(sources),
    }
    section("Checklist")
    for name, ok in checks.items():
        print(f"  {'✓' if ok else '✗'} {name}")
    if untagged:
        print(f"    untagged: {', '.join(untagged)}")

    setup_task = unwrap(await client.get_task(setup_task_id), "get setup task")
    if setup_task.current_status != "pending":
        print(f"\nSetup task already {setup_task.current_status} — nothing to publish.")
        return
    if args.no_publish or not all(checks.values()):
        print("\nObservatory left disabled (setup task still pending).")
        return

    done = unwrap(
        await client.complete_task(setup_task_id, DTO.TaskCompleteDTO(success=True, message="Reviewed by 12_review_observatory.py")),
        "complete setup task",
    )
    print(f"\n✓ [complete_task] {done.task_id} → {done.status}, observatory enabled: {done.observatory_enabled}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-publish", action="store_true", help="review only, do not complete the setup task")
    asyncio.run(main(parser.parse_args()))
