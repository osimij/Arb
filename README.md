# Telegram Manager Bot

This is a Telegram bot designed to manage user interactions by connecting them with available managers. It uses a round-robin system to ensure fair distribution of user requests.

## Features

-   **User-friendly Interface**: Simple buttons for users to request a manager.
-   **Manager Rotation**: Automatically assigns users to the next available manager in a queue.
-   **Admin Commands**: Allows an admin to add, delete, and list managers.
-   **Deployment Ready**: Configured for deployment on services like Render.com.
-   **Keep-Alive**: Includes a web server to keep the bot active on free hosting tiers.

## Setup

1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Set environment variables for `BOT_TOKEN` and `ADMIN_ID`.
4.  Run the bot: `python main.py` 