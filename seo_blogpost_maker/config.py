import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.txt")
GOOGLE_AUTH = os.path.join(BASE_DIR, "google_credentials.json")
PROMPT_PATH = os.path.join(BASE_DIR, "prompt.txt")

def load_api_keys():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        keys = {}
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                keys[key] = value
    return keys

keys = load_api_keys()

OPENAI_API_KEY = keys["OPENAI_API_KEY"]
HASHNODE_API_KEY = keys["HASHNODE_API_KEY"]
HASHNODE_BLOG_ID = keys["HASHNODE_BLOG_ID"]
SHEET_NAME = keys["SHEET_NAME"]
TAB_NAME = keys["TAB_NAME"]
DROPBOX_ACCESS_TOKEN = keys["DROPBOX_ACCESS_TOKEN"]
DROPBOX_IMAGE_FOLDER = "/automation material/downloaded_images"
DROPBOX_APP_KEY = keys["DROPBOX_APP_KEY"]
DROPBOX_APP_SECRET = keys["DROPBOX_APP_SECRET"]