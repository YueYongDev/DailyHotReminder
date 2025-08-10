```markdown
DailyHotReminder/
├── daily_hot_collector.py    # 热点数据收集器
├── daily_hot_reminder.py     # 邮件提醒发送器
├── daily_hot_scheduler.py    # 定时任务调度器
├── models.py                 # 数据库模型
├── database.py               # 数据库连接配置
├── config.py                 # 配置文件
├── .env.example             # 环境变量示例配置
├── .env                     # 环境变量配置（需手动创建）
├── requirements.txt         # 项目依赖
├── Dockerfile               # Docker配置文件
└── docker-compose.yml       # Docker Compose配置文件
```
## 环境要求

- Python 3.8+
- PostgreSQL数据库
- SMTP邮件服务

## 安装部署

### 本地部署

1. 克隆项目代码：
```
bash
git clone <repository-url>
cd DailyHotReminder
```
2. 安装依赖：
```
bash
pip install -r requirements.txt
```
3. 配置环境变量：
复制 `.env.example` 文件为 `.env`，并根据实际情况修改配置：
```
bash
cp .env.example .env
```
4. 配置说明：
- 邮件配置：配置SMTP服务器信息和发件人账号
- 数据库配置：配置PostgreSQL数据库连接信息
- 收件人订阅配置：按格式`RECIPIENT_{邮箱地址}={分类列表}`添加订阅用户
- AI摘要服务：配置摘要API地址

### Docker部署（推荐）

1. 配置环境变量：
修改 `.env` 文件中的配置信息

2. 构建并启动容器：
```
bash
docker compose up -d --build
docker logs -f daily-hot-reminder
```
## 使用说明

### 配置收件人订阅

在 `.env` 文件中按以下格式添加收件人订阅配置：
```

RECIPIENT_user@example.com=36kr,zhihu,github
```
支持的分类包括：
- `36kr`: 36氪
- `zhihu`: 知乎
- `tieba`: 百度贴吧
- `juejin`: 掘金
- `github`: GitHub
- `ithome-xijiayi`: IT之家-西嘉懿
- `bilibili`: 哔哩哔哩

### 定时任务

系统包含三个定时任务，默认时间：
- 热点数据收集：每天上午8点
- 热点数据分析：每天上午9点
- 邮件发送：每天上午10点

可通过修改 [daily_hot_scheduler.py](file:///Users/yueyong/Dev/DailyHotReminder/daily_hot_scheduler.py) 文件中的Cron表达式来调整执行时间。

### 手动执行

也可以手动执行各个模块：
```
bash
# 收集热点数据
python daily_hot_collector.py

# 发送邮件
python daily_hot_reminder.py
```
## 配置参数说明

| 参数名 | 说明 | 默认值 |
|--------|------|--------|
| [SMTP_SERVER](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L16-L16) | SMTP服务器地址 | smtp.gmail.com |
| [SMTP_PORT](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L17-L17) | SMTP端口 | 587 |
| [SENDER_EMAIL](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L18-L18) | 发件人邮箱 |  |
| [SENDER_PASSWORD](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L15-L15) | 发件人邮箱密码或授权码 |  |
| [SUMMARIZER_API_URL](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L9-L9) | AI摘要服务地址 | http://127.0.0.1:8001/summarize |
| [SQLALCHEMY_DATABASE_URL](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L13-L13) | 数据库连接地址 | postgresql://root:root@localhost:5432/alfred |
| [MAX_ITEMS_PER_EMAIL](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L18-L18) | 每封邮件最大项目数 | 12 |
| [RUN_AS_SCHEDULER](file:///Users/yueyong/Dev/DailyHotReminder/config.py#L23-L23) | 是否以定时任务模式运行 | false |

## 邮件内容分发策略

系统根据用户订阅的分类数量智能分配邮件内容：
- 每个分类默认选取3条最热内容
- 根据订阅分类数量动态调整每个分类的内容数量
- 单封邮件最多包含12条内容（可通过环境变量调整）
- 按热度排序展示内容

例如：
- 用户订阅3个分类：每个分类选取4条内容（3*4=12）
- 用户订阅5个分类：每个分类选取2条内容（5*2=10）

## 项目依赖

- SQLAlchemy: 数据库ORM
- Requests: HTTP请求库
- Loguru: 日志记录
- Jinja2: 模板引擎
- APScheduler: 定时任务
- python-dotenv: 环境变量加载

## 许可证

MIT License
```
