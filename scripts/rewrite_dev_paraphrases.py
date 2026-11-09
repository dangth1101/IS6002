"""Replace templated Development wording with hand-authored draft variants.

No model/API calls. Final split, SQL, expected outputs and frozen DBs are untouched.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "benchmark_data/authoring"
REGISTRY_PATH = AUTH / "dataset.json"
RECORDS_PATH = AUTH / "validation_records.json"
GROUND_PATH = AUTH / "ground_truth_validation.json"
EXPECTED_PATH = AUTH / "expected_outputs_dev.json"
OUT = ROOT / "docs/benchmark/review/dev_human_approval"
ARCHIVE = OUT / "archive_v1_generic_wrappers"

# Each wording is drafted for the specified transformation; mixed rows state
# both transformations in secondary_tags for reviewer visibility.
CARDS = {
"ERP-EF-01": {
"q0":"Liệt kê từng đơn hàng ở trạng thái CONFIRMED, kèm mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái.",
"variants":[
("Cho biết các đơn hàng đã xác nhận; với mỗi đơn, nêu mã đơn, số đơn, mã khách, ngày đặt và trạng thái.","lexical",[]),
("Những đơn bán hàng nào đã được xác nhận? Trả về mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái của từng đơn.","lexical",[]),
("Tra cứu các đơn ở trạng thái CONFIRMED, gồm mã đơn, số đơn, khách hàng, ngày đặt và trạng thái.","lexical",[]),
("Mỗi đơn CONFIRMED gồm mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái là gì?", "syntactic",[]),
("Cần danh sách đơn CONFIRMED với năm trường: mã đơn, số đơn, mã khách hàng, ngày đặt, trạng thái.","syntactic",[]),
("Hãy trả về các bộ thông tin (mã đơn, số đơn, mã khách hàng, ngày đặt, trạng thái) cho những đơn có trạng thái CONFIRMED.","syntactic",[]),
("Với mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái cần hiển thị, hãy lọc những đơn có trạng thái CONFIRMED.","reordering",[]),
("Trạng thái cần xét là CONFIRMED; trong toàn bộ đơn hàng, liệt kê mã đơn, số đơn, mã khách hàng và ngày đặt cùng trạng thái.","reordering",[]),
("Tìm các đơn bán đã được chốt (lexical), rồi trình bày từng đơn dưới dạng mã đơn, số đơn, mã khách hàng, ngày đặt và trạng thái (projection reordered).","mixed",["lexical","reordering"]),
("Trả về mỗi đơn ở trạng thái CONFIRMED dưới dạng mã đơn, số đơn, mã khách hàng, ngày đặt, trạng thái; đây là các đơn đã xác nhận.","mixed",["syntactic","reordering"]),
]},
"ERP-GB-03": {
"q0":"Với mỗi sales rep có confirmed orders, kể cả một nhóm riêng cho sales rep chưa gán (NULL), cho biết mã sales rep, tên nếu có và số đơn CONFIRMED trong toàn bộ dữ liệu.",
"variants":[
("Theo từng nhân viên kinh doanh có đơn đã xác nhận, kể cả nhóm chưa phân công, cho biết mã, tên nếu có và số đơn.","lexical",[]),
("Thống kê số đơn CONFIRMED của từng sales rep; giữ cả nhóm chưa được gán nhân viên và trả mã, tên nếu có.","lexical",[]),
("Cho biết mỗi người phụ trách bán hàng có bao nhiêu đơn ở trạng thái xác nhận, kể cả phần chưa gán; kèm mã và tên nếu có.","lexical",[]),
("Mỗi nhóm sales rep (kể cả NULL chưa gán) có mã nào, tên nào nếu có, và bao nhiêu confirmed orders?","syntactic",[]),
("Hãy lập bảng theo sales rep, gồm mã rep, tên nếu có và số đơn CONFIRMED; biểu diễn giá trị NULL thành nhóm chưa gán.","syntactic",[]),
("Cần một dòng cho mỗi sales rep có đơn đã xác nhận (kể cả NULL): mã rep, tên nếu có, tổng số đơn.","syntactic",[]),
("Trước hết xét mọi đơn không giới hạn thời gian và chỉ giữ CONFIRMED; sau đó nhóm theo sales rep, gồm NULL, rồi trả mã, tên nếu có và số đơn.","reordering",[]),
("Kết quả cần mã sales rep, tên nếu có và số đơn. Hãy đếm trên các đơn CONFIRMED theo từng rep, đồng thời giữ nhóm NULL chưa gán.","reordering",[]),
("Phân nhóm theo người phụ trách bán hàng (cả nhóm chưa phân công), rồi cho biết mã/tên nếu có và số đơn đã xác nhận (lexical + reordered).","mixed",["lexical","reordering"]),
("Bao nhiêu đơn CONFIRMED thuộc từng sales rep, tính cả nhóm NULL? Trình bày mỗi nhóm thành mã rep, tên nếu có và số lượng đơn.","mixed",["syntactic","reordering"]),
]},
"ERP-RK-02": {
"q0":"Trong từng base unit riêng biệt, xếp hạng mỗi SKU theo tổng ordered quantity của các đơn CONFIRMED; trả SKU, tên sản phẩm, base unit, tổng lượng (milli-unit) và hạng, lấy mọi hạng từ 1 đến 3 kể cả đồng hạng ở mốc 3.",
"variants":[
("Riêng trong từng đơn vị cơ sở, xếp các SKU theo tổng số lượng đặt ở đơn đã xác nhận; nêu SKU, tên, đơn vị, tổng milli-unit và hạng, giữ mọi đồng hạng ở vị trí ba.","lexical",[]),
("Với mỗi base unit, tìm các mã hàng dẫn đầu theo lượng bán trong confirmed orders: mã SKU, tên, đơn vị, tổng lượng milli-unit và thứ hạng; lấy top ba kể cả hòa ở hạng ba.","lexical",[]),
("Xếp từng mặt hàng theo tổng lượng ordered trong các đơn được xác nhận, tách riêng từng đơn vị cơ sở; hiển thị SKU, tên, đơn vị, tổng milli-unit và hạng 1–3 cùng mọi trường hợp đồng hạng tại cutoff.","lexical",[]),
("Những SKU nào đứng trong ba hạng đầu của từng base unit nếu cộng ordered quantity trên các đơn CONFIRMED? Với mỗi SKU, cho biết tên, đơn vị, tổng milli-unit và rank; không bỏ đồng hạng hạng ba.","syntactic",[]),
("Hãy lập bảng xếp hạng riêng theo base unit từ lượng ordered của đơn CONFIRMED. Mỗi dòng gồm SKU, tên sản phẩm, đơn vị, tổng milli-unit và hạng; bao gồm toàn bộ tie ở hạng 3.","syntactic",[]),
("Cần chọn mọi SKU có rank không quá 3 trong cohort cùng base unit, tính rank từ tổng ordered quantity của confirmed orders; trả tên, SKU, đơn vị, tổng milli-unit và rank, giữ ties tại 3.","syntactic",[]),
("Trước tiên tách sản phẩm theo base unit, rồi trong mỗi nhóm xếp theo tổng ordered milli-unit giảm dần trên confirmed orders; trả SKU, tên, đơn vị, tổng và hạng, gồm mọi tie ở hạng ba.","reordering",[]),
("Chỉ dùng dòng hàng thuộc đơn CONFIRMED và cộng quantity theo SKU. Sau đó xếp hạng độc lập trong từng đơn vị cơ sở; kết quả cần SKU, tên, đơn vị, tổng milli-unit, hạng 1–3 và mọi tie tại hạng ba.","reordering",[]),
("Trong mỗi cohort đơn vị cơ sở, hãy xếp các mặt hàng dẫn đầu (lexical) theo tổng lượng ordered ở đơn đã chốt; xuất SKU/tên/đơn vị/tổng milli-unit/hạng và giữ đồng hạng thứ ba (syntactic).","mixed",["lexical","syntactic"]),
("Hãy trả trước SKU, tên, đơn vị, tổng ordered milli-unit và thứ hạng: dùng các đơn CONFIRMED, cộng theo SKU, phân hạng riêng mỗi base unit và giữ mọi trường hợp hòa tại hạng 3 (lexical + reordered).","mixed",["lexical","reordering"]),
]},
"ERP-JN-02": {
"q0":"Liệt kê từng dòng của mọi đơn CONFIRMED, một dòng cho mỗi order line, gồm số đơn, ngày đặt, SKU, tên sản phẩm, ordered quantity theo milli-unit và line net theo VND.",
"variants":[
("Cho xem chi tiết từng dòng hàng thuộc đơn đã xác nhận: số đơn, ngày đặt, mã và tên SKU, lượng đặt milli-unit cùng giá trị ròng dòng hàng VND.","lexical",[]),
("Tra cứu các order line của đơn CONFIRMED, mỗi dòng kèm số đơn, ngày đặt, SKU/tên sản phẩm, số lượng đặt milli-unit và net amount VND.","lexical",[]),
("Hiển thị các dòng sản phẩm trong đơn bán đã chốt; cần số đơn, ngày đơn, mã/tên mặt hàng, ordered quantity milli-unit và line net bằng VND.","lexical",[]),
("Mỗi order line trong đơn CONFIRMED có số đơn, ngày đặt, SKU, tên sản phẩm, ordered quantity milli-unit và line net VND nào?","syntactic",[]),
("Hãy tạo danh sách ở cấp dòng đơn hàng. Với đơn đã xác nhận, trình bày số đơn, ngày đặt, mã SKU, tên sản phẩm, lượng đặt milli-unit và giá trị ròng VND.","syntactic",[]),
("Cần các bộ (số đơn, ngày đặt, SKU, tên sản phẩm, ordered quantity milli-unit, line net VND) cho tất cả order line thuộc đơn CONFIRMED.","syntactic",[]),
("Chỉ giữ đơn có trạng thái CONFIRMED; sau đó mở rộng đến từng order line và ghép sản phẩm, trả số đơn/ngày đặt, SKU/tên, lượng đặt milli-unit và line net VND.","reordering",[]),
("Đầu ra cần số đơn, ngày đặt, SKU, tên sản phẩm, ordered quantity milli-unit và line net VND. Hãy lấy ở grain từng dòng hàng, chỉ từ các đơn đã xác nhận.","reordering",[]),
("Với từng chi tiết đơn bán đã chốt (lexical), nối thông tin mặt hàng và trình bày bộ số đơn, ngày, SKU/tên, lượng milli-unit, net VND (syntactic).","mixed",["lexical","syntactic"]),
("Trả trước projection gồm order number/date, SKU/name, ordered milli-quantity và net VND cho mỗi dòng hàng; lọc các đơn có trạng thái CONFIRMED (lexical + reordering).","mixed",["lexical","reordering"]),
]},
"ERP-TM-02": {
"q0":"Cho mỗi ngày Việt Nam trong năm 2025 có ít nhất một shipment DELIVERED, trả ngày địa phương và số shipment; dùng delivered_at_utc quy đổi sang Asia/Ho_Chi_Minh, khoảng [2025-01-01, 2026-01-01), không tạo dòng cho ngày không có shipment.",
"variants":[
("Thống kê theo ngày giờ Việt Nam số chuyến đã giao trong năm 2025; chỉ hiện ngày có chuyến, lấy ngày từ delivered timestamp UTC và đếm shipment.","lexical",[]),
("Mỗi ngày địa phương có giao hàng thành công trong 2025 có bao nhiêu shipment? Dùng mốc delivered, đổi UTC sang Asia/Ho_Chi_Minh và không thêm ngày có số 0.","lexical",[]),
("Đếm các lô giao đã hoàn tất theo ngày Việt Nam trong năm 2025, dựa vào delivered_at_utc; chỉ trả ngày phát sinh ít nhất một shipment.","lexical",[]),
("Ngày địa phương nào trong khoảng năm 2025 có shipment ở trạng thái DELIVERED, và mỗi ngày có bao nhiêu shipment? Diễn giải ngày theo Asia/Ho_Chi_Minh.","syntactic",[]),
("Hãy lập bảng ngày–số chuyến giao: đổi delivered_at_utc sang giờ Việt Nam, lọc năm 2025 theo [01/01/2025, 01/01/2026), chỉ giữ ngày có dữ liệu.","syntactic",[]),
("Cần số lượng shipment DELIVERED cho từng ngày địa phương hiện diện trong dữ liệu năm 2025; ngày lấy từ thời điểm giao UTC quy đổi sang giờ Việt Nam.","syntactic",[]),
("Dùng delivered_at_utc và trạng thái DELIVERED để chọn khoảng local-year 2025 trước; sau đó nhóm theo ngày Asia/Ho_Chi_Minh và đếm shipment, không scaffold ngày rỗng.","reordering",[]),
("Kết quả gồm ngày Việt Nam và số shipment. Chỉ tính mốc giao trong [2025-01-01, 2026-01-01) theo giờ địa phương, đổi từ UTC, và chỉ nhóm ngày có shipment DELIVERED.","reordering",[]),
("Tổng hợp các đơn vị giao đã hoàn tất (lexical) mỗi ngày theo giờ Việt Nam; dùng delivered time UTC và lọc local-year 2025, chỉ xuất các ngày có chuyến cùng số lượng (syntactic).","mixed",["lexical","syntactic"]),
("Trước hết chọn event DELIVERED trong năm địa phương 2025, rồi đếm shipment theo ngày sau quy đổi UTC→Asia/Ho_Chi_Minh; trả ngày và count, không sinh ngày 0 (lexical + reordered).","mixed",["lexical","reordering"]),
]},
"WMS-EF-01": {
"q0":"Liệt kê từng inventory document có document_status POSTED, gồm document ID, document number, document type, trạng thái và business date.",
"variants":[
("Cho biết các chứng từ kho đã ghi nhận ở trạng thái POSTED; mỗi dòng cần ID, số chứng từ, loại, trạng thái và ngày nghiệp vụ.","lexical",[]),
("Tra cứu inventory documents đã hạch toán, kèm document ID/no, document type, status và business date.","lexical",[]),
("Những phiếu kho nào đã được ghi sổ? Trả mã chứng từ, số chứng từ, loại chứng từ, trạng thái và ngày nghiệp vụ.","lexical",[]),
("Mỗi inventory document POSTED có ID, số hiệu, loại, status và business date nào?","syntactic",[]),
("Hãy lập danh sách ở grain một chứng từ kho; chỉ chọn POSTED và hiển thị document ID, number, type, status, business date.","syntactic",[]),
("Cần các bộ thông tin (ID, số chứng từ, loại, trạng thái, ngày nghiệp vụ) của tất cả chứng từ kho có status POSTED.","syntactic",[]),
("Lọc trạng thái document là POSTED trước; sau đó trả ID/số chứng từ, loại, trạng thái và business date cho từng chứng từ.","reordering",[]),
("Đầu ra cần document ID, document number, document type, status và business date. Trong toàn bộ chứng từ kho, chỉ lấy những dòng POSTED.","reordering",[]),
("Liệt kê các phiếu kho đã ghi sổ (lexical), mỗi phiếu là một dòng gồm ID, số hiệu, loại, trạng thái và business date (syntactic).","mixed",["lexical","syntactic"]),
("Trả projection ID/no/type/status/business date cho từng chứng từ; trước tiên giới hạn inventory document ở trạng thái POSTED (lexical + reordered).","mixed",["lexical","reordering"]),
]},
"WMS-EF-02": {
"q0":"Liệt kê từng product có base_unit KG, gồm product ID, SKU, tên sản phẩm, base unit và category ID (giữ NULL nếu chưa phân loại).",
"variants":[
("Cho xem các mặt hàng đo theo kilogram (KG), mỗi SKU kèm product ID, tên, đơn vị cơ sở và category ID nếu có.","lexical",[]),
("Tra cứu sản phẩm có đơn vị chuẩn là KG; trả ID sản phẩm, mã SKU, tên, base unit và mã danh mục, kể cả danh mục NULL.","lexical",[]),
("Những SKU nào dùng KG làm đơn vị cơ sở? Với mỗi mặt hàng, nêu product ID, tên hàng, đơn vị và category ID nếu được gán.","lexical",[]),
("Mỗi product có base_unit KG mang product ID, SKU, tên, category ID nào? Giữ nguyên NULL ở category nếu chưa phân loại.","syntactic",[]),
("Hãy lập danh sách sản phẩm theo grain một product, chỉ gồm đơn vị KG; các cột là ID, SKU, tên, base unit và category ID.","syntactic",[]),
("Cần các bộ (product ID, SKU, tên, base unit, category ID) sau khi lọc sản phẩm có đơn vị cơ sở KG; category chưa gán vẫn để NULL.","syntactic",[]),
("Trước hết chọn base_unit='KG'; từ mỗi product được chọn, xuất product ID, SKU, tên, đơn vị và category ID, không loại NULL category.","reordering",[]),
("Kết quả cần ID sản phẩm, SKU, tên, base unit và category ID. Trong catalog, chỉ lấy product đo bằng KG và giữ product chưa có category.","reordering",[]),
("Tìm các mặt hàng tính theo kilogram (lexical), rồi trình bày ID/SKU/tên/đơn vị/category ID, kể cả category chưa gán (syntactic).","mixed",["lexical","syntactic"]),
("Trả product ID, SKU, tên, base unit và category ID; bộ lọc catalog là KG, còn NULL category vẫn được giữ (lexical + reordered).","mixed",["lexical","reordering"]),
]},
"WMS-AG-02": {
"q0":"Với mỗi product có base_unit KG và phát sinh ít nhất một movement âm thuộc chứng từ SHIPMENT đã POSTED trong toàn bộ lịch sử, trả product ID, SKU, base unit và tổng lượng xuất (milli-KG).",
"variants":[
("Tổng hợp lượng hàng xuất giao khách đã ghi sổ cho từng SKU tính bằng KG; nêu product ID, SKU, base unit và tổng milli-KG trên toàn bộ lịch sử.","lexical",[]),
("Cho biết mỗi mặt hàng đơn vị KG đã giao khách bao nhiêu lượng: chỉ tính movement âm của SHIPMENT POSTED và trả ID, SKU, đơn vị, tổng milli-KG.","lexical",[]),
("Tính tổng lượng xuất kho cho khách của từng SKU cơ sở KG từ các shipment đã hạch toán; hiển thị product ID, SKU, base unit và milli-KG.","lexical",[]),
("Mỗi SKU KG có bao nhiêu milli-KG đã xuất cho khách qua SHIPMENT POSTED? Trả product ID, mã SKU, base unit và tổng lượng.","syntactic",[]),
("Hãy lập một dòng cho mỗi SKU KG có outbound shipment movement: cộng độ lớn các delta âm của chứng từ SHIPMENT đã POSTED trong toàn lịch sử.","syntactic",[]),
("Cần tổng lượng giao theo product ở đơn vị milli-KG, cùng product ID/SKU/base unit; chỉ xét các movement âm thuộc shipment đã ghi sổ.","syntactic",[]),
("Trước tiên giới hạn chứng từ vào SHIPMENT POSTED và movement âm; kế đó chọn product base_unit KG, nhóm theo SKU rồi cộng lượng xuất milli-unit.","reordering",[]),
("Kết quả cần product ID, SKU, base unit và tổng shipped milli-KG. Chỉ nhóm các sản phẩm KG có phát sinh shipment movement âm đã POSTED, không giới hạn ngày.","reordering",[]),
("Cộng lượng giao khách đã hoàn tất (lexical) cho mỗi SKU KG, dùng riêng movement âm của shipment đã ghi sổ; trả ID/SKU/unit/tổng milli-KG (syntactic).","mixed",["lexical","syntactic"]),
("Chỉ chọn shipment POSTED có delta âm trên SKU KG, rồi tổng hợp theo product (reordered); xuất product ID, SKU, đơn vị và tổng lượng milli-KG đã xuất (lexical).","mixed",["lexical","reordering"]),
]},
"WMS-JN-04": {
"q0":"Liệt kê từng movement leg của mỗi chứng từ TRANSFER POSTED, một dòng mỗi leg; gồm document ID/no, line number, SKU, leg number/role, warehouse nguồn/đích, signed quantity milli-unit và thời điểm movement UTC.",
"variants":[
("Cho xem từng chân movement của lệnh chuyển kho đã ghi sổ, với ID/số chứng từ, dòng, SKU, số thứ tự/vai trò leg, kho đi/đến, delta milli-unit có dấu và timestamp UTC.","lexical",[]),
("Tra cứu các inventory transfer POSTED ở mức từng leg; cần mã/số chứng từ, line, SKU, leg no/role, warehouse nguồn-đích, lượng signed milli-unit và moved_at UTC.","lexical",[]),
("Mỗi chân luân chuyển giữa kho trong chứng từ đã hạch toán cần hiện document ID/no, line no, SKU, leg no và role, kho nguồn/đích, signed milli-quantity, thời điểm UTC.","lexical",[]),
("Với từng leg của TRANSFER POSTED, document nào và line nào liên quan, SKU gì, leg number/role ra sao, kho nguồn/đích nào, delta milli-unit và thời điểm UTC là bao nhiêu?","syntactic",[]),
("Hãy tạo bảng ở grain một movement leg, chỉ từ transfer đã ghi sổ; các cột gồm document ID/no, line, SKU, leg no/role, source/destination warehouse, signed qty milli-unit và moved_at UTC.","syntactic",[]),
("Cần các bộ thông tin chi tiết cho mọi transfer leg POSTED: chứng từ, số dòng, SKU, nhận diện/vai trò leg, hai warehouse, lượng có dấu và timestamp UTC.","syntactic",[]),
("Lọc chứng từ TRANSFER có status POSTED trước, rồi theo từng movement leg nối document line, product và location; trả mã chứng từ/line/SKU, vai trò leg, hai kho, delta và giờ UTC.","reordering",[]),
("Đầu ra cần document ID/no, line number, SKU, leg number/role, kho nguồn/đích, signed milli-quantity và thời điểm UTC. Mỗi row là một leg thuộc transfer đã POSTED.","reordering",[]),
("Liệt kê từng chân luân chuyển kho (lexical) của chứng từ đã ghi sổ, rồi nối chi tiết SKU/kho và trả signed quantity cùng thời gian UTC (syntactic).","mixed",["lexical","syntactic"]),
("Mỗi row tương ứng một movement leg; trước hết giới hạn transfer POSTED, sau đó xuất chứng từ/line/SKU/leg-role/kho nguồn-đích/signed milli-qty/timestamp UTC (lexical + reordered).","mixed",["lexical","reordering"]),
]},
"WMS-CD-02": {
"q0":"Với mọi cặp document × SKU, bất kể trạng thái, trả document ID/no/type/status, SKU, base unit, planned quantity và executed quantity theo milli-unit; executed bằng 0 nếu document chưa POSTED, TRANSFER chỉ tính SOURCE leg một lần, loại POSTED khác theo movement rules đã chốt.",
"variants":[
("Đối chiếu lượng dự kiến với lượng thực hiện cho từng SKU trên từng chứng từ kho; giữ cả DRAFT, POSTED, CANCELLED, đơn vị milli-unit và quy ước transfer lấy SOURCE một lần.","lexical",[]),
("Theo từng document và SKU, cho biết planned so với executed quantity (milli-unit), kèm trạng thái/loại chứng từ và base unit; chứng từ chưa ghi sổ có executed bằng 0.","lexical",[]),
("Tra cứu chênh lệch giữa lượng kế hoạch và lượng đã phát sinh ở mỗi cặp chứng từ–SKU, gồm đủ trạng thái; transfer đếm leg nguồn một lần, các loại đã POSTED khác theo movement rules.","lexical",[]),
("Mỗi cặp document × SKU có ID/số chứng từ, type/status, SKU/base unit, planned milli-quantity và executed milli-quantity nào? Với status khác POSTED, executed là 0.","syntactic",[]),
("Hãy lập bảng đối chiếu ở grain document–SKU, bao gồm mọi trạng thái. Trình bày định danh chứng từ, SKU, đơn vị, lượng planned và executed theo milli-unit; transfer lấy SOURCE leg, non-POSTED bằng 0.","syntactic",[]),
("Cần kết quả cho mọi chứng từ và SKU, không lọc status: mã/no/type/status, SKU/base unit, planned quantity và executed quantity. Tính transfer từ SOURCE một lần; các loại POSTED còn lại theo quy tắc movement.","syntactic",[]),
("Giữ trước tất cả document status và tính planned quantity theo document × SKU; sau đó lấy executed từ movement POSTED, dùng SOURCE một lần cho TRANSFER, rồi trả định danh chứng từ/SKU/unit và cả hai lượng milli-unit.","reordering",[]),
("Đầu ra gồm document ID/no/type/status, SKU, base unit, planned và executed milli-unit. Quy tắc: non-POSTED có executed=0; transfer POSTED lấy SOURCE, các document type khác theo movement rules.","reordering",[]),
("So sánh lượng dự kiến với lượng đã ghi nhận cho từng cặp chứng từ–mặt hàng (lexical), giữ cả trạng thái; transfer chỉ tính leg nguồn một lần và trạng thái chưa POSTED cho lượng thực hiện bằng không (syntactic).","mixed",["lexical","syntactic"]),
("Trước hết phân nhóm document × SKU trên mọi trạng thái, rồi xuất ID/no/type/status, SKU/unit và hai lượng milli-unit; DRAFT/CANCELLED có executed=0, TRANSFER lấy SOURCE, loại POSTED khác theo rules (lexical + reordered).","mixed",["lexical","reordering"]),
]}}

EXPECTED_TAGS = Counter({"lexical": 3, "syntactic": 3, "reordering": 2, "mixed": 2})
WRAPPER_RE = re.compile(r"^(bạn vui lòng cho biết|tôi cần tra cứu|đối với yêu cầu này|hãy giúp tôi xác định)", re.I)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    groups = {g["group_id"]: g for g in registry["groups"]}
    questions = {q["question_id"]: q for q in registry["questions"]}
    if not set(CARDS).issubset(groups):
        raise RuntimeError("Expected Development group is missing")
    OUT.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "DEVELOPMENT_INTENT_SQL_REVIEW_10.csv", "ERP_DEVELOPMENT_QUESTIONS_55.csv", "WMS_DEVELOPMENT_QUESTIONS_55.csv"):
        source = OUT / name
        if source.exists():
            shutil.copy2(source, ARCHIVE / name)
    old_registry = OUT / "dataset_v1_before_paraphrase_rewrite.json"
    if not old_registry.exists():
        shutil.copy2(REGISTRY_PATH, old_registry)

    archived_registry_path = OUT / "dataset_v1_before_paraphrase_rewrite.json"
    archived_briefs = {}
    if archived_registry_path.exists():
        archived_groups = {g["group_id"]: g for g in json.loads(archived_registry_path.read_text(encoding="utf-8"))["groups"]}
        archived_briefs = {gid: archived_groups[gid]["card_fields"].get("brief", "") for gid in CARDS}
    old_copy = {gid: archived_briefs.get(gid, groups[gid]["card_fields"].get("brief", "")) for gid in CARDS}
    cards_path = ROOT / "docs/benchmark/intent_cards/INTENT_CARDS_DRAFT.md"
    card_lines = cards_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(card_lines):
        for gid, card in CARDS.items():
            if line.startswith(f"| {gid} |"):
                cells = line.split("|")
                if len(cells) < 5:
                    raise RuntimeError(f"Unexpected Intent Cards table row for {gid}")
                cells[3] = " " + card["q0"] + " "
                card_lines[index] = "|".join(cells)
    cards_path.write_text("\n".join(card_lines) + "\n", encoding="utf-8")
    q0_changes = []
    for gid, card in CARDS.items():
        group = groups[gid]
        if group["split"] != "development":
            raise RuntimeError(f"Refusing to edit non-Development group {gid}")
        group["card_fields"]["brief"] = card["q0"]
        group["intent_card_status"] = "NEEDS_HUMAN_REVIEW"
        group["ground_truth_review"] = "NEEDS_HUMAN_REVIEW"
        q0 = questions[f"{gid}-Q00"]
        q0["question"] = card["q0"]
        q0["variant_type"] = "anchor"
        q0["variant_review"] = "NEEDS_HUMAN_REVIEW"
        q0["review_notes"] = "Q0 clarified to state existing card/SQL output semantics; pending Owner review."
        q0_changes.append({"group_id": gid, "old": old_copy[gid], "new": card["q0"], "status": "NEEDS_HUMAN_REVIEW"})
        for index, (text, category, secondary) in enumerate(card["variants"], 1):
            q = questions[f"{gid}-Q{index:02d}"]
            q["question"] = text
            q["variant_type"] = category
            q["secondary_tags"] = secondary
            q["variant_review"] = "NEEDS_HUMAN_REVIEW"
            q["semantic_slots_inherited"] = False
            q["review_notes"] = "Hand-authored draft; taxonomy intent is descriptive, semantic equivalence requires human review."

    registry["human_review_status"] = "NEEDS_HUMAN_REVIEW"
    registry["paraphrase_revision"] = "dev-v2"
    registry["paraphrase_revision_note"] = "Development Q0 clarified and 100 variants hand-authored; Final questions untouched."
    registry["source_hashes"]["intent_cards"] = digest(cards_path)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Keep human review records aligned with current question text and explicitly pending.
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    for record in records:
        if record["group_id"] not in CARDS:
            continue
        gid = record["group_id"]
        record["question_reviews"] = []
        for i in range(11):
            q = questions[f"{gid}-Q{i:02d}"]
            record["question_reviews"].append({
                "question_id": q["question_id"], "question": q["question"], "q_index": i,
                "role": q["role"], "variant_type": q["variant_type"],
                "secondary_tags": q.get("secondary_tags", []),
                "semantic_slots_inherited": False if i else True,
                "review_status": "NEEDS_HUMAN_REVIEW", "owner_decision": None,
            })
        record["human_review_status"] = "NEEDS_HUMAN_REVIEW"
        record["ground_truth_status"] = "NEEDS_HUMAN_REVIEW"
        record["owner_approval"] = {"status":"PENDING", "approver":None, "date":None, "rationale":None}
        record["wording_revision"] = "dev-v2"
    RECORDS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Keep the validation summary's provenance pointer current; SQL rows/hashes do not change.
    ground = json.loads(GROUND_PATH.read_text(encoding="utf-8"))
    ground["validation_records_sha256"] = digest(RECORDS_PATH)
    ground["question_wording_revision"] = "dev-v2; wording review pending; execution rows unchanged"
    GROUND_PATH.write_text(json.dumps(ground, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    expected = {x["group_id"]: x for x in json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))["expected_outputs"]}
    val = {x["group_id"]: x for x in ground["results"]}
    audit_rows = []
    for gid, card in CARDS.items():
        qitems = [questions[f"{gid}-Q{i:02d}"] for i in range(11)]
        quota = Counter(q["variant_type"] for q in qitems[1:])
        substantive = sum(not WRAPPER_RE.match(q["question"].strip()) for q in qitems[1:])
        changed = sum(qitems[i]["question"] != qitems[0]["question"] for i in range(1, 11))
        audit_rows.append({
            "group_id":gid, "q0_audit":"REVISED_TO_MATCH_CARD_AND_SQL_PROJECTION",
            "q0_decision":"NONE; wording clarification only" if gid != "WMS-CD-02" else "NONE; existing decision already explicit",
            "variant_count":10, "lexical":quota["lexical"], "syntactic":quota["syntactic"],
            "reordering":quota["reordering"], "mixed":quota["mixed"],
            "mixed_secondary_tags_complete":all(q.get("secondary_tags") for q in qitems[1:] if q["variant_type"]=="mixed"),
            "non_generic_wrapper_variants":substantive, "wordings_different_from_q0":changed,
            "all_questions_pending_human_review":all(q.get("variant_review")=="NEEDS_HUMAN_REVIEW" for q in qitems),
            "expected_rows":expected[gid]["row_count_before_set_comparison"],
            "candidate_rows":val[gid]["actual_row_count_before_set_comparison"],
            "candidate_execution_status":val[gid]["status"],
        })
    audit = {
        "revision":"dev-v2", "created_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope":"10 Development groups only; 40 Final groups, SQL/oracles, expected rows and snapshots untouched",
        "taxonomy_quota_per_group":dict(EXPECTED_TAGS), "groups":audit_rows,
        "totals":{"development_groups":10,"variants":100,"q0_revised":len(q0_changes),
                  "q0_needs_owner_decision":0,"lexical":sum(x['lexical'] for x in audit_rows),
                  "syntactic":sum(x['syntactic'] for x in audit_rows),"reordering":sum(x['reordering'] for x in audit_rows),
                  "mixed":sum(x['mixed'] for x in audit_rows),
                  "non_generic_wrapper_variants":sum(x['non_generic_wrapper_variants'] for x in audit_rows),
                  "variants_pending_human_review":100},
        "q0_changes":q0_changes,
        "interpretation":"Taxonomy labels describe intended linguistic transformations; automated shape checks do not establish semantic equivalence. All 110 questions remain NEEDS_HUMAN_REVIEW.",
    }
    (AUTH / "dev_paraphrase_quality_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (OUT / "DEV_PARAPHRASE_QUALITY_AUDIT.md").write_text(render_audit(audit, registry, expected), encoding="utf-8")
    print(json.dumps(audit["totals"], ensure_ascii=False, indent=2))


def render_audit(audit, registry, expected):
    lines=["# Development paraphrase quality audit — dev-v2", "",
           "Status: draft; all Q0–Q10 still need human review. Heuristic checks do not prove equivalence.", "",
           "## Q0 audit", "",
           "All 10 Q0 were clarified to expose projection/output grain and relevant filters/status/time/unit/tie semantics already present in the card and SQL. No SQL projection conflicts found; no Owner decision is required. WMS-CD-02 already stated its key business semantics and was made explicit about the complete output columns.", "",
           "## Variant audit", "",
           "| Group | Lexical | Syntactic | Reordering | Mixed | Expected rows | Technical rows | Status |",
           "|---|---:|---:|---:|---:|---:|---:|---|"]
    for x in audit["groups"]:
        lines.append(f"| {x['group_id']} | {x['lexical']} | {x['syntactic']} | {x['reordering']} | {x['mixed']} | {x['expected_rows']} | {x['candidate_rows']} | {x['candidate_execution_status']} |")
    lines += ["", "Totals: **100/100 variants** are authored as content-bearing transformations rather than fixed lead-in/lead-out wrappers; quotas are 30 lexical, 30 syntactic, 20 reordering, 20 mixed. All 100 remain `NEEDS_HUMAN_REVIEW`; this count is an authoring/heuristic audit, not a semantic-equivalence acceptance rate.", "",
              "## Examples by taxonomy", ""]
    for category, example in [
        ("Lexical", "ERP-AG equivalent terms: ‘tổng lượng xuất giao khách’ / ‘lượng đã xuất cho khách’; filters, unit and aggregation retained."),
        ("Syntactic", "ERP-JN-02 changes from a direct request to a question over each order line and its full six-field projection."),
        ("Reordering", "ERP-TM-02 states the delivered/local-year filters before grouping by local date, while retaining [start,end) and no zero-day rows."),
        ("Mixed", "WMS-CD-02 combines alternative wording for planned/executed quantities with reordered status and transfer rules; secondary tags identify both transformations."),
    ]: lines += [f"### {category}", "", example, ""]
    lines += ["## Q0 wording changes", "", "| Group | Previous Q0 | Revised Q0 |", "|---|---|---|"]
    for x in audit["q0_changes"]:
        lines.append(f"| {x['group_id']} | {x['old']} | {x['new']} |")
    lines += ["", "## Semantic risks for reviewers", "",
              "- ERP-GB-03: confirm ‘mã sales rep, tên nếu có’ maps to the nullable sales_rep_id and LEFT JOIN employee name; NULL stays one group.",
              "- ERP-TM-02: confirm Vietnamese local date, half-open 2025 interval, DELIVERED only, and no generated zero-count dates.",
              "- ERP-RK-02: confirm milli-quantity remains within each base unit; rank <=3 includes ties at third position.",
              "- WMS-AG-02: confirm ‘lượng xuất giao khách’ means negative movement magnitude from POSTED SHIPMENT only, output in milli-KG.",
              "- WMS-JN-04: confirm one row per movement leg and signed movement quantity; both transfer legs remain visible.",
              "- WMS-CD-02: confirm all document statuses, planned/executed milli-units, transfer SOURCE once, and other posted types per rules.",
              "- Every lexical synonym and mixed wording remains subject to Vietnamese domain review; no item has been accepted automatically.", "",
              "## Provenance", "",
              f"Previous registry SHA-256 (generic-wrapper version): `{hashlib.sha256((OUT / 'dataset_v1_before_paraphrase_rewrite.json').read_bytes()).hexdigest()}`  ",
              f"Registry SHA-256: `{digest(REGISTRY_PATH)}`  ",
              f"Validation Records SHA-256: `{digest(RECORDS_PATH)}`  ",
              f"Expected outputs SHA-256: `{digest(EXPECTED_PATH)}`  ",
              f"Audit JSON: `benchmark_data/authoring/dev_paraphrase_quality_audit.json`  ",
              "Question changes are confined to Development Q0–Q10; SQL candidates, expected rows, Python oracles and frozen snapshots are unchanged.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
