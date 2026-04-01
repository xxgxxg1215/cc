"""
应用配置
"""
import os

# ── 数据库 ──
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "whg348859")
MYSQL_DB = os.getenv("MYSQL_DB", "crop_disease")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)

# ── JWT ──
SECRET_KEY = os.getenv("SECRET_KEY", "crop-disease-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72

# ── 微信小程序 ──
WX_APPID = os.getenv("WX_APPID", "")
WX_SECRET = os.getenv("WX_SECRET", "")


# ── 文件上传 ──
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── 管理员 ──
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ── 百度文心一言 API（免费）──
XUNFEI_APPID = os.getenv("XUNFEI_APPID", "")  # 百度云 AppID
XUNFEI_SECRET = os.getenv("XUNFEI_SECRET", "")  # 百度云 Secret Key
XUNFEI_TOKEN = os.getenv("XUNFEI_TOKEN", "")
