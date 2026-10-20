"""Competitor news and cloud vendor news models."""
from sqlalchemy import Column, Integer, Text, Date, TIMESTAMP, Index, UniqueConstraint
from models.base import Base


class CompetitorNews(Base):
    __tablename__ = "competitor_news"
    __table_args__ = (
        UniqueConstraint("scrape_date", "vendor", "title", name="idx_comp_news_unique"),
        Index("idx_comp_news_date", "scrape_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scrape_date = Column(Text, nullable=False)
    vendor = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text)
    category = Column(Text)
    published_date = Column(Date)
    created_at = Column(TIMESTAMP, server_default="NOW()")


class CloudVendorNews(Base):
    __tablename__ = "cloud_vendor_news"
    __table_args__ = (
        UniqueConstraint("crawl_date", "vendor", "title", name="idx_cloudnews_unique"),
        Index("idx_cloudnews_date", "crawl_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    crawl_date = Column(Text, nullable=False)
    vendor = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text)
    category = Column(Text)
    created_at = Column(TIMESTAMP, server_default="NOW()")
