from sqlalchemy import create_engine, Column, Integer, Float, DateTime, String
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DATABASE_URL = "sqlite:///./vw_history.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class BatteryLog(Base):
    __tablename__ = "battery_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(Float, nullable=False)
    range_km = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=False)
    odometer = Column(Float, nullable=False, default=0.0)
    is_charging = Column(Integer, default=0) # 0 False, 1 True

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True) # Updated when trip ends
    start_odometer = Column(Float, nullable=False)
    end_odometer = Column(Float, nullable=True)
    start_level = Column(Float, nullable=False)
    end_level = Column(Float, nullable=True)
    is_active = Column(Integer, default=1) # 1 Active, 0 Completed

class AlarmSettings(Base):
    __tablename__ = "alarm_settings"

    id = Column(Integer, primary_key=True, index=True)
    days = Column(String, default="[]") # JSON string of days [0,1,2...] where 0=Monday
    time_str = Column(String, default="22:00")
    email_to = Column(String, default="")
    ntfy_topic = Column(String, default="")
    is_active = Column(Integer, default=0) # 1 Active, 0 Inactive
    last_triggered_date = Column(String, default="")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
