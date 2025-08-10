import os

from dotenv import load_dotenv

load_dotenv()

ALL_ENV_VARS = os.environ.items()

# 网页分析服务链接
SUMMARIZER_API_URL = os.getenv('SUMMARIZER_API_URL', "http://127.0.0.1:8001/summarize")

# 数据库配置
SQLALCHEMY_DATABASE_URL = os.getenv('SQLALCHEMY_DATABASE_URL', "postgresql://root:root@localhost:5432/alfred")

# 邮件配置
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'yueyong.lyy@icloud.com')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')

# 邮件内容配置
MAX_ITEMS_PER_EMAIL = int(os.getenv('MAX_ITEMS_PER_EMAIL', '12'))

# 定时任务配置
RUN_AS_SCHEDULER = os.getenv('RUN_AS_SCHEDULER', '').lower() == 'true'