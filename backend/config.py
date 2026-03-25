import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cashdabba.db")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "1440"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")

RSS_FEED_URLS = os.getenv(
    "RSS_FEED_URLS",
    "https://economictimes.indiatimes.com/industry/cons-products/food/rssfeeds/58476498.cms,"
    "https://www.thehindubusinessline.com/economy/agri-business/feeder/default.rss",
).split(",")

# Map each RSS feed URL to a category
RSS_CATEGORY_MAP = {
    "economictimes.indiatimes.com": "price_update",
    "thehindubusinessline.com": "market_trend",
}

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
