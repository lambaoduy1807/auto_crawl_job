import os
from sqlalchemy import create_engine, Column, String, Boolean, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker

# Lấy URL kết nối database từ biến môi trường, hoặc dùng giá trị mặc định
# Thay đổi username, password, host, port và db_name cho phù hợp với cấu hình của bạn
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/auto_apply_db"
)

# Khởi tạo engine kết nối với database
engine = create_engine(DATABASE_URL)

# Tạo class SessionLocal để làm việc với database trong mỗi request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class để định nghĩa các models
Base = declarative_base()

# ============================================================
# Định nghĩa Model mapping với bảng trong database
# ============================================================
class DBJobMatch(Base):
    __tablename__ = "jobs"

    id = Column(BigInteger, primary_key=True, index=True)
    job_id = Column(String, index=True)
    title = Column(String)
    company = Column(String)
    url = Column(String)
    salary = Column(String)
    location = Column(String)
    working_model = Column(String)
    experience = Column(String)
    description = Column(String)
    requirements = Column(String)
    benefits = Column(String)
    source = Column(String)

    cv_name = Column(String)
    match_score = Column(String)
    match_level = Column(String)

    matched_skills = Column(String)
    missing_skills = Column(String)

    experience_match = Column(Boolean)
    education_match = Column(Boolean)
    language_match = Column(Boolean)
    position_match = Column(Boolean)

    match_reason = Column(String)

    created_at = Column(String)
    updated_at = Column(String)
    is_applied = Column(Boolean, default=False)

# Hàm helper để lấy session của database (Dùng trong FastAPI Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
