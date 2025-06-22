from flask import Flask
from threading import Thread
import requests
import time
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

def ping_self():
    """Ping the bot every 14 minutes to keep it alive"""
    while True:
        time.sleep(840)  # 14 minutes
        try:
            # Get the Render URL from environment variable
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url:
                requests.get(render_url)
                print(f"Pinged {render_url}")
        except Exception as e:
            print(f"Ping failed: {e}") 