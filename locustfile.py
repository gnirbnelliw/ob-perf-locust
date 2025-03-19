import json
import asyncio
import logging
from locust import task, between, events, run_single_user
from locust_plugins.users.playwright import PageWithRetry, PlaywrightUser, pw, event
from common.helpers.playwright import *
from config import *

SUPERVISOR_COOKIES_FILE = "supervisor_cookies.json"

# Configure logging
logging.basicConfig(
    filename="load_test.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# **Global Variables for Shared Supervisor Data**
shared_plan_url = None
shared_order_url = None
supervisor_cookies = None
supervisor_page = None  # ✅ Persistent supervisor page
setup_complete = asyncio.Event()  # ✅ Blocks tasks until setup is complete


@events.test_start.add_listener
def load_supervisor_data(environment, **kwargs):
    """Reads supervisor cookies & URLs from file before Locust users start."""
    global shared_plan_url, shared_order_url, supervisor_cookies

    logging.info("🔍 Loading supervisor setup data from JSON...")
    try:
        with open(SUPERVISOR_COOKIES_FILE, "r") as f:
            data = json.load(f)

        shared_plan_url = data["shared_plan_url"]
        shared_order_url = data["shared_order_url"]
        supervisor_cookies = data["auth_cookies"]

        logging.info(f"✅ Supervisor setup loaded: {shared_plan_url}")
        setup_complete.set()  # ✅ Unblocks tasks that depend on this data

    except Exception as e:
        logging.error(f"❌ Failed to load supervisor setup: {e}")
        raise SystemExit("Exiting due to missing supervisor setup.")


class Onebrief(PlaywrightUser):
    """Main Locust user class that simulates registered users."""

    wait_time = between(5, 10)
    host = HOST_URL

    def __init__(self, environment):
        super().__init__(environment)
        self.startup_event = asyncio.Event()

        # Ensure shared data exists
        if not hasattr(self.environment, "shared_data"):
            self.environment.shared_data = {
                "shared_plan_url": shared_plan_url,
                "shared_order_url": shared_order_url,
                "supervisor_cookies": supervisor_cookies,
                "pages": [],
                "registered_users": [],
            }

    async def handle_page_errors(self, page):
        """Attaches error handlers to the given Playwright page."""

        # ✅ Detect failed requests
        page.on(
            "requestfailed",
            lambda request: self.log(f"❌ Request failed: {request.url}"),
        )

        # ✅ Detect HTTP 400+ responses
        async def check_response(response):
            if response.status >= 400:
                self.log(f"🚨 HTTP {response.status} on {response.url}")
                await self.handle_error(response.url, response.status)

        page.on("response", check_response)

    async def handle_error(self, url, status):
        """Handles detected errors by logging and taking necessary actions."""
        self.log(f"🔥 Detected issue! {status} response from {url}")
        # ✅ Add any recovery steps here (e.g., reload page, retry request, etc.)

    async def check_page_for_oops(self, page):
        """Checks if 'Oops' appears anywhere in the page."""
        try:
            await expect(page.locator("body")).not_to_contain_text("Oops", timeout=5000)
        except Exception:
            self.log(f"⚠️ 'Oops' detected on {page.url}")
            await self.handle_error(page.url, "Oops")

    def log(self, msg):
        print(msg)
        logging.info(msg)

    def get_shared_plan_url(self):
        return self.environment.shared_data["shared_plan_url"]

    def get_shared_order_url(self):
        return self.environment.shared_data["shared_order_url"]

    async def resize_browser(self, page):
        """Resize the browser window to a specific size."""
        await page.set_viewport_size({"width": 1400, "height": 800})

    async def get_supervisor_page(self):
        """Creates or retrieves a persistent Playwright page for the supervisor."""
        self.log("🔍 Retrieving supervisor page...")
        global supervisor_page

        if supervisor_page is None:
            self.log("🆕 Creating a persistent supervisor page...")
            context = await self.browser.new_context()
            supervisor_page = await context.new_page()
            await supervisor_page.context.add_cookies(supervisor_cookies)
            self.log("✅ Supervisor page initialized with stored cookies.")
            # Resize
            await self.resize_browser(supervisor_page)
        return supervisor_page

    def get_total_concurrent_user_count(self):
        """Get the total number of concurrent users."""
        count = len(self.environment.shared_data["registered_users"])
        self.log(f"❤️ Total concurrent users: {count}")
        return count

    def get_creation_order(self, u):
        """Get the index # of the user in the registered_users list."""
        try:
            return self.environment.shared_data["registered_users"].index(u) + 1
        except ValueError:
            return -1

    # @pw
    async def link_user_to_shared_plan(self, user_id: int):
        """Links the registered user to the shared plan."""
        supervisor_page = await self.get_supervisor_page()
        self.log(f"🔗 Linking user {user_id} to the shared plan...")

        # Navigate to the shared plan management page
        await supervisor_page.goto(shared_plan_url)
        await wait_for_page_to_fully_load(supervisor_page)

        # Perform linking operation (Replace with actual logic)
        plan_id = get_plan_id_from_url(shared_plan_url)
        await link_user_to_plan_api(supervisor_page, user_id, plan_id)

        self.log(f"✅ User {user_id} linked successfully to Plan {plan_id}.")

    @task
    @pw
    async def register_account(self, page: PageWithRetry):
        """Register for an account and interact with the shared plan."""
        await setup_complete.wait()  # ✅ Ensure supervisor setup is ready

        # Resize
        await self.resize_browser(page)

        self.log("🧨" * 5)
        self.log(self.get_shared_plan_url())
        self.log("🧨" * 5)

        self.log("✅ Onebrief user proceeding!!!")

        async with event(self, "Register new user"):
            u = await register_user(page)
            if not u:
                logging.error(
                    "❌ Failed to register user: register_user() returned None"
                )
                return

            if "id" not in u["user_data"]:
                logging.error(f"❌ Invalid user object: {u}")
                return

            if u:
                self.log("✅ Registered successfully.")

                # Store the user & page object
                self.environment.shared_data["registered_users"].append(u)
                self.environment.shared_data["pages"].append(page)

                user_id = u["user_data"]["id"]

                self.log("-----------------")
                self.log(u)
                self.log("-----------------")
                self.log("☝🏽 Attempting to link {user_id}")

                # Now link this user to the shared plan
                await self.link_user_to_shared_plan(user_id)

                # Now the user is linked to the shared plan
                self.log(f"🚀 Navigating to shared plan: {shared_plan_url}")
                await page.goto(shared_order_url, timeout=60000)
                self.log(f"\t - Waiting for shared plan url to load...")
                await wait_for_page_to_fully_load(page)
                self.log(f"\t - Loaded!!!")

                # If the creation_order is a multiple of 5, retitle the page
                creation_order = self.get_creation_order(u)
                count = self.get_total_concurrent_user_count()
                if creation_order % 5 == 0:
                    await title_page(page, f"Shared Order [{count}] Concurrent Users")

                # Create a dict of function references
                async def f1():
                    for i in range(5):
                        await edit_order(page)

                async def f2():
                    await create_cards_in_card_library(page, rand_between(1, 4))

                async def f3():
                    await create_random_artifact(page)
                    await page.goto(shared_order_url)
                    await wait_for_page_to_fully_load(page)

                async def f4():
                    await title_page(page, f"Shared Order [{count}] Concurrent Users")

                funcs = [f1, f2, f3]

                for i in range(10):
                    # Do 1 random thing...
                    await funcs[rand_between(0, 2)]()

                # Screenshot
                await page.screenshot(path=f"shared-order-{user_id}.png")


if __name__ == "__main__":
    run_single_user(Onebrief)
