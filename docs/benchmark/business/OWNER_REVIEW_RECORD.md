# Ghi nhận rà soát quy tắc nghiệp vụ

| Trường | Giá trị |
|---|---|
| Tài liệu được rà soát | [BIRD_VN_BUSINESS_RULES_REVIEW_DRAFT.docx](BIRD_VN_BUSINESS_RULES_REVIEW_DRAFT.docx) |
| Người rà soát ghi trên phiếu | Liêu Trương Gia Huy |
| Ngày ghi trên phiếu | 2026-11-17 |
| Kết quả ghi trên phiếu | Chấp nhận tài liệu nghiệp vụ |
| Phạm vi | Chấp nhận tài liệu mô tả các quy tắc nghiệp vụ mô phỏng ERP Sales và WMS Inventory |

## Các nội dung đã được chọn đồng ý

Theo phiếu đã điền trong tài liệu Word, người rà soát chọn **Đồng ý** cho sáu mục:

1. Cách phân biệt giá trị đơn hàng, doanh thu ghi nhận và tiền đã thu.
2. Trạng thái đơn, giao hàng, trả hàng và hoàn tiền.
3. Ngày nghiệp vụ, mốc giờ, múi giờ và khoảng thời gian.
4. Trạng thái chứng từ kho, dấu biến động, điều chuyển và tồn kho.
5. NULL, số 0, không có bản ghi và kết quả rỗng.
6. Các giới hạn được nêu trong tài liệu.

Phiếu không ghi chú yêu cầu sửa và lựa chọn cuối cùng là **Chấp nhận tài liệu nghiệp vụ**.

## Phạm vi không bao gồm

Ghi nhận này chỉ xác nhận tài liệu quy tắc nghiệp vụ mô phỏng. Nó **không** phê duyệt riêng 40 Intent Final, 40 SQL chuẩn, kết quả kỳ vọng, bộ kiểm tra Python, câu hỏi gốc, biến thể câu hỏi, bằng chứng bộ dữ liệu biên hoặc việc đóng băng bộ dữ liệu Final.

Các điểm chưa thống nhất tại WMS-AG-04, WMS-RK-01, WMS-RK-03, WMS-CD-01 và WMS-RK-02 vẫn phải được xử lý và kiểm chứng trước khi các nhóm đó có thể được duyệt. Chấp nhận quy tắc chung không tự giải quyết các mâu thuẫn cụ thể giữa Intent và SQL.

## Cập nhật xử lý năm nhóm WMS Final — 2026-11-17

Benchmark Owner đồng ý với các phương án xử lý cụ thể cho WMS-AG-04, WMS-RK-01, WMS-RK-02, WMS-RK-03 và WMS-CD-01. Các sửa đổi kỹ thuật và kiểm tra tự động đã được ghi trong registry, Validation Records và `benchmark_data/authoring/wms_final_alignment_fixture_validation.json`.

Việc đồng ý phương án sửa không phải phê duyệt cuối cùng cho Intent Card, câu hỏi, SQL chuẩn hoặc kết quả mong đợi của năm nhóm. Tất cả vẫn giữ trạng thái `NEEDS_HUMAN_REVIEW`.

## Nguồn và giới hạn bằng chứng

Ghi nhận này được lập từ các lựa chọn, tên người rà soát và ngày tháng có trong phiếu Word. Đây là bản chép lại quyết định đã ghi trên phiếu, không phải một lần rà soát độc lập mới. Tài liệu Word đã điền là bằng chứng gốc.


## Benchmark Owner duyệt 40 nhóm Final — 2026-11-17

Benchmark Owner xác nhận đã xem xét và chấp nhận 40 nhóm Final. Quyết định bao gồm 40 Intent Cards, 40 SQL chuẩn dự thảo, expected outputs và 440 câu hỏi Q00–Q10 hiện hành. Provenance chi tiết được lưu tại `benchmark_data/authoring/final_owner_approval_provenance_2026-11-17.json`; các quyết định theo nhóm và câu hỏi nằm trong registry và Validation Records.

Giới hạn được ghi nhận cùng quyết định: Q01/Q02 trong các nhóm có chung phần yêu cầu cốt lõi sau khi bỏ câu dẫn; đây là hạn chế đa dạng cách diễn đạt đã được Benchmark Owner chấp nhận cho bản hiện tại. Trạng thái fixture được giữ nguyên, không biến bằng chứng chưa ghi nhận thành PASS.

Quyết định này không sửa câu hỏi, SQL, oracle, expected outputs hay SQLite snapshot; không đóng băng registry và không cấp phép chạy Official Evaluation. Các điều kiện phát hành khác vẫn phải được kiểm tra riêng.
