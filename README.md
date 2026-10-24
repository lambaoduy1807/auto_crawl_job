# Job Crawler & CV Matcher

Dự án thu thập tin tuyển dụng từ nhiều trang việc làm, cung cấp API để chạy và theo dõi các lượt crawl, đồng thời có giao diện dashboard để xem kết quả matching giữa job và CV.
## Workflow & Demo

### 1.Workflow

<img width="1256" height="557" alt="image" src="https://github.com/user-attachments/assets/6795a2bf-b5f8-488c-8e94-e66fe6333e58" />

Workflow được xây dựng bằng n8n nhằm tự động hóa quy trình thu thập tin tuyển dụng và đối chiếu CV với công việc. Hệ thống lấy CV từ Google Drive, trích xuất thông tin ứng viên, thu thập tin tuyển dụng thông qua API và lọc các công việc phù hợp. Sau đó, AI phân tích mức độ tương thích giữa CV và mô tả công việc, xác định kỹ năng phù hợp, kỹ năng còn thiếu và tạo thư ứng tuyển cá nhân hóa (Cover Letter). Kết quả được chuẩn hóa và lưu vào PostgreSQL để hiển thị trên dashboard, giúp người dùng dễ dàng đánh giá mức độ phù hợp và quản lý trạng thái ứng tuyển.

### 2. Demo Video

Xem video demo để khám phá cách hệ thống hoạt động, từ khởi chạy crawl đến theo dõi kết quả matching trên dashboard.

https://youtu.be/zNgEZfUh7mc



## Chức năng chính

- Crawl việc làm từ **ITviec, Vieclam24h, VietnamWorks, JobsGO** và **Saramin** bằng Crawl4AI.
- Chạy crawl bất đồng bộ qua RabbitMQ; trạng thái và kết quả từng yêu cầu được lưu trong Redis.
- Trả kết quả crawl dưới dạng JSON và ghi danh sách đã chuẩn hóa vào `jobs.json`.
- Dashboard hiển thị các job match, điểm và mức độ phù hợp, CV được so khớp, thông tin ứng tuyển, lý do AI, kỹ năng khớp/thiếu và cover letter.
- Lọc dashboard theo ngày tạo, địa điểm và trạng thái đã ứng tuyển; mở rộng từng job để xem nội dung chi tiết.
- Đánh dấu hoặc bỏ đánh dấu một job là đã ứng tuyển.

## Công nghệ

| Thành phần | Công nghệ |
| --- | --- |
| API | Python, FastAPI, SQLAlchemy |
| Thu thập dữ liệu | Crawl4AI, Patchright/Chromium; có Scrapy spider cho ITviec |
| Hàng đợi | RabbitMQ |
| Trạng thái crawl | Redis |
| Dữ liệu job match | PostgreSQL |
| Giao diện | React, TypeScript, Vite, Tailwind CSS |
| Chạy dịch vụ | Docker Compose, Nginx |

## Cấu trúc dự án

```text
.
├── cv_fe/                       # Ứng dụng dashboard React
├── job_crawler/
│   ├── api.py                   # FastAPI endpoints
│   ├── database.py              # SQLAlchemy model cho bảng jobs
│   ├── rabbit/                  # RabbitMQ producer và consumer
│   ├── craw4ai/                 # Cấu hình và crawler theo nguồn
│   └── job_crawler/spiders/     # Scrapy spider
├── docker-compose.yml
├── Dockerfile                   # Image Python API/worker
└── requirements.txt
```

## Chạy bằng Docker Compose

### Yêu cầu

- Docker Desktop có Docker Compose.
- Một RabbitMQ server có thể truy cập được từ các container. RabbitMQ không được khai báo trong `docker-compose.yml` hiện tại.
- Bảng PostgreSQL `jobs` đã được khởi tạo với các cột mà model trong `job_crawler/database.py` sử dụng. Dự án hiện chưa kèm migration hoặc script tạo schema.

### Cấu hình

Tạo file `job_crawler/.env` trước khi chạy Compose. Compose yêu cầu file này cho service API và worker:

```env
RABBITMQ_URL=amqp://<user>:<password>@<rabbitmq-host>:5672/%2F
RABBITMQ_QUEUE=crawl_queue
```

Thay các giá trị trong dấu `<...>` bằng thông tin RabbitMQ của bạn. Compose tự cấu hình Redis và PostgreSQL nội bộ; địa chỉ database trong Compose là `postgresql://postgres:postgres@postgres:5432/job_crawler`.

### Khởi động

Từ thư mục gốc dự án:

```bash
docker compose up --build
```

Mở các địa chỉ sau:

| Dịch vụ | Địa chỉ |
| --- | --- |
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| n8n | http://localhost:5678 |
| pgAdmin | http://localhost:5050 |

Dừng các dịch vụ bằng `Ctrl+C`, hoặc chạy `docker compose down` trong terminal khác. Dữ liệu PostgreSQL, Redis, n8n và pgAdmin được giữ trong Docker volumes.

## Luồng dữ liệu

1. Gọi `POST /crawl` để tạo yêu cầu crawl. API đưa yêu cầu vào RabbitMQ và trả về `request_id`.
2. Worker lấy yêu cầu, chạy các crawler, cập nhật trạng thái trong Redis và lưu kết quả crawl.
3. Kiểm tra tiến độ bằng endpoint trạng thái; khi hoàn tất, lấy JSON kết quả từ endpoint result.
4. Dashboard tải các bản ghi matching từ bảng PostgreSQL `jobs` qua `GET /job-matches`.

> Kết quả crawl được lưu trong Redis và `jobs.json`; endpoint `/job-matches` đọc dữ liệu matching từ PostgreSQL. Compose không tự chuyển kết quả crawl thành bản ghi matching trong bảng `jobs`.

## API chính

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/` | Kiểm tra API đang hoạt động |
| `POST` | `/crawl` | Thêm yêu cầu crawl vào hàng đợi |
| `GET` | `/crawl/{request_id}/status` | Xem trạng thái crawl |
| `GET` | `/crawl/{request_id}/result` | Lấy kết quả khi crawl hoàn tất |
| `GET` | `/job-matches` | Lấy danh sách job match từ PostgreSQL |
| `POST` | `/job-matches/{match_id}/apply` | Đánh dấu đã ứng tuyển |
| `POST` | `/job-matches/{match_id}/unapply` | Bỏ trạng thái đã ứng tuyển |

Mở http://localhost:8000/docs để xem request/response và thử gọi API.

## Chạy frontend riêng

```bash
cd cv_fe
npm install
npm run dev
```

Frontend mặc định gọi API tại `http://localhost:8000` (cấu hình trong `cv_fe/src/api.ts`). Để build bản production:

```bash
npm run build
```

## Cấu hình crawler

Các nguồn và URL crawl mặc định được khai báo trong `job_crawler/craw4ai/common_config.py`. Cùng file này cấu hình số job và số trang tối đa cho từng nguồn. Từ khóa và độ tuổi tin đăng mặc định cũng nằm trong cấu hình này.

## Lưu ý dữ liệu

- Worker cần `RABBITMQ_URL` hợp lệ để nhận yêu cầu crawl; API cũng cần giá trị này để gửi yêu cầu.
- PostgreSQL trong Compose tạo database `job_crawler`, nhưng không tự tạo bảng `jobs`. Hãy khởi tạo schema trước khi dùng dashboard/API job match.
- Dashboard chỉ hiển thị dữ liệu đã có trong bảng `jobs`; việc thu thập tin mới không tự tạo điểm match, đánh giá AI hoặc cover letter.
- Không commit file `.env` hoặc thông tin xác thực vào repository.
