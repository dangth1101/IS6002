"""Conservative lexical evidence for review, never a semantic-equivalence judge.

An absent cue is a review hint, not a proven defect. A present cue does not prove
its scope, polarity or relationship; those require the locked card and human review.
"""
import re

CONFIRMED = r"confirmed|đã (?:được )?xác nhận"
POSTED = r"posted|đã ghi sổ"
UNIT = r"base[_ ]unit|đơn vị (?:cơ sở|chuẩn)|đơn vị"
NAME = r"tên"
SKU = r"sku"
PRODUCT_ID = r"product id|id sản phẩm|mã sản phẩm"
DOCUMENT_ID = r"document id|\bid\b|mã (?:định danh|chứng từ|phiếu|và số chứng từ)"
DOCUMENT_NO = r"document (?:number|id/no)|id/số|số (?:chứng từ|phiếu|hiệu)|id/no|mã và số"
DOCUMENT_TYPE = r"document (?:type|id/no/type)|loại|id/no/type"
STATUS = r"trạng thái|status"
CONTRACTS = {
    "ERP-EF-01": {
        "order_id": r"mã (?:đơn|định danh)", "order_no": r"số (?:đơn|hiệu)",
        "customer_id": r"mã khách hàng|customer_id", "order_date": r"ngày đặt",
        "order_status": STATUS, "confirmed_only": CONFIRMED,
    },
    "ERP-GB-03": {
        "rep_id": r"mã", "rep_name": NAME, "count_orders": r"số (?:đơn|lượng)|bao nhiêu đơn",
        "confirmed_cohort": CONFIRMED, "group_by_rep": r"từng|mỗi|theo (?:sales rep|rep)",
        "null_bucket": r"null", "unassigned": r"chưa (?:gán|phân công)|không có sales rep",
        "rep_with_orders": r"có (?:ít nhất một )?đơn",
    },
    "ERP-RK-02": {
        "sku": SKU, "product_name": NAME, "base_unit": UNIT,
        "quantity_sum": r"tổng|cộng", "ordered_measure": r"ordered|lượng đặt",
        "milli_unit": r"milli-unit", "rank": r"hạng|rank", "confirmed_only": CONFIRMED,
        "per_unit_partition": r"từng|mỗi đơn vị|cùng base unit|riêng",
        "cutoff": r"1.*3|ba hạng đầu|không quá 3", "ties": r"đồng hạng",
    },
    "ERP-JN-02": {
        "order_no": r"số đơn", "order_date": r"ngày đặt", "sku": SKU,
        "product_name": NAME, "ordered_qty": r"ordered|lượng đặt", "milli_unit": r"milli-unit",
        "net_vnd": r"ròng.*vnd|line net.*vnd", "line_grain": r"dòng|chi tiết",
        "confirmed_only": CONFIRMED,
    },
    "ERP-TM-02": {
        "local_date": r"ngày", "shipment_count": r"số (?:shipment|lượng shipment|lượt|lần)|đếm|bao nhiêu",
        "delivered": r"delivered", "local_year": r"2025",
        "timezone": r"việt nam|asia/ho_chi_minh", "event_time": r"delivered_at_utc|thời điểm giao|mốc giao",
        "no_scaffold": r"ngày có|ngày .*có shipment|không có shipment|ngày địa phương hiện diện|ngày có phát sinh",
    },
    "WMS-EF-01": {
        "document_id": DOCUMENT_ID, "document_no": DOCUMENT_NO, "document_type": DOCUMENT_TYPE,
        "document_status": STATUS, "business_date": r"business date|ngày nghiệp vụ", "posted": POSTED,
    },
    "WMS-EF-02": {
        "product_id": PRODUCT_ID, "sku": SKU, "name": NAME, "base_unit": UNIT,
        "category_id": r"category id|mã danh mục", "kg_filter": r"\bkg\b|kilogram",
        "null_preserved": r"null|nếu có",
    },
    "WMS-AG-02": {
        "product_id": PRODUCT_ID, "sku": SKU, "base_unit": UNIT, "sum_outgoing": r"tổng.*xuất",
        "unit": r"milli-kg", "negative_movement": r"movement âm|giảm tồn",
        "shipment": r"shipment", "posted": POSTED, "all_history": r"toàn bộ lịch sử|không giới hạn ngày",
    },
    "WMS-JN-04": {
        "document_id": DOCUMENT_ID, "document_no": DOCUMENT_NO,
        "line_no": r"line number|số dòng", "sku": SKU,
        "leg_number": r"leg number|số (?:thứ tự )?(?:leg|vế)", "leg_role": r"role|vai trò",
        "source_warehouse": r"warehouse nguồn|kho (?:nguồn|đi|xuất)",
        "destination_warehouse": r"nguồn/đích|kho (?:đích|đến|nhận)|và kho đến",
        "signed_quantity": r"signed quantity|có dấu", "unit": r"milli-unit", "timestamp": r"utc",
        "posted": POSTED, "transfer": r"transfer", "leg_grain": r"từng|mỗi",
    },
    "WMS-CD-02": {
        "document_id": DOCUMENT_ID, "document_no": DOCUMENT_NO, "document_type": DOCUMENT_TYPE,
        "status": STATUS, "sku": SKU, "base_unit": UNIT,
        "planned": r"planned|kế hoạch|dự kiến", "executed": r"executed|thực hiện",
        "unit": r"milli-unit", "all_statuses": r"mọi trạng thái|bất kể trạng thái|không lọc trạng thái",
        "zero_nonposted": r"0", "source_once": r"source.*(?:một lần|1 lần)",
        "other_posted_rules": r"(?:loại|posted).*khác.*(?:rules|quy tắc)|còn lại.*(?:rules|quy tắc)",
    },
}


def slot_evidence(group_id, wording):
    result = {}
    for name, pattern in CONTRACTS[group_id].items():
        match = re.search(pattern, wording, re.IGNORECASE)
        result[name] = match.group(0) if match else None
    return {"cues": result, "missing_cues": [key for key, value in result.items() if value is None],
            "interpretation": "LEXICAL_CUES_ONLY; human must check projection, scope, NULL, time and measure semantics"}


def editorial_markers(wording):
    return re.findall(r"\((?:lexical|syntactic|reordered|projection reordered|lexical \+ reordered)\)",
                      wording, re.IGNORECASE)
