from datetime import datetime
from datetime import datetime
from typing import Dict, Any

from loguru import logger
from sqlalchemy.orm import Session

from daily_hot_client import DailyHotClient
from database import SessionLocal
from models import DailyHot


# 修改后的 save_hot_item_to_db 函数
def save_hot_item_to_db(category: str, item: Dict[str, Any]) -> bool:
    """
    将单个热点数据保存到数据库

    :param category: 热点分类
    :param item: 热点数据项
    :return: 是否保存成功
    """
    session: Session = SessionLocal()
    try:
        # 检查是否已存在
        existing_item = session.query(DailyHot).filter(
            DailyHot.category == category,
            DailyHot.title == item.get('title')
        ).first()

        # 处理时间戳
        publish_time = None
        if 'timestamp' in item and item['timestamp']:
            try:
                # 处理毫秒时间戳
                timestamp = int(item['timestamp'])
                # 检查时间戳是否合理 (1970-01-01 到 2100-12-31)
                if 0 <= timestamp <= 4102444800000:  # 2100年底的毫秒时间戳
                    if timestamp > 1000000000000:  # 毫秒时间戳
                        publish_time = datetime.fromtimestamp(timestamp / 1000)
                    else:  # 秒时间戳
                        publish_time = datetime.fromtimestamp(timestamp)
                else:
                    logger.warning(f"时间戳超出合理范围，将忽略: {timestamp}")
            except (ValueError, OSError, OverflowError) as e:
                logger.warning(f"时间戳转换失败，将忽略时间信息: {item.get('timestamp')}, 错误: {e}")

        if existing_item:
            # 更新现有记录
            existing_item.description = item.get('desc')
            existing_item.cover = item.get('cover')
            existing_item.hot_score = item.get('hot')
            existing_item.url = item.get('url')
            existing_item.mobile_url = item.get('mobileUrl')
            existing_item.publish_time = publish_time
            existing_item.collected_at = datetime.now()
        else:
            # 创建新记录
            hot_item = DailyHot(
                category=category,
                title=item.get('title'),
                description=item.get('desc'),
                cover=item.get('cover'),
                hot_score=item.get('hot'),
                url=item.get('url'),
                mobile_url=item.get('mobileUrl'),
                publish_time=publish_time,
                collected_at=datetime.now()
            )
            session.add(hot_item)

        session.commit()
        logger.info(f"热点数据已保存到数据库: {category} - {item.get('title')}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"保存热点数据到数据库时出错: {category} - {item.get('title')}, 错误: {e}")
        return False
    finally:
        session.close()


def collect_daily_hot_data():
    """
    收集所有热点数据并保存到数据库
    """
    client = DailyHotClient()

    # 获取所有类目
    categories = client.get_all_categories()
    logger.info(f"获取到 {len(categories)} 个热点类目")

    # 获取所有热点数据
    all_hot_data = client.get_all_hot_lists()

    # 处理每个类目的数据
    for category_name, hot_data in all_hot_data.items():
        logger.info(f"正在处理 {category_name} 的热点数据...")

        # 获取热点列表
        hot_list = hot_data.get('data', [])
        logger.info(f"{category_name} 共有 {len(hot_list)} 条热点数据")

        # 保存每条热点数据
        for item in hot_list:
            save_hot_item_to_db(category_name, item)


def analyze_daily_hot_data():
    """
    对数据库中的热点数据进行分析，生成摘要和标签
    通过调用DailyHotClient中的外部API获取分析结果
    """
    session: Session = SessionLocal()
    client = DailyHotClient()

    try:
        # 获取未分析或需要重新分析的热点数据
        hot_items = session.query(DailyHot).filter(
            DailyHot.last_summarized_at.is_(None)
        ).all()

        logger.info(f"找到 {len(hot_items)} 条需要分析的热点数据")

        for item in hot_items:
            try:
                # 检查失败次数，如果失败超过2次则跳过
                if item.extra and isinstance(item.extra, dict):
                    fail_count = item.extra.get('analysis_fail_count', 0)
                    if fail_count >= 2:
                        logger.info(f"跳过分析（失败次数已达上限）: {item.category} - {item.title}")
                        continue

                # 检查是否有URL可以用于分析
                if not item.url:
                    logger.warning(f"跳过分析，没有URL: {item.category} - {item.title}")
                    # 记录失败次数
                    if not item.extra:
                        item.extra = {}
                    item.extra['analysis_fail_count'] = item.extra.get('analysis_fail_count', 0) + 1
                    item.last_summarized_at = datetime.now()
                    session.commit()
                    continue

                # 调用客户端的分析功能
                analysis_result = client.analyze_hot_item(item.url)

                if analysis_result:
                    # 更新数据库记录
                    item.ai_summary = analysis_result["summary"]
                    item.ai_tags = analysis_result["tags"]
                    item.last_summarized_at = datetime.now()
                    # 重置失败计数
                    if item.extra and isinstance(item.extra, dict):
                        item.extra['analysis_fail_count'] = 0

                    session.commit()
                    logger.info(f"分析完成: {item.category} - {item.title}")
                else:
                    logger.error(f"分析失败: {item.category} - {item.title}")
                    # 记录失败次数
                    if not item.extra:
                        item.extra = {}
                    item.extra['analysis_fail_count'] = item.extra.get('analysis_fail_count', 0) + 1
                    item.last_summarized_at = datetime.now()
                    session.commit()
                    continue

            except Exception as e:
                logger.error(f"分析失败: {item.category} - {item.title}, 错误: {e}")
                # 记录失败次数
                if not item.extra:
                    item.extra = {}
                item.extra['analysis_fail_count'] = item.extra.get('analysis_fail_count', 0) + 1
                item.extra['last_error'] = str(e)
                item.last_summarized_at = datetime.now()
                session.commit()
                continue

    except Exception as e:
        logger.error(f"分析热点数据时出错: {e}")
    finally:
        session.close()


def main():
    """
    主函数，用于执行热点数据收集和分析
    """
    logger.info("开始收集热点数据...")
    collect_daily_hot_data()
    logger.info("热点数据收集完成")

    logger.info("开始分析热点数据...")
    analyze_daily_hot_data()
    logger.info("热点数据分析完成")


if __name__ == "__main__":
    main()
