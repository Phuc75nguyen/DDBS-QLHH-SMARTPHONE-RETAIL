# Distributed database system final Project "Smartphone Retail Management"

### Nhân sự tham gia của PhucNT, DiepVNH, PhucLam219 :vvv

### Cách chạy APP

- Bật Docker Desktop trước
- Chạy file docker_compose.yml bằng lệnh "docker compose -f docker_compose.yml up -d --build"
- Trong terminal chỗ chạy Docker gán:

$env:MONGODB_URI_SERVER1 = "mongodb://localhost:27017"

$env:MONGODB_URI_SERVER2 = "mongodb://localhost:27018"

$env:MONGODB_URI_SERVER3 = "mongodb://localhost:27019"

Đối với người dùng terminal "bash", gõ lệnh sau:

export MONGODB_URI_SERVER1="mongodb://localhost:27017"
export MONGODB_URI_SERVER2="mongodb://localhost:27018"
export MONGODB_URI_SERVER3="mongodb://localhost:27019"


-Tiếp theo bật một terminal khác để chạy app, tùy theo pip install có thể chạy các lệnh:

 streamlit run app.py
hoặc
 python -m streamlit run app.py
Nếu app chưa chạy, thì phảm đảm bảo đã cài các gói;
 python -m pip install streamlit pymongo

## Kiểm tra container đã chạy chưa
Trong terminal PowerShell hoặc tab terminal VS Code, gõ:
 docker ps

## Cách test nhanh CRUD:
Đăng nhập admin/admin → vào “Kho” thêm 1 kho CN1 (ví dụ KHO3).
Mở shell vào server3 để kiểm tra đã ghi thật:
docker exec -it qlhh_server3 mongosh
use qlhh_server3
db.Kho.find()


## Đăng nhập tài khoản CN1 (cn1_mgr/password) → tạo Đơn đặt hàng. Kiểm tra ở server1:
docker exec -it qlhh_server1 mongosh
use qlhh_server1
db.DatHang.find()


## Đăng nhập tài khoản CN2 → tạo phiếu → kiểm tra ở cổng 27018 
docker exec -it <tên_container_map_27018> mongosh
use qlhh_server2
db.PhieuXuat.find()