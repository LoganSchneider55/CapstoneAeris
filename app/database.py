import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "defaultdb")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SSL_CA = os.getenv("DB_SSL_CA", None)

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

connect_args = {}
if DB_SSL_CA:
    connect_args = {"ssl": {"ca": DB_SSL_CA}}

engine = create_engine(DB_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db():
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT 1")).scalar()
            return True, "reachable" if row == 1 else "unexpected"
    except Exception as e:
        return False, str(e)
