"""Main entrypoint for weworkremotely-jobs-scraper Actor."""
import asyncio
import logging
from apify import Actor
try:
    from src.wwr_client import WeWorkRemotelyClient
except ImportError:
    from wwr_client import WeWorkRemotelyClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        max_items = actor_input.get("maxItems", 30)
        kw_filter = actor_input.get("keywordFilter", "")
        cat_filter = actor_input.get("categoryFilter", "")

        Actor.log.info(f"Starting WeWorkRemotely scraper: maxItems={max_items}, keyword='{kw_filter}', category='{cat_filter}'")

        client = WeWorkRemotelyClient()
        jobs = client.fetch_jobs(max_items=max_items, keyword_filter=kw_filter, category_filter=cat_filter)

        if not jobs:
            Actor.log.warning("No jobs extracted from WeWorkRemotely.")
            await Actor.set_value("OUTPUT", {"jobsExtracted": 0})
            return

        try:
            for _ in jobs:
                try:
                    await Actor.charge({"eventName": "job-extracted", "count": 1})
                except Exception:
                    pass
        except Exception:
            pass

        await Actor.push_data(jobs)
        await Actor.set_value("OUTPUT", {
            "jobsExtracted": len(jobs),
            "sampleJob": f"{jobs[0]['position']} @ {jobs[0]['company']}" if jobs else None
        })
        Actor.log.info(f"Successfully pushed {len(jobs)} jobs to dataset.")


if __name__ == "__main__":
    asyncio.run(main())
