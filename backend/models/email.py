"""Email subscriber model."""
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY
from models.base import Base


class EmailSubscriber(Base):
    __tablename__ = "email_subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(Text, nullable=False, unique=True)
    active = Column(Integer, server_default="1")
    weekdays = Column(ARRAY(Integer), nullable=False, server_default="ARRAY[0,1,2,3,4,5,6]")
    send_time = Column(Text, nullable=False, server_default="'09:05'")
    language = Column(Text, nullable=False, server_default="'zh'")
    last_sent_at = Column(DateTime(timezone=True))
