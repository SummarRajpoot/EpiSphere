from sqlalchemy import Column, Float, Integer, String, Text

from database import Base

class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=False)
    risk = Column(String(20), nullable=False)
    active_cases = Column(Integer, default=0)
    active_trend = Column(String(20), default="+0%")
    patients = Column(Integer, default=0)
    patients_trend = Column(String(20), default="+0%")
    history = Column(Text, default="[]")  # stores JSON string of 7 integers
    disease = Column(String(100), nullable=True)
    population_density = Column(Float, nullable=True)
    hospital_capacity = Column(Float, nullable=True)
    vaccination_rate = Column(Float, nullable=True)
    recommendations = Column(Text, nullable=True)  # stores JSON string
    last_week_cases = Column(Integer, nullable=True)
