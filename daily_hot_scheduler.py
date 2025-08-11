# scheduler_main.py
import os
import signal
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from daily_hot_collector import collect_daily_hot_data, analyze_daily_hot_data
from daily_hot_reminder import send_personalized_emails

# ==== 日志 ====
LOG_DIR = os.getenv("LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),  # 控制台
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
)
logger.add(
    f"{LOG_DIR}/scheduler.log",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    enqueue=True,
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

TZ = ZoneInfo("Asia/Shanghai")


def get_next_time(job) -> Optional[datetime]:
    # v3: next_run_time；v4: next_fire_time
    nrt = getattr(job, "next_run_time", None) or getattr(job, "next_fire_time", None)
    if nrt:
        # 某些实现返回 naive datetime，补时区
        if nrt.tzinfo is None:
            nrt = nrt.replace(tzinfo=TZ)
        return nrt.astimezone(TZ)

    # 兜底：从 trigger 计算
    now = datetime.now(TZ)
    try:
        # v3 签名: (previous_fire_time, now)
        nft = job.trigger.get_next_fire_time(None, now)
    except TypeError:
        # v4 签名: (previous_fire_time, now) 也可能可用；某些实现叫 next
        try:
            nft = job.trigger.get_next_fire_time(previous_fire_time=None, now=now)
        except Exception:
            nft = None

    if nft and nft.tzinfo is None:
        nft = nft.replace(tzinfo=TZ)
    return nft.astimezone(TZ) if nft else None


def collect_job():
    try:
        logger.info("开始执行【数据收集】")
        collect_daily_hot_data()
        logger.info("完成【数据收集】")
    except Exception as e:
        logger.exception(f"【数据收集】出错: {e}")


def analyze_job():
    try:
        logger.info("开始执行【数据分析】")
        analyze_daily_hot_data()
        logger.info("完成【数据分析】")
    except Exception as e:
        logger.exception(f"【数据分析】出错: {e}")


def email_job():
    try:
        logger.info("开始执行【邮件发送】")
        send_personalized_emails()
        logger.info("完成【邮件发送】")
    except Exception as e:
        logger.exception(f"【邮件发送】出错: {e}")


def start_scheduler():
    scheduler = BlockingScheduler(
        timezone=TZ,
        job_defaults={
            "coalesce": True,  # 堆积时只跑一次
            "max_instances": 1,  # 防止并发重入
            "misfire_grace_time": 300,  # 错过触发点5分钟内仍执行
        },
    )

    # === 根据你的注释：8:00 / 8:05 / 9:00 ===
    scheduler.add_job(
        collect_job,
        CronTrigger(hour=1, minute=0),
        id="daily_hot_collector",
        name="每日热点收集",
        replace_existing=True,
    )
    scheduler.add_job(
        analyze_job,
        CronTrigger(hour=1, minute=5),
        id="daily_hot_analyzer",
        name="每日热点分析",
        replace_existing=True,
    )
    scheduler.add_job(
        email_job,
        CronTrigger(hour=10, minute=0),
        id="daily_hot_reminder",
        name="每日热点提醒",
        replace_existing=True,
    )

    logger.info("定时任务已启动：")
    for job in scheduler.get_jobs():
        nrt = get_next_time(job)
        logger.info(
            f"  - {job.name} | 下次运行：{nrt:%Y-%m-%d %H:%M:%S %Z}" if nrt else f"  - {job.name} | 下次运行：未知")

    # 优雅退出
    def _graceful_shutdown(signum, frame):
        logger.warning(f"收到信号 {signum}，准备停止调度器...")
        scheduler.shutdown(wait=True)
        logger.info("调度器已停止")

    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    try:
        scheduler.start()
        logger.info("立即执行一次收集/分析/发送任务用于验证")
        collect_job()
        analyze_job()
        email_job()
    except Exception as e:
        logger.exception(f"调度器异常退出：{e}")


if __name__ == "__main__":
    # 启动后立即执行一次（用于验证）
    if os.getenv("RUN_ON_START", "").lower() == "true":
        logger.info("RUN_ON_START=true：立即执行一次 收集/分析/发送 用于验证")
        try:
            collect_job()
            analyze_job()
            email_job()
        except Exception:
            logger.exception("RUN_ON_START 执行失败")

    if os.getenv("RUN_AS_SCHEDULER", "").lower() == "true":
        logger.info(f"以定时任务模式启动（当前时间 {datetime.now(TZ):%Y-%m-%d %H:%M:%S %Z}）")
        start_scheduler()
    else:
        logger.info("请设置环境变量 RUN_AS_SCHEDULER=true 后运行本程序")
