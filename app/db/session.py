# app/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://salon:u7LK1FC4yLg2Joc8qNwnch3UPNjTMfuq@dpg-d68cvn3h46gs73fd84qg-a.virginia-postgres.render.com/salon_db_cz7z")

# echo=True for SQL logging (handy while learning)
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
