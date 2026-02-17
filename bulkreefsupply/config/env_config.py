import os

from dotenv import load_dotenv

load_dotenv()


class EnvConfig:
    PRODUCTS_FILE_DIR = os.getenv("PRODUCTS_FILE_DIR")
    SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")
