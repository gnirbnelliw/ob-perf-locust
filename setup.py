import json
import asyncio
import logging
from playwright.async_api import async_playwright
from common.helpers.playwright import *
from config import *

SUPERVISOR_COOKIES_FILE = "supervisor_cookies.json"

# Configure logging
logging.basicConfig(
    filename="supervisor_setup.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def supervisor_setup():
    """Handles supervisor login and batch user registration."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        supervisor_page = await browser.new_page(**DEFAULT_BROWSER_OPTIONS)

        logging.info("🚀 Logging in as Supervisor...")
        await login_supervisor(supervisor_page)

        # Persist this data in a JSON file
        supervisor_user = await get_user_data(supervisor_page)

        # Clock how long it takes to create a blank plan
        t1 = time.time()
        shared_plan_url = await create_plan(supervisor_page, f"TP - {get_ts_string()}")
        t2 = time.time()
        time_to_create_plan = t2 - t1
        logging.info(f"Plan created in {time_to_create_plan:.2f} seconds")

        shared_order_url = await create_special_order(supervisor_page)

        await title_page(supervisor_page, "Shared Order")

        # Also persist the cookies for later use in Locust
        auth_cookies = await supervisor_page.context.cookies()
        supervisor_data = {
            "shared_plan_url": shared_plan_url,
            "time_to_create_plan": f"{time_to_create_plan:.2f} seconds",
            "shared_order_url": shared_order_url,
            "auth_cookies": auth_cookies,
            "supervisor_user": supervisor_user,
        }

        with open(SUPERVISOR_COOKIES_FILE, "w") as f:
            json.dump(supervisor_data, f, indent=2)

        # Lastly link the ADDITIONAL_USER_IDS to the plan
        plan_id = get_plan_id_from_url(shared_plan_url)
        for user_id in ADDITIONAL_USER_IDS:
            await link_user_to_plan_api(supervisor_page, user_id, plan_id)

        logging.info(f"✅ Supervisor setup complete. Shared plan: {shared_plan_url}")


if __name__ == "__main__":
    asyncio.run(supervisor_setup())
