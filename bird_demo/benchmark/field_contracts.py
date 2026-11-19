"""Output field contracts and explicit column aliases for BIRD-VN groups."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence

EVALUATION_PROTOCOL_VERSION = "0.4.0"
CONTRACT_VERSION = "field-contract-v1"
COMPARATOR_VERSION = "named-fields-order-insensitive-v1"

# Meanings are keyed by the output column names used by the canonical SQL.
# They explain semantics without changing the frozen physical schema.
FIELD_MEANINGS = {
    "all_net_movement_milli": "Tổng biến động kho có dấu, tính bằng phần nghìn đơn vị cơ sở.",
    "avg_location_on_hand_milli": "Lượng tồn trung bình trên mỗi vị trí thuộc nhóm được yêu cầu, tính bằng phần nghìn đơn vị cơ sở.",
    "avg_net_cash_vnd": "Tiền thuần trung bình trên mỗi đơn có khoản thu/hoàn đã ghi sổ, tính bằng VND.",
    "avg_order_value_vnd": "Giá trị đơn hàng trung bình theo phạm vi trạng thái và thời gian của câu hỏi, tính bằng VND.",
    "balance_state": "Nhãn phân biệt số dư ròng bằng 0 sau khi đã có biến động với trường hợp chưa từng có biến động.",
    "base_unit": "Đơn vị cơ sở của sản phẩm; không cộng gộp lượng giữa các đơn vị khác nhau.",
    "business_date": "Ngày nghiệp vụ ghi trên chứng từ kho; không đồng nhất với thời điểm tạo chứng từ.",
    "cash_state": "Nhãn trạng thái tiền thuần theo quy tắc phân loại riêng của Intent.",
    "category_id": "ID nội bộ của danh mục sản phẩm; không phải mã danh mục nghiệp vụ.",
    "confirmed_order_count": "Số đơn hàng có trạng thái CONFIRMED trong nhóm tương ứng.",
    "customer_code": "Mã khách hàng nghiệp vụ, dùng để nhận diện khách hàng với người dùng.",
    "customer_count": "Số khách hàng phân biệt trong từng nhóm kết quả.",
    "customer_id": "ID nội bộ của khách hàng, dùng làm khóa liên kết; không phải customer_code.",
    "customer_name": "Tên khách hàng.",
    "delivered_date_local": "Ngày giao hàng theo giờ Việt Nam, ở mức từng đơn hàng.",
    "delivered_local_date": "Ngày giao hàng sau khi đổi timestamp UTC sang giờ Việt Nam.",
    "delivered_shipment_count": "Số lần giao hàng hoàn tất trong ngày địa phương tương ứng.",
    "delivery_month_local": "Tháng giao hàng theo giờ Việt Nam.",
    "destination_warehouse": "Mã kho đích của nhánh biến động chuyển kho.",
    "document_count": "Số chứng từ trong nhóm kết quả.",
    "document_id": "ID nội bộ của chứng từ kho; không phải document_no.",
    "document_no": "Số chứng từ nghiệp vụ hiển thị cho người dùng.",
    "document_status": "Trạng thái chứng từ kho, ví dụ DRAFT, POSTED hoặc CANCELLED.",
    "document_type": "Loại chứng từ kho, ví dụ RECEIPT, SHIPMENT, TRANSFER hoặc ADJUSTMENT.",
    "executed_qty_milli": "Lượng thực hiện theo quy tắc WMS-CD-02, tính bằng phần nghìn đơn vị cơ sở.",
    "full_name": "Họ tên nhân viên.",
    "line_no": "Số thứ tự dòng trong chứng từ; không phải ID nội bộ của dòng.",
    "location_code": "Mã vị trí kho nghiệp vụ.",
    "location_id": "ID nội bộ của vị trí kho; không phải location_code.",
    "location_type": "Loại vị trí kho, ví dụ STORAGE, PICKING hoặc QUARANTINE.",
    "locations_below_mean": "Số vị trí có lượng tồn thấp hơn mức trung bình của cùng sản phẩm, đơn vị và kho.",
    "metric": "Tên loại giá trị tiền được báo cáo ở dòng đó; cần đọc cùng value_vnd.",
    "moved_at_utc": "Thời điểm biến động kho theo UTC.",
    "movement_id": "ID nội bộ của bản ghi biến động kho.",
    "movement_leg_no": "Số thứ tự nhánh biến động trong chứng từ; không phải movement_id.",
    "movement_role": "Vai trò của nhánh chuyển kho, chẳng hạn SOURCE hoặc DESTINATION.",
    "net_cash_vnd": "Tiền thuần đã ghi sổ, bằng khoản thu trừ khoản hoàn theo quy tắc Intent, tính bằng VND.",
    "net_movement_qty_milli": "Tổng lượng biến động kho có dấu theo nhóm kết quả, tính bằng phần nghìn đơn vị cơ sở.",
    "net_qty_milli": "Lượng biến động ròng có dấu, tính bằng phần nghìn đơn vị cơ sở.",
    "net_vnd": "Giá trị ròng sau giảm giá, tính bằng VND.",
    "on_hand_change_milli": "Thay đổi lượng tồn từ các biến động trong phạm vi truy vấn, tính bằng phần nghìn đơn vị cơ sở.",
    "on_hand_milli": "Lượng tồn ròng, tính bằng phần nghìn đơn vị cơ sở.",
    "order_count": "Số đơn hàng trong nhóm kết quả.",
    "order_date": "Ngày nghiệp vụ đặt hàng; không thay bằng created_at_utc.",
    "order_id": "ID nội bộ của đơn hàng; không phải order_no.",
    "order_no": "Số đơn hàng nghiệp vụ hiển thị cho người dùng.",
    "order_status": "Trạng thái đơn hàng, ví dụ DRAFT, CONFIRMED hoặc CANCELLED.",
    "order_value_vnd": "Tổng giá trị hàng hóa sau giảm giá của đơn theo quy tắc Intent, tính bằng VND.",
    "ordered_qty_milli": "Số lượng đặt hàng, tính bằng phần nghìn đơn vị cơ sở.",
    "payment_method": "Phương thức thanh toán.",
    "planned_qty_milli": "Số lượng theo kế hoạch trên chứng từ, tính bằng phần nghìn đơn vị cơ sở.",
    "posted_capture_vnd": "Tổng khoản thu đã ghi sổ, tính bằng VND.",
    "posted_net_cash_vnd": "Tổng tiền thuần đã ghi sổ, bằng khoản thu trừ khoản hoàn, tính bằng VND.",
    "posted_receipt_count": "Số chứng từ nhập kho đã ghi sổ.",
    "posted_refund_vnd": "Tổng khoản hoàn tiền đã ghi sổ, tính bằng VND.",
    "product_id": "ID nội bộ của sản phẩm; không phải SKU.",
    "product_name": "Tên sản phẩm.",
    "qty_delta_milli": "Lượng biến động có dấu, tính bằng phần nghìn đơn vị cơ sở.",
    "receipt_count": "Số chứng từ nhập kho trong nhóm nhà cung cấp tương ứng.",
    "received_return_qty_milli": "Số lượng hàng trả đã được nhận, tính bằng phần nghìn đơn vị cơ sở.",
    "recognized_revenue_vnd": "Doanh thu được ghi nhận theo quy tắc giao hàng của benchmark, tính bằng VND.",
    "revenue_rank": "Thứ hạng khách hàng theo doanh thu được ghi nhận trong phạm vi Intent.",
    "revenue_vnd": "Doanh thu được ghi nhận của khách hàng, tính bằng VND.",
    "rnk": "Thứ hạng theo tiêu chí xếp hạng đã nêu trong Intent; tie policy được giữ nguyên.",
    "sales_rep_id": "ID nội bộ của nhân viên phụ trách bán hàng; khóa liên kết tới EMPLOYEES.employee_id, không phải employee_code.",
    "segment": "Phân khúc khách hàng.",
    "shipped_qty_milli": "Tổng lượng xuất dương từ chứng từ SHIPMENT đã ghi sổ, tính bằng phần nghìn đơn vị cơ sở.",
    "sku": "Mã SKU nghiệp vụ của sản phẩm; không phải product_id.",
    "sold_qty_milli": "Tổng lượng đặt đã bán theo phạm vi Intent, tính bằng phần nghìn đơn vị cơ sở.",
    "source_warehouse": "Mã kho nguồn của nhánh biến động chuyển kho.",
    "supplier_id": "ID nội bộ của nhà cung cấp; không phải supplier_code.",
    "supplier_name": "Tên nhà cung cấp.",
    "value_vnd": "Giá trị tiền theo loại metric ở cột metric, tính bằng VND.",
    "warehouse_code": "Mã kho nghiệp vụ.",
    "warehouse_id": "ID nội bộ của kho; không phải warehouse_code.",
    "warehouse_name": "Tên kho.",
}

# A result-column alias is accepted only in the intent where its meaning is
# unambiguous. No global guessing is performed for generic names such as id/code.
GROUP_COLUMN_ALIASES = {
    "ERP-GB-03": {"employee_id": "sales_rep_id"},
}


def make_output_contract(
    group_id: str,
    columns: Sequence[str],
    card_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fields = []
    unresolved = []
    for column in columns:
        meaning = FIELD_MEANINGS.get(column)
        if meaning is None:
            unresolved.append(column)
            meaning = "Chưa có mô tả chuẩn cho trường này; cần bổ sung trước khi chấm chính thức."
        if column in {"rnk", "revenue_rank"} and card_fields:
            meaning += f" Tiêu chí Intent: {card_fields.get('brief', '')}"
            tie = card_fields.get("null_tie")
            if tie:
                meaning += f" Quy tắc đồng hạng: {tie}"
        if column in {"metric", "value_vnd"} and card_fields:
            meaning += f" Ngữ cảnh Intent: {card_fields.get('brief', '')}"
        fields.append({"column": column, "meaning": meaning})
    return {
        "version": CONTRACT_VERSION,
        "comparator_version": COMPARATOR_VERSION,
        "group_id": group_id,
        "fields": fields,
        "columns": [str(column) for column in columns],
        "aliases": dict(GROUP_COLUMN_ALIASES.get(group_id, {})),
        "column_order_required": False,
        "unresolved_fields": unresolved,
        "status": "NEEDS_FIELD_REVIEW" if unresolved else "PROVISIONAL_FROM_CANONICAL_PROJECTION",
        # Projection-derived contracts are useful prompt guidance, but remain
        # provisional until the Benchmark Owner confirms them against the Intent.
        "owner_review_status": "PENDING",
    }


def output_contract_sha256(contract: dict[str, Any]) -> str:
    """Hash the stable semantic contract, excluding mutable review metadata."""
    payload = {
        key: value for key, value in contract.items()
        if key not in {"owner_review_status", "contract_sha256"}
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def bind_output_contract(contract: dict[str, Any], group: dict[str, Any]) -> dict[str, Any]:
    """Attach source SQL hash and only accept review provenance for this exact contract."""
    bound = dict(contract)
    sql = group.get("canonical_sql_draft") or group.get("canonical_sql") or ""
    bound["source_canonical_sql_sha256"] = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    bound["contract_sha256"] = output_contract_sha256(bound)
    review = group.get("output_contract_review", {})
    bound["owner_review_status"] = (
        "APPROVED"
        if review.get("status") == "APPROVED"
        and review.get("contract_sha256") == bound["contract_sha256"]
        and review.get("reviewer")
        and review.get("approved_on")
        and review.get("rationale")
        else "PENDING"
    )
    return bound


def align_result(
    rows: Sequence[Sequence[Any]],
    columns: Sequence[str] | None,
    expected_columns: Sequence[str],
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Align a result to the named field contract, ignoring only column order."""
    expected = [str(item).strip().casefold() for item in expected_columns]
    if columns is None:
        return {"valid": False, "status": "missing_column_metadata", "missing": list(expected_columns), "extra": [], "aliases_applied": [], "rows": None}
    if len(expected) != len(set(expected)):
        return {"valid": False, "status": "duplicate_contract_fields", "missing": [], "extra": [], "aliases_applied": [], "rows": None}

    alias_map = {str(alias).strip().casefold(): str(target).strip().casefold()
                 for alias, target in (aliases or {}).items()}
    expected_set = set(expected)
    mapped: list[str | None] = []
    aliases_applied = []
    extra = []
    for raw in columns:
        name = str(raw).strip().casefold()
        target = name if name in expected_set else alias_map.get(name)
        if target not in expected_set:
            mapped.append(None)
            extra.append(str(raw))
            continue
        mapped.append(target)
        if target != name:
            aliases_applied.append({"generated": str(raw), "canonical": target})

    mapped_names = [name for name in mapped if name is not None]
    duplicates = sorted({name for name in mapped_names if mapped_names.count(name) > 1})
    present = set(mapped_names)
    missing = [str(expected_columns[index]) for index, name in enumerate(expected) if name not in present]
    if extra or duplicates or missing:
        status = "ambiguous_or_duplicate_mapping" if duplicates else "projection_mismatch"
        return {"valid": False, "status": status, "missing": missing, "extra": extra,
                "duplicate_fields": duplicates, "aliases_applied": aliases_applied, "rows": None}

    if any(len(row) != len(columns) for row in rows):
        return {"valid": False, "status": "row_arity_mismatch", "missing": [], "extra": [],
                "duplicate_fields": [], "aliases_applied": aliases_applied, "rows": None}
    positions = {name: index for index, name in enumerate(mapped_names)}
    normalized = [[row[positions[name]] for name in expected] for row in rows]
    return {"valid": True, "status": "matched" if not aliases_applied else "matched_with_declared_alias",
            "missing": [], "extra": [], "duplicate_fields": [], "aliases_applied": aliases_applied,
            "column_order_match": [str(item).strip().casefold() for item in columns] == expected,
            "rows": normalized}


def compare_named_results(
    predicted_rows: Sequence[Sequence[Any]],
    predicted_columns: Sequence[str] | None,
    expected_rows: Sequence[Sequence[Any]],
    expected_columns: Sequence[str],
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    predicted = align_result(predicted_rows, predicted_columns, expected_columns, aliases)
    expected = align_result(expected_rows, expected_columns, expected_columns)
    if not expected["valid"]:
        raise ValueError("Canonical result does not match its own output field contract")
    equal = bool(
        predicted["valid"]
        and set(map(tuple, predicted["rows"])) == set(map(tuple, expected["rows"]))
    )
    return {
        "correct": equal,
        "projection_valid": predicted["valid"],
        "projection_status": predicted["status"],
        "projection_missing": predicted.get("missing", []),
        "projection_extra": predicted.get("extra", []),
        "projection_duplicate_fields": predicted.get("duplicate_fields", []),
        "aliases_applied": predicted.get("aliases_applied", []),
        "column_order_match": predicted.get("column_order_match"),
        "normalized_rows": predicted.get("rows"),
        "expected_normalized_rows": expected["rows"],
    }
