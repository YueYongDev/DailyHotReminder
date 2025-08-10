# db/models.py
from sqlalchemy import Column, Integer, Text, ARRAY, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class DailyHot(Base):
    __tablename__ = "daily_hot"
    id = Column(Integer, primary_key=True)
    category = Column(Text, nullable=False)  # 热点分类，如 36kr, tieba 等
    title = Column(Text, nullable=False)
    description = Column(Text)  # 描述
    cover = Column(Text)  # 封面图片链接
    hot_score = Column(Integer)  # 热度值
    url = Column(Text)  # 原始链接
    mobile_url = Column(Text)  # 移动端链接
    publish_time = Column(TIMESTAMP)  # 发布时间
    collected_at = Column(TIMESTAMP)  # 收集时间
    ai_tags = Column(ARRAY(Text))  # AI生成的标签
    ai_summary = Column(Text)  # AI生成的摘要
    last_summarized_at = Column(TIMESTAMP)  # 最后一次AI处理时间
    last_embedded_at = Column(TIMESTAMP)  # 最后一次向量化时间
