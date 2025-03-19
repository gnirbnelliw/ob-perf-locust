# About
Run configuration-based load tests using `Python` and `Locust` in a few simple steps:
1. Install
2. Configure
3. Run
4. Observe
5. Halt
6. Rerun (after halting)


## 1. Install
Set up the Python virtual env. Note: if you've gone through this before, just skip ahead to installing python libraries.

- Create and activate a virtual env

```bash 
python3 -m venv venv
source venv/bin/activate
```

- Install `python` libraries
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

- Install Playwright Chromium browser
```bash
playwright install-deps chromium
```

- Confirm installation
```bash
locust -V       # locust 2.33.1
playwright -V   # Version 1.50.0

```


## 2. Configure
Open up `config.py` and set the following:
```python
# This is the target site
HOST_URL = "https://17619-test.preview.onebrief.com"

# The user that creates the shared plan
SUPERVISOR_USERNAME = "designated-admin-user"
SUPERVISOR_PASSWORD = "super-unguessable-password"

# An array of additional IDs — they will be added to the plan in the setup.
ADDITIONAL_USER_IDS = [1255]
```

## 3. Run 
- Type this, then hit `ENTER`
```bash
locust -f locustfile.py
```
- You'll see the Locust web ui open up on port `:8089`:
  - **Number of users** — This caps the number of <u>Locust threads</u>. If set to 5, each of the 5 threads will continuously create new Onebrief users.
  - **Ramp up** — Locust threads to spawn per second. 1 is fine.
  - **Host**: — Target site. Defaults to `config.HOST_URL`.
- Click `Start`

**Here's what happens**
- Configured supervisor credentials are injected into a browser, and kept open for the duration of the locust test. 
- The sole purpose of that browser is to link newly-created user accounts to the configured shared plan.
- For each Locust thread, a new user registers for an account
- Once signed in, the user is added to the shared plan
- The new user then navigates to the shared order url
- The new user proceeds to do one of several tasks...
  - Create cards in the card library
  - Create a random artifact
  - Edit the order
  - etc...

## 4. Observe
Assuming you've added your user id to the list of `ADDITIONAL_USER_IDS` in `config.py` and clicked `start`, do this:
- Locust web UI => `Logs`
- Wait for the log output to print the URL to the shared plan
- Copy that URL and visit it in your browser
- Login and navigate to the Shared Order
- Wait for the arrival of the Locust users

## 5. Halt
- Stop the Locust test at any time `CTRL+C` in the console.
- Deactivate the virtual environment with...

```bash
deactivate
```

## 6. Rerun (after halting)
Assuming you've gone through the install once, just do this from the repo root:

```bash
source venv/bin/activate
locust -f locustfile.py
```
