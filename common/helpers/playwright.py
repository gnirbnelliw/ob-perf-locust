import random
from playwright.async_api import Page, expect
import re
from common.helpers.global_selectors import *
from config import SUPERVISOR_USERNAME, SUPERVISOR_PASSWORD
import time
import logging
from faker import Faker
import asyncio
from config import *

fake = Faker()

# Configure logging to append to the Locust log file
logging.basicConfig(
    filename="load_test.log",  # Locust log file
    level=logging.INFO,  # you can change this to DEBUG, ERROR, etc.
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)


async def resize_browser(page: Page):
    await page.set_viewport_size({"width": 1400, "height": 768})


async def login_supervisor(page: Page):
    logged_in = await is_logged_in(page)
    if logged_in:
        return

    logging.info("🇺🇸 Logging in the supervisor...")
    await login(page, SUPERVISOR_USERNAME, SUPERVISOR_PASSWORD)
    logging.info("🇺🇸 Supervisor logged in...")


def get_ts_string():
    return str(int(time.time() * 1000))[-6:]


def get_performance_user_credentials():
    """Returns unique performance user credentials"""
    # Generate a unique standard-length number string from time.time()
    slug = get_ts_string()
    name = "Performance User"
    return {
        "email": f"perf-user-{slug}@onebrief.com",
        "username": f"perf-user-{slug}",
        "password": SUPERVISOR_PASSWORD,
        "first-name": name.split()[0],
        "last-name": f"{name.split()[1]} {slug}",
        "rank": "E-5",
        "job-title": "Quality",
        "organization": "Quality",
        "parent-organization": "Onebrief",
    }


async def register_user(page: Page, screenshot: bool = False):
    # Get credentials
    creds = get_performance_user_credentials()

    uname = creds["username"]

    logging.info(
        f"🍔 Registering user with username: {creds['username']} and email {creds['email']}..."
    )

    # Navigate to login form
    await page.goto(f"{HOST_URL}/login")
    await page.get_by_test_id("sign-up").click()
    logging.info(f"🍔 {uname} is on registration page...")

    # Iterate over the credentials, which is a dictionary
    for field, value in creds.items():  # Use items() to get both key and value
        input = page.get_by_test_id(field)
        await expect(input).to_be_visible(timeout=10000)
        await input.fill(value)  # Fill the input with the value from creds

        # If the field is "password", fill the confirm password field as well
        if field == "password":
            await page.get_by_test_id("confirm-password").fill(value)

    # Check the accept terms box
    await page.get_by_test_id("terms").check()

    logging.info(f"🍔 {uname} is about to check the terms...")

    # Ensure that the register button is enabled
    register_btn = page.get_by_test_id("submit-registration")
    await expect(register_btn).to_be_enabled(timeout=10000)
    await register_btn.click()

    # Assert the page url does not contain /login
    await expect(page).not_to_have_url(
        re.compile(r".*/login"), timeout=NAVIGATION_TIMEOUT
    )

    logging.info(f"🍔 {uname} is waiting for page to fully load...")
    await wait_for_page_to_fully_load(page)
    logging.info(f"🍔 {uname} has a fully loaded page...")

    logging.info(f"🍔 {uname} is navigating to the home page...")

    # Get the user data and add it to creds
    user_data = await get_user_data(page)
    if user_data:
        creds["user_data"] = user_data

    # Return the user data
    logging.info(f"🍔 Returning creds...")
    return creds


async def login(page: Page, username: str, password: str):
    await page.goto(f"{HOST_URL}/login")
    # Simulate login using the first user (or a default admin user)
    await page.fill("input[name='username']", username)
    await page.fill("input[name='password']", password)
    await page.click("button[type='submit']")

    # Insert expect here that waits for the locator
    await expect(get_user_avatar(page)).to_be_visible(timeout=10000)

    # Wait for successful login (adjust according to your app)
    await wait_for_page_to_fully_load(page)


async def poll_expect(fn, timeout=5000, interval=500):
    """Polls a given function until it returns True or timeout is reached."""
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
        if await fn():
            return True
        await asyncio.sleep(interval / 1000)

    raise TimeoutError(f"Condition not met within {timeout}ms")


async def no_spinners_visible(page: Page) -> bool:
    """Checks if there are no spinners visible"""
    spinners = await page.locator('[data-testid*="spinner"]:visible').count()
    return spinners == 0


async def page_load_state_complete(page: Page) -> bool:
    complete = await page.evaluate("document.readyState") == "complete"
    return complete


async def user_avatar_visible(page: Page) -> bool:
    """Checks if the user avatar is visible"""
    return await get_user_avatar(page).is_visible()


async def wait_for_page_to_fully_load(page: Page):
    """Waits for the page to fully load"""
    # Barebones... not even domcontentloaded (which doesn't always fire)
    long_timeout = 60000

    try:
        await poll_expect(lambda: no_spinners_visible(page), timeout=long_timeout)
        await poll_expect(lambda: page_load_state_complete(page), timeout=long_timeout)
        await poll_expect(lambda: user_avatar_visible(page), timeout=long_timeout)

    except Exception as e:
        logging.error(f"Error waiting for page to load: {e}")
        raise  # 🔥 Do not silently return False


async def get_user_data(page: Page, attempts: int = 0):
    """Checks if the user is logged in"""
    # Create an api call to /api/auth/profile
    try:
        response = await page.request.get(f"{HOST_URL}/api/auth/profile")
        data = await response.json()
        # If data is an object containing "id" return it
        if isinstance(data, dict) and "id" in data:
            return data
        else:
            return None
    except Exception as e:
        return None


async def is_logged_in(page: Page):
    """Checks if the user is logged in"""
    user_data = await get_user_data(page)
    if user_data:
        return True
    else:
        return False


async def create_plan(page: Page, plan_name: str, screenshot: bool = False):
    """Creates a plan and returns the plan url"""
    # Directly access new plan creation url
    await page.goto(f"{HOST_URL}/new")
    await get_create_new_plan_btn(page).click()
    await get_new_plan_input(page).fill(plan_name)

    # Click 2nd create button
    await get_create_new_plan_btn2(page).click()
    # Ensure you are on the dashboard
    # Set the expect timeout to 20 seconds
    await page.wait_for_url(
        re.compile(r".*/dashboard"), timeout=NAVIGATION_TIMEOUT
    )
    # await expect(page).to_have_url(re.compile(r".*/dashboard"))
    await wait_for_page_to_fully_load(page)

    # Screenshot
    if screenshot:
        await page.screenshot(path=f"screenshot_supervisor.png")

    return page.url


def get_allowable_artifacts():
    return ["Document", "C2", "Cause and effect", "List board", "Map"]


async def create_special_order(page: Page) -> str:
    """Creates a shared order and returns the url"""
    url = await create_artifact(page, "Document", "Shared Order")
    return url


def get_random_text():
    # Use faker to generate random text
    return fake.sentence()


def rand_between(min, max):
    return random.randint(min, max)


async def edit_order(page: Page, screenshot: bool = False):
    """Edits current order"""
    order_editor = page.get_by_test_id("order-editor")
    await expect(order_editor).to_be_visible(timeout=10000)
    # Get the total count of the paragraphs
    paragraphs = await order_editor.locator('[data-testid="typed-content"]').all()
    # Get a random one
    random_paragraph = random.choice(paragraphs)
    await random_paragraph.dblclick()
    # Get the prosemirror editor
    pm = get_prosemirror_editor(page)
    u = await get_user_data(page)
    username = u.get("name", "unknown")
    id = u.get("id", "?")
    random_text = f"{username} [id={id}] — {get_random_text()}"
    ts = get_ts_string()
    logging.info(f"😜 {ts} => {random_text}")
    # Get a random number between 5 and 50
    delay = float(random.randint(25, 75))
    await pm.press_sequentially(random_text, delay=delay)
    await page.wait_for_timeout(1000)
    await page.keyboard.press("Enter")
    # Wait for a random amount
    await page.wait_for_timeout(rand_between(1000, 4000))
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(1000)
    if screenshot:
        await page.screenshot(path=f"order-{ts}.png")


async def create_artifact(page: Page, artifact_type: str, artifact_title: str = None):
    if artifact_type not in get_allowable_artifacts():
        raise ValueError(f"Invalid artifact type: {artifact_type}")
    # Get user data
    user = await get_user_data(page)

    # Leftnav => Plus button => {Artifact}
    await get_leftnav_get_started_button(page).click()
    await page.get_by_role("menuitem").locator(
        f"[data-testid='dropdown-item']:text('{artifact_type}')"
    ).click()
    await page.get_by_test_id("create-new-artifact-button").click()

    # Default name?
    if not artifact_title:
        ts = get_ts_string()
        page_title = f"{artifact_type} - [user {user["id"]}] - {time.time()}"
    else:
        page_title = artifact_title

    # Now title the page
    await title_page(page, artifact_title)
    # Assume that the title is now set
    return page.url


async def create_random_artifact(page: Page):
    """Creates a random artifact"""
    # Get random artifact
    artifact = random.choice(get_allowable_artifacts())
    url = await create_artifact(page, artifact)
    return url


async def link_user_to_plan_api(page: Page, user_id: int, plan_id: int):
    """Dispatches a PUT request to link a user to the shared plan via API."""

    api_url = f"{HOST_URL}/api/brief/{plan_id}/access/user/{user_id}/editor"
    logging.info(f"🐝 Making PUT request to {api_url}")

    try:
        # Get cookies and format them as a header string
        cookies = await page.context.cookies()
        cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Length": "0",  # Required for PUT requests
            "Cookie": cookie_header,
        }

        response = await page.request.put(api_url, headers=headers)

        logging.info(f"📡 Response Status: {response.status}")
        logging.info(f"📡 Response Headers: {response.headers}")

        # ✅ Handle empty response
        response_text = await response.text()
        if not response_text.strip():
            logging.info(
                f"✅ Successfully linked {user_id} to plan {plan_id}. (No response body)"
            )
            return None  # Nothing to parse, exit function

        # ✅ Attempt to parse JSON if body exists
        try:
            response_data = await response.json()
            logging.info(
                f"✅ Successfully linked {user_id} to plan {plan_id}: {response_data}"
            )
        except Exception:
            logging.info(
                f"✅ Successfully linked {user_id} to plan {plan_id}. (Non-JSON response: {response_text})"
            )

    except Exception as e:
        logging.error(f"❌ Error linking user {user_id}: {e}")


def get_plan_id_from_url(url: str) -> int:
    """Extracts the last numeric sequence from a URL and returns it as an int."""
    match = re.search(r"(\d+)(?!.*\d)", url)  # Finds the last numeric sequence
    if match:
        return int(match.group(1))
    raise ValueError(f"No numeric plan ID found in URL: {url}")


async def invoke_planning_team_modal(page: Page):
    """Invokes the planning team modal"""
    # Planning Dropdwon => Planning team
    await get_plan_dropdown_btn(page).click()
    await page.locator(f'[data-testid="dropdown-item"]:text("Planning team")').click()
    # Assert the modal is visible
    await expect(page.get_by_role("dialog")).to_be_visible(timeout=10000)


async def link_users_to_plan(page: Page, users: list[str], keep_open: bool = False):
    """Links multiple users to plans"""
    try:
        await invoke_planning_team_modal(page)

        # Loop over users
        for user in users:
            # Get index of this user
            idx = users.index(user) + 1
            dismiss = idx == len(users)
            await link_user_to_current_plan(page, user, dismiss)

        # Dismiss the modal
        if not keep_open:
            await page.get_by_role("dialog").locator('button:text("Dismiss")').click()

    except Exception as e:
        logging.error(f"Error linking users to plan: {e}")


async def link_user_to_current_plan(page: Page, email: str, dismiss: bool = False):
    """Links the other users to the plan"""
    # Add member button locator
    add_member_btn = page.get_by_role("dialog").locator(
        'button:enabled *:text("Add member")'
    )

    # Wait for add member btn to be visible
    await expect(add_member_btn).to_be_visible(timeout=10000)
    await add_member_btn.click()
    # Search for user and press enter
    await page.keyboard.type(email)

    # Wait for an xhr request to /api/accounts?q=
    page.expect_request_finished(
        lambda request: f"/api/accounts?q=" in request.url, timeout=10000
    )

    # TODO: Add action to specify permission role (editor | admin | read only)

    # Select the user from the dropdown
    await page.get_by_text(f"- {email}").click()

    # Click add member to finalize selection
    await add_member_btn.click()

    # Wait until the newly added user is there
    new_entry = page.locator(f'[data-testid="account-details"]:text("{email}")')
    await page.wait_for_timeout(1000)
    await expect(new_entry).to_be_attached(timeout=10000)

    # Screenshot
    # await page.screenshot(path=f"link-user-{email}.png")

    if dismiss:
        # Click dismiss
        await page.get_by_role("dialog").locator('button *:text("Dismiss")').click()
        await expect(page.get_by_role("dialog")).to_be_hidden(timeout=5000)


async def invoke_user_profile_dialog(page: Page, stow: bool = False):
    """Invokes the user profile dialog"""
    await get_user_avatar(page).click()
    # Click the Profile menu item
    menu_item = get_menu_item_by_text(page, "Profile")
    await menu_item.click()
    # Assert the User Profile modal is visible
    modal = get_profile_modal(page)
    await expect(modal).to_be_attached(timeout=10000)
    # Make sure the user profile dialog is actually visible
    await expect(
        modal.locator('[data-testid="modal-title"]:text("Profile")')
    ).to_be_visible(timeout=ASSERTION_TIMEOUT)

    if stow:
        # Dismiss the dialog
        await page.get_by_test_id("modal-dismiss").click()


async def dismiss_card_library(page: Page):
    await page.get_by_test_id("close-rfw-card-library-window").click()
    card_library = get_card_library_window(page)
    await expect(card_library).to_be_hidden(timeout=ASSERTION_TIMEOUT)


async def create_cards_in_card_library(page: Page, totalCards: int = 10):
    # Expand the card library
    card_library_btn = get_card_library_btn(page)
    await card_library_btn.click()
    card_library = get_card_library_window(page)
    # Expect the card library to be visible
    await expect(card_library).to_be_visible(timeout=NAVIGATION_TIMEOUT)

    # Selectors
    plus_btn = card_library.get_by_test_id("btn-add-card-floating")
    floating_form = page.get_by_test_id("add-card-floating-form")
    # editor_body = page.get_by_test_id("editor-body")
    editor_body = floating_form.get_by_test_id("editor-body")
    active_editor = get_prosemirror_editor(page)

    # Click + button once
    await plus_btn.click()
    await expect(floating_form).to_be_visible(timeout=NAVIGATION_TIMEOUT)

    # Loop over totalCards times
    for i in range(totalCards):
        # Create a random card
        card_text = get_random_text()
        # Wait for a random amount of time
        # await page.wait_for_timeout(rand_between(100, 500))

        # Click into the editor body and type
        await floating_form.get_by_test_id("editor-body").click()
        await expect(active_editor).to_be_attached(timeout=ACTION_TIMEOUT)
        await active_editor.press_sequentially(card_text)

        # Wait until the active editor contains the text
        await expect(editor_body.locator("p")).to_contain_text(card_text)
        await floating_form.locator('button[type="submit"]').click()
        # Wait until the editor no longer has the copy
        await expect(editor_body.locator("p")).not_to_contain_text(card_text)
        await page.wait_for_timeout(rand_between(100, 500))

    # Now, dismiss the card library
    await dismiss_card_library(page)


async def title_page(page: Page, page_title: str):
    """Titles a page"""

    title = page.get_by_test_id("page-title")
    await title.dblclick()

    editor = get_prosemirror_editor(page)
    await expect(editor).to_be_focused(timeout=10000)

    await title.clear()
    await title.fill(page_title, force=True)
    await page.keyboard.down("Enter")
    await asyncio.sleep(0.5)
    await expect(title.locator("*")).to_contain_text(page_title, timeout=10000)

    # Wait until the leftnav contains an item with that very name
    leftnav_link = get_leftnav(page).locator(
        f'[data-testid="artifact-link"][title="{page_title}"]'
    )
    await expect(leftnav_link).to_be_visible(timeout=10000)
    # Note: Clicking here is a means to blur the goddamn prosemirror editor
    await get_user_avatar(page).click()
    # Wait until the title no longer has focus
    await expect(title).not_to_be_focused(timeout=10000)
