import os

TOKEN = os.environ.get("BOT_TOKEN", "7312413389:AAH1djA4FKjIGJwXMWmyOHORT5qckScq52U")

# --- Multi-Admin Configuration ---

# A list of admin user IDs that can be changed directly in the code.
ADMIN_IDS = [
    6965346393,
    7586007738,  # The test ID you wanted to add
    788357726    # osimijasur - add this user as admin
    # You can add more admin IDs here, e.g., 123456789
]

# Get your main admin ID from the environment variable (e.g., on Render).
# This ensures your ID is always included as an admin without changing the code.
primary_admin_id_str = os.environ.get("ADMIN_ID")
if primary_admin_id_str:
    try:
        primary_admin_id = int(primary_admin_id_str)
        if primary_admin_id not in ADMIN_IDS:
            ADMIN_IDS.append(primary_admin_id)
    except ValueError:
        # Handle case where ADMIN_ID is not a valid integer
        print(f"Warning: ADMIN_ID environment variable ('{primary_admin_id_str}') is not a valid integer.")

# --- API Configuration ---
# Single API key shared by all managers
API_KEY = os.environ.get("API_KEY", "2d329336c2f4c0612b96ce032ed081dec1ce0ee9805182f6a7f047e220ab06cb")
