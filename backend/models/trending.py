"""GitHub Trending, Baidu Hotsearch, Business Evaluation models."""
from sqlalchemy import Column, Integer, BigInteger, Text, Float, TIMESTAMP, Index, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import TIMESTAMP as PG_TIMESTAMP
from models.base import Base


class GithubTrending(Base):
    __tablename__ = "github_trending"
    __table_args__ = (
        UniqueConstraint("scrape_date", "category", "repo_name", name="idx_trending_unique"),
        Index("idx_trending_date", "scrape_date"),
        Index("idx_trending_category", "category"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scrape_date = Column(Text, nullable=False)
    scrape_time = Column(Text)
    repo_name = Column(Text, nullable=False)
    repo_url = Column(Text)
    description = Column(Text)
    language = Column(Text)
    stars = Column(Text)
    forks = Column(Text)
    today_stars = Column(Text)
    category = Column(Text)
    summary = Column(Text)


class BaiduHotsearch(Base):
    __tablename__ = "baidu_hotsearch"
    __table_args__ = (
        UniqueConstraint("scrape_date", "title", name="idx_baidu_unique"),
        Index("idx_baidu_date", "scrape_date"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scrape_date = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text)
    heat = Column(Text)
    category = Column(Text)


class TrendingBusinessEval(Base):
    __tablename__ = "trending_business_eval"
    __table_args__ = (
        UniqueConstraint("scrape_date", "repo_name", name="idx_tbe_unique"),
        Index("idx_tbe_date", "scrape_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("trending_business_eval.id"))
    scrape_date = Column(Text, nullable=False)
    repo_name = Column(Text, nullable=False)
    repo_url = Column(Text)
    language = Column(Text)
    stars = Column(Text)
    summary = Column(Text)
    summary_zh = Column(Text)
    d1 = Column(Float)
    d2 = Column(Float)
    d3 = Column(Float)
    d4 = Column(Float)
    total = Column(Float)
    level = Column(Text)
    recommendation = Column(Text)
    reasoning = Column(Text)
    eval_time = Column(Text)
    created_at = Column(TIMESTAMP, server_default="NOW()")
