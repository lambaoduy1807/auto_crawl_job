
import json
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException

from job_crawler.rabbit.producer import publish_crawl_job
from job_crawler.redis_client import redis_client
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from sqlalchemy.orm import Session
from job_crawler.database import get_db, DBJobMatch

app = FastAPI(
    title="Job Crawler API",
    description="API để gửi và quản lý các Crawl4AI job crawler",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# ROOT API
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Job Crawler API is running"
    }


# ============================================================
# API 1: TẠO REQUEST + GỬI VÀO QUEUE
# ============================================================

@app.post("/crawl")
def start_crawl():

    # --------------------------------------------------------
    # 1. Tạo request ID
    # --------------------------------------------------------

    request_id = str(uuid.uuid4())

    created_at = datetime.now().isoformat()

    # --------------------------------------------------------
    # 2. Tạo thông tin request
    # --------------------------------------------------------

    request_data = {
        "request_id": request_id,
        "status": "queued",
        "created_at": created_at,
        "started_at": "",
        "completed_at": "",
        "result": "",
        "error": ""
    }

    # --------------------------------------------------------
    # 3. Lưu request vào Redis
    #
    # Key:
    # crawl:{request_id}
    # --------------------------------------------------------

    redis_client.hset(
        f"crawl:{request_id}",
        mapping=request_data
    )

    try:

        # ----------------------------------------------------
        # 4. Gửi request vào RabbitMQ
        # ----------------------------------------------------

        publish_crawl_job(
            request_id=request_id,
            crawler="all-crawl4ai"
        )

        # ----------------------------------------------------
        # 5. Cập nhật status = queued
        # ----------------------------------------------------

        return {
            "request_id": request_id,
            "status": "queued",
            "message": "Crawler request has been added to the queue"
        }

    except Exception as e:

        # ----------------------------------------------------
        # 6. Nếu gửi RabbitMQ thất bại
        # ----------------------------------------------------

        redis_client.hset(
            f"crawl:{request_id}",
            mapping={
                "status": "failed",
                "completed_at": datetime.now().isoformat(),
                "error": str(e)
            }
        )

        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "error": str(e)
            }
        )


# ============================================================
# API 2: KIỂM TRA STATUS
# ============================================================

@app.get("/crawl/{request_id}/status")
def get_crawl_status(request_id: str):

    # --------------------------------------------------------
    # Lấy request từ Redis
    # --------------------------------------------------------

    request = redis_client.hgetall(
        f"crawl:{request_id}"
    )

    # --------------------------------------------------------
    # Request không tồn tại
    # --------------------------------------------------------

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Request ID not found"
        )

    # --------------------------------------------------------
    # Trả về status
    # --------------------------------------------------------

    return {
        "request_id": request["request_id"],
        "status": request["status"],
        "created_at": request["created_at"],
        "started_at": request["started_at"],
        "completed_at": request["completed_at"],
        "error": request["error"]
    }


# ============================================================
# API 3: LẤY RESULT
# ============================================================

@app.get("/crawl/{request_id}/result")
def get_crawl_result(request_id: str):

    # --------------------------------------------------------
    # Lấy request từ Redis
    # --------------------------------------------------------

    request = redis_client.hgetall(
        f"crawl:{request_id}"
    )

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Request ID not found"
        )

    # --------------------------------------------------------
    # Chưa bắt đầu
    # --------------------------------------------------------

    if request["status"] in ["pending", "queued"]:

        return {
            "request_id": request_id,
            "status": request["status"],
            "message": "Crawler has not started yet"
        }

    # --------------------------------------------------------
    # Đang chạy
    # --------------------------------------------------------

    if request["status"] == "running":

        return {
            "request_id": request_id,
            "status": "running",
            "message": "Crawler is still running"
        }

    # --------------------------------------------------------
    # Failed
    # --------------------------------------------------------

    if request["status"] == "failed":

        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "error": request["error"]
            }
        )

    # --------------------------------------------------------
    # Completed
    # --------------------------------------------------------

    result = request["result"]

    if result:
        result = json.loads(result)
    else:
        result = []

    return {
        "request_id": request_id,
        "status": "completed",
        "result": result
    }

# ============================================================
# API 4: LẤY DỮ LIỆU JOB MATCH TỪ POSTGRESQL
# ============================================================


@app.get("/job-matches")
def get_job_matches(db: Session = Depends(get_db)):
    """
    API lấy danh sách các Job Matches từ database PostgreSQL.
    Lưu ý: Bạn cần cài đặt thư viện sqlalchemy và psycopg2-binary
    (pip install sqlalchemy psycopg2-binary)
    """
    matches = db.query(DBJobMatch).all()

    return [
        {
            column.name: getattr(match, column.name)
            for column in DBJobMatch.__table__.columns
        }
        for match in matches
    ]


@app.post("/job-matches/{match_id}/apply")
def mark_job_applied(match_id: int, db: Session = Depends(get_db)):
    return _set_job_applied(match_id, True, db)


@app.post("/job-matches/{match_id}/unapply")
def mark_job_not_applied(match_id: int, db: Session = Depends(get_db)):
    return _set_job_applied(match_id, False, db)


def _set_job_applied(match_id: int, is_applied: bool, db: Session):
    match = db.query(DBJobMatch).filter(DBJobMatch.id == match_id).first()
    if match is None:
        raise HTTPException(status_code=404, detail="Job match not found")

    match.is_applied = is_applied
    try:
        db.commit()
        db.refresh(match)
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update applied status") from error

    return {"id": match.id, "is_applied": match.is_applied}

