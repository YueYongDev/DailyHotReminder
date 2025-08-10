import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from daily_hot_collector import collect_daily_hot_data, analyze_daily_hot_data
from daily_hot_reminder import send_personalized_emails


def collect_job():
    """
    数据收集定时任务函数
    """
    try:
        logger.info("开始执行数据收集任务")
        collect_daily_hot_data()
        logger.info("数据收集任务执行完成")
    except Exception as e:
        logger.error(f"数据收集任务执行出错: {e}")


def analyze_job():
    """
    数据分析定时任务函数
    """
    try:
        logger.info("开始执行数据分析任务")
        analyze_daily_hot_data()
        logger.info("数据分析任务执行完成")
    except Exception as e:
        logger.error(f"数据分析任务执行出错: {e}")


def email_job():
    """
    邮件发送定时任务函数
    """
    try:
        logger.info("开始执行邮件发送任务")
        send_personalized_emails()
        logger.info("邮件发送任务执行完成")
    except Exception as e:
        logger.error(f"邮件发送任务执行出错: {e}")


def start_scheduler():
    """
    启动定时任务调度器
    """
    scheduler = BlockingScheduler()

    # 添加数据收集任务，每天上午8点执行
    scheduler.add_job(
        collect_job,
        CronTrigger(hour=0, minute=0),
        id='daily_hot_collector',
        name='每日热点收集',
        timezone='Asia/Shanghai'  # 使用中国时区
    )

    # 添加数据分析任务，每天上午9点执行
    scheduler.add_job(
        analyze_job,
        CronTrigger(hour=0, minute=5),
        id='daily_hot_analyzer',
        name='每日热点分析',
        timezone='Asia/Shanghai'  # 使用中国时区
    )

    # 添加邮件发送任务，每天上午10点执行
    scheduler.add_job(
        email_job,
        CronTrigger(hour=9, minute=0),
        id='daily_hot_reminder',
        name='每日热点提醒',
        timezone='Asia/Shanghai'  # 使用中国时区
    )

    logger.info("定时任务已启动:")
    logger.info("  - 热点数据收集任务: 每天上午8点")
    logger.info("  - 热点数据分析任务: 每天上午9点")
    logger.info("  - 热点摘要邮件发送任务: 每天上午10点")
    logger.info("按 Ctrl+C 停止程序")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("定时任务已停止")
        scheduler.shutdown()


if __name__ == "__main__":
    # 检查是否需要以定时任务模式运行
    if os.getenv('RUN_AS_SCHEDULER', '').lower() == 'true':
        start_scheduler()
    else:
        print("请使用定时任务模式运行本程序")
