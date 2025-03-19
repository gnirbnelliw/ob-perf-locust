from playwright.async_api import Page


# Define global selectors as functions or variables
def get_user_avatar(page: Page):
    """Circle icon that represents the user in top right header"""
    return page.get_by_test_id("btn-user-avatar")


def get_create_new_plan_btn(page: Page):
    """Button to create a new plan"""
    return page.get_by_test_id("create-new-plan-button")


def get_create_new_plan_btn2(page: Page):
    """Second button to create a new plan"""
    return page.get_by_test_id("new-plan-create")


def get_new_plan_input(page: Page):
    return page.get_by_test_id("new-plan-input")


def get_plan_dropdown_btn(page: Page):
    """Button in top leftnav that reveals plan functionality."""
    return page.get_by_test_id("plan-dropdown-button")


def get_leftnav(page: Page):
    return page.get_by_test_id("leftnav")


def get_leftnav_get_started_button(page: Page):
    return get_leftnav(page).get_by_test_id("get-started").first


def get_new_artifact_btn(page: Page):
    return page.get_by_test_id("create-new-artifact-button")


def get_prosemirror_editor(page: Page):
    return page.locator('[contenteditable="true"].ProseMirror-focused')


def get_profile_modal(page: Page):
    return page.locator(
        '[role="dialog"]:has([data-testid="modal-title"]:text("Profile"))'
    )


def get_menu_item_by_text(page: Page, menu_text: str):
    return page.get_by_role("menuitem").get_by_text(menu_text)


def get_card_library_btn(page: Page):
    return page.get_by_test_id("btn-card-library")


def get_card_library_window(page: Page):
    return page.get_by_test_id("card-library-window")
