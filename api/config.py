"""
API Configuration - Environment variables and settings
"""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# Build DATABASE_URL from individual parts to avoid special-character issues in password
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Gikonyo@2025!')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'creviastory')
DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
WEB_API_URL = os.getenv('WEB_API_URL', 'http://localhost:8000')
WEB_API_SECRET = os.getenv('WEB_API_SECRET', 'crevia-internal-key')

# CORS origins (Next.js frontend)
CORS_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://creviacockpit.com',
    'https://www.creviacockpit.com',
    'https://api.creviacockpit.com',
]

# JWT Authentication
JWT_SECRET = os.getenv('JWT_SECRET', 'crevia-jwt-secret-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
JWT_REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days

# Admin portal
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '')
ADMIN_DISCORD_WEBHOOK = os.getenv('ADMIN_DISCORD_WEBHOOK', '')

# Payments — USDC on Base L2
PAYMENT_RECEIVE_WALLET = os.getenv('PAYMENT_RECEIVE_WALLET', '')   # Treasury wallet on Base
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
NEXAPAY_API_KEY = os.getenv('NEXAPAY_API_KEY', '')
NEXAPAY_SECRET = os.getenv('NEXAPAY_SECRET', '')                   # HMAC webhook validation
NEXAPAY_MERCHANT_ID = os.getenv('NEXAPAY_MERCHANT_ID', '')

# Content tier delay (seconds)
ENTERPRISE_WINDOW = 3600      # First hour: Enterprise only
PRO_WINDOW = 21600            # 1-6 hours: Pro
# After PRO_WINDOW: Free
