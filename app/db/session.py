# app/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://salon:rQ750VVDxHgEgSazxzTyVsdbtz4mUuB8@dpg-d68r1ji48b3s73aqbpeg-a.oregon-postgres.render.com/salonbooking_db")

# echo=True for SQL logging (handy while learning)
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args={"sslmode": "require"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
