from time import sleep
from typing import Dict, Any


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


from typing import List
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from daily_hot_client import DailyHotClient
from database import SessionLocal
from models import DailyHot


def analyze_daily_hot_data(batch_size: int = 100, max_fail: int = 2) -> None:
    """
    拉取"待分析"的热点数据，调用外部摘要器生成 {summary, tags}，并写回数据库。

    规则：
    - 仅处理 last_summarized_at 为 NULL 且 url 非空的记录
    - 分析成功：写入 ai_summary/ai_tags，设置 last_summarized_at=now，清理失败计数
    - 分析失败：只增加 analysis_fail_count（不写 last_summarized_at），记录 last_error
    - 当 analysis_fail_count >= max_fail 时跳过
    - 每条记录独立提交，避免单条失败影响整批
    """
    session: Session = SessionLocal()
    client = DailyHotClient()

    success_cnt = 0
    fail_cnt = 0
    skip_no_url = 0
    skip_maxfail = 0
    skip_flagged = 0
    total_processed = 0
    
    try:
        # 先获取待处理数据的总数
        total_count = (
            session.query(DailyHot)
            .filter(
                DailyHot.last_summarized_at.is_(None),
                DailyHot.url.isnot(None),
                DailyHot.url != "",
            )
            .count()
        )
        
        if total_count == 0:
            logger.info("没有需要分析的热点数据")
            return
            
        logger.info(f"总共找到 {total_count} 条需要分析的热点数据")
        
        # 计算总批次数
        total_batches = (total_count + batch_size - 1) // batch_size
        current_batch = 0
        
        # 分批处理所有数据
        for offset in range(0, total_count, batch_size):
            current_batch += 1
            logger.info(f"开始处理第 {current_batch}/{total_batches} 批数据")
            
            # 获取当前批次的数据
            hot_items: List[DailyHot] = (
                session.query(DailyHot)
                .filter(
                    DailyHot.last_summarized_at.is_(None),
                    DailyHot.url.isnot(None),
                    DailyHot.url != "",
                )
                .order_by(DailyHot.collected_at.desc())
                .offset(offset)
                .limit(batch_size)
                .all()
            )

            # 如果没有更多数据需要处理，则退出循环
            if not hot_items:
                break

            logger.info(f"第 {current_batch} 批: 找到 {len(hot_items)} 条需要分析的热点数据")

            for item in hot_items:
                try:
                    # extra 规范化
                    if item.extra is None or not isinstance(item.extra, dict):
                        item.extra = {}

                    # 跳过"明确标记不分析"的
                    if item.extra.get("skip") is True:
                        skip_flagged += 1
                        continue

                    # 跳过无 URL 的（双保险，理论上上面的 filter 已经排除了）
                    if not item.url:
                        skip_no_url += 1
                        # 记一次失败，防止反复进入队列
                        item.extra["analysis_fail_count"] = item.extra.get("analysis_fail_count", 0) + 1
                        item.extra["last_error"] = "missing_url"
                        session.commit()
                        continue

                    # 失败次数上限
                    if item.extra.get("analysis_fail_count", 0) >= max_fail:
                        skip_maxfail += 1
                        continue

                    logger.info(f"分析中: {item.category} - {item.title}")
                    # 调用外部分析器
                    result = client.analyze_hot_item(item.url)
                    logger.debug(f"分析结果: {result}", extra={"item_id": item.id})
                    logger.debug(f"等待1秒...")
                    sleep(1)
                    if result and isinstance(result, dict) and "summary" in result and "tags" in result:
                        item.ai_summary = result["summary"]
                        item.ai_tags = result["tags"]
                        item.last_summarized_at = datetime.now()

                        # 清理失败痕迹
                        item.extra.pop("analysis_fail_count", None)
                        item.extra.pop("last_error", None)
                        if not item.extra:
                            item.extra = None

                        session.commit()
                        success_cnt += 1
                        logger.info(f"分析完成: {item.category} - {item.title}")
                    else:
                        # 失败分支：只累计失败，不写 last_summarized_at
                        item.extra["analysis_fail_count"] = item.extra.get("analysis_fail_count", 0) + 1
                        item.extra["last_error"] = "empty_result"
                        session.commit()
                        fail_cnt += 1
                        logger.error(f"分析失败（空结果）: {item.category} - {item.title}")

                except Exception as e:
                    # 异常同样视为失败；不写 last_summarized_at
                    try:
                        if item.extra is None or not isinstance(item.extra, dict):
                            item.extra = {}
                        item.extra["analysis_fail_count"] = item.extra.get("analysis_fail_count", 0) + 1
                        item.extra["last_error"] = str(e)
                        session.commit()
                    except Exception:
                        session.rollback()
                    fail_cnt += 1
                    logger.exception(f"分析失败（异常）: {item.category} - {item.title} | 错误: {e}")
                    
            total_processed += len(hot_items)
            logger.info(f"第 {current_batch} 批处理完成，已处理 {total_processed}/{total_count} 条数据")
            logger.debug(f"等待5秒...")
            sleep(5)

    except Exception as e:
        logger.exception(f"分析阶段顶层异常：{e}")
    finally:
        session.close()

    logger.info(
        "分析完成汇总："
        f"成功 {success_cnt} | 失败 {fail_cnt} | 跳过(无URL) {skip_no_url} | "
        f"跳过(失败达上限≥{max_fail}) {skip_maxfail} | 跳过(标记skip) {skip_flagged} | "
        f"总计处理 {total_processed}"
    )


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
