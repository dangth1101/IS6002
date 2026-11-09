# BIRD-VN-Robust-50 — Physical Database (Bước 2B)

| Thuộc tính | Giá trị |
|---|---|
| Database schema version | 1 |
| Builder / validator | 0.1.0 |
| Seed mặc định | 6002 |
| Phạm vi | Hai SQLite database synthetic; Intent Cards/Questions/SQL hiện ở dạng draft, chưa được Benchmark Owner duyệt |
| Trạng thái | Bước 2B được Benchmark Owner xác nhận nghiệm thu riêng trong yêu cầu Autonomous Benchmark Implementation ngày 2026-11-09; snapshot/hash dưới đây là baseline đóng băng |

## Tệp và cách chạy

Build, seed, validate và rebuild độc lập để đối chiếu SHA-256 bằng một lệnh:

```powershell
.\.venv\Scripts\python.exe scripts\build_bird_vn_physical.py
```

Đổi seed hoặc output directory:

```powershell
.\.venv\Scripts\python.exe scripts\build_bird_vn_physical.py --seed 6002 --output benchmark_data\physical
```

Kiểm thử invariant và negative fixtures:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp=benchmark_data\pytest_tmp tests\test_benchmark_physical.py -q
```

Hoặc lưu kết quả fixture tests (và toàn bộ repository tests) thành JSON/Markdown/JUnit evidence:

```powershell
.\.venv\Scripts\python.exe scripts\run_bird_vn_physical_tests.py
.\.venv\Scripts\python.exe scripts\run_bird_vn_physical_tests.py --all
```

Lệnh chỉ ghi vào `benchmark_data/physical/`; hai DB BIRD hiện tại trong `data/` không bị mở hoặc sửa. Mỗi connection tạo bởi builder/validator bật và xác nhận `PRAGMA foreign_keys=ON`.

## Artifacts

- `benchmark_data/physical/erp_sales.sqlite`, `wms_inventory.sqlite`: snapshot vật lý.
- `schema_erp_sales.sql`, `schema_wms_inventory.sql`: DDL đúng với snapshot build.
- `seed_config.json`: seed, schema version và generator version.
- `build_manifest.json`: phiên bản Python/SQLite, counts, schema/config/source/database SHA-256 và kết quả tái lập.
- `validation/*_validation.json`: machine-readable invariant results và failure details.
- `validation/*_validation.md`: báo cáo dễ đọc theo từng invariant.
- `fixture_test_results.*`, `all_test_results.*`: pytest case results dạng JSON/Markdown và JUnit XML.
- `BUILD_REPORT.md`: tóm tắt build.

Manifest là nguồn chuẩn cho hash hiện hành. Hai lần build sạch với cùng seed phải có SHA-256 database giống nhau trên cùng môi trường Python/SQLite. Khác phiên bản SQLite/Python có thể tạo byte khác dù nội dung logic tương đương; khi đó cần so sánh row-level deterministic export và ghi môi trường mới.

## Kiểm chứng và giới hạn

- SQL `PK`, `FK`, `UNIQUE`, `NOT NULL`, `CHECK` và indexes được khai báo theo Data Dictionary. Các invariant cross-row được kiểm tra riêng trong `bird_vn_benchmark/validate.py`.
- Negative tests tạo bản sao trong temporary directory, sau đó gây lỗi có chủ đích; không đưa dữ liệu sai vào snapshot chính.
- WMS opening balances, transfers, shipments, receipts, adjustments, draft/cancelled docs và movement identities là dữ liệu synthetic. ERP có nhiều status, lines, captures/refunds, returns, NULL và measures theo thời điểm khác nhau.
- Database này là nền tảng vật lý cho intent authoring; kích thước seed được chọn cho demo và kiểm tra semantics, không phải benchmark dataset hoàn chỉnh hoặc dữ liệu hiệu năng.
- Hai empty-result slots ERP-EF-04 và WMS-EF-04 đã được ánh xạ thành draft intents; chưa có owner approval và chưa có false-empty fixture trong snapshot đóng băng.
- Tiêu chí nghiệm thu Bước 2B: builder tái lập, cả hai validator PASS, positive/negative fixtures đạt, hashes/artifacts lưu được, không có lỗi Critical/Major. Việc nghiệm thu chính thức thuộc Benchmark Owner.
