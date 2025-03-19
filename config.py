# Target site URL for the load test
HOST_URL = "https://17619-test.preview.onebrief.com"

# Supervisor user credentials. These are the credentials used for creating a shared plan in which spawned Locust users will navigate to and interact with.
SUPERVISOR_USERNAME = "****"
SUPERVISOR_PASSWORD = "****"

# Additional user Ids to be added to the plan. It is recommended you add your User ID to this list so that you can login and observe the test as it unfolds. To get your ID in the browser JavaScript console, do this:
# (await dev_clientApi.retrieveUser()).data.id
ADDITIONAL_USER_IDS = []

# Timeout settings in milliseconds
ASSERTION_TIMEOUT = 10000  # Timeout for assertions
NAVIGATION_TIMEOUT = 20000  # Timeout for navigating between pages

# Playwright browser options. Note: Minimum browser width MUST be 1400px or greater in order for the leftnav to be unpinned.
DEFAULT_BROWSER_OPTIONS = {
    "viewport": {"width": 1400, "height": 768},
    "permissions": ["clipboard-read", "clipboard-write"],
}
