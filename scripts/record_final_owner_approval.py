from __future__ import annotations
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'benchmark_data/authoring'
SBERT = ROOT / 'docs/benchmark/review/full_semantic_validation_sbert'
BUSINESS = ROOT / 'docs/benchmark/business'
DATE = '2026-11-17'
PROV_PATH = 'benchmark_data/authoring/final_owner_approval_provenance_2026-11-17.json'
PROVENANCE = {
    'approver_role': 'Benchmark Owner',
    'decision_date': DATE,
    'decision': 'APPROVE',
    'scope': 'All 40 Final Semantic Groups, their 40 Intent Cards, 40 canonical SQL candidates, expected outputs, and all 440 Questions (Q00-Q10), based on the Owner statement that they reviewed and accepted them.',
    'source': 'Explicit user message in this conversation: "Mình đã xem xét và chấp nhận. Bạn hãy duyệt giúp mình nhé" following the request to review the 40 Final groups.',
    'rationale': 'The Benchmark Owner explicitly states they reviewed and accepted the Final groups. The decision is recorded as Owner approval; automation evidence remains a separate status.',
    'acknowledged_limitations': [
        'The known Q01/Q02 wording pattern shares a common request core after removing framing language; this accepted limitation is retained and does not count as evidence that the variants are strongly distinct.',
        'Fixture evidence remains at its recorded per-group status; Owner approval does not convert NOT_RECORDED or missing fixture evidence into a fixture PASS.',
        'Approval does not freeze the registry, authorize official evaluation, or change the approved experimental protocol.'
    ],
    'question_texts_modified': False,
    'sql_oracle_or_expected_outputs_modified': False,
    'database_snapshots_modified': False,
    'official_evaluation_authorized': False
}

def readj(path): return json.loads(path.read_text(encoding='utf-8'))
def writej(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def readcsv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f)), list(csv.DictReader(f).fieldnames or [])
def writecsv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

registry_path = AUTH/'dataset.json'
registry = readj(registry_path)
final_groups = [g for g in registry['groups'] if g.get('split') == 'final']
assert len(final_groups) == 40, f'Expected 40 final groups; found {len(final_groups)}'
final_ids = {g['group_id'] for g in final_groups}
questions_by_group = {}
for q in registry['questions']:
    questions_by_group.setdefault(q['group_id'], []).append(q)
assert sum(len(questions_by_group[g]) for g in final_ids) == 440
assert all(len(questions_by_group[g]) == 11 and sorted(q['q_index'] for q in questions_by_group[g]) == list(range(11)) for g in final_ids)

provenance_file = AUTH/'final_owner_approval_provenance_2026-11-17.json'
writej(provenance_file, PROVENANCE)

# Update only human decision gates. Keep benchmark wording and technical evidence intact.
for group in final_groups:
    group['intent_card_status'] = 'APPROVED'
    # The registry release gate recognizes VALIDATED; owner provenance remains explicit below.
    group['ground_truth_review'] = 'VALIDATED'
    group['human_review_status'] = 'APPROVED'
    group['owner_approval'] = {**PROVENANCE, 'provenance_artifact': PROV_PATH}
    # Preserve validation_status as machine status; matching evidence is asserted below.
    for q in questions_by_group[group['group_id']]:
        q['variant_review'] = 'ACCEPT'
        q['review_decision_provenance'] = {**PROVENANCE, 'provenance_artifact': PROV_PATH}
registry['human_review_status'] = 'FINAL_APPROVED_BY_OWNER; DEVELOPMENT_Q00_REVIEW_PENDING'
registry['final_owner_approval'] = {'status':'APPROVED_BY_OWNER','date':DATE,'provenance_artifact':PROV_PATH,'groups':40,'questions':440}
writej(registry_path, registry)
registry_hash = sha(registry_path)

# Update 40 Validation Records, including explicit Q00 and Q01-Q10 decisions.
records_path = AUTH/'validation_records.json'
records = readj(records_path)
record_by_id = {r['group_id']: r for r in records}
assert final_ids.issubset(record_by_id)
for group in final_groups:
    rec = record_by_id[group['group_id']]
    rec['ground_truth_status'] = 'APPROVED_BY_OWNER'
    rec['human_review'] = 'APPROVED'
    rec['human_review_status'] = 'APPROVED'
    rec['approval_provenance'] = {**PROVENANCE, 'provenance_artifact': PROV_PATH}
    rec['owner_approval'] = rec['approval_provenance']
    rec['machine_validation_status'] = 'VALIDATED_BY_AUTOMATION'
    rec['owner_reviewed_artifacts'] = ['intent_card', 'canonical_sql_candidate', 'expected_output', 'questions_Q00_Q10']
    existing = {x.get('question_id'): x for x in rec.get('question_reviews', []) if x.get('question_id')}
    reviews = []
    for q in sorted(questions_by_group[group['group_id']], key=lambda x: x['q_index']):
        review = existing.get(q['question_id'], {})
        review.update({
            'question_id': q['question_id'], 'question': q['question'], 'q_index': q['q_index'],
            'role': q.get('role', 'original' if q['q_index'] == 0 else 'variant'),
            'variant_type': q.get('variant_type', 'anchor' if q['q_index'] == 0 else 'unknown'),
            'review_status': 'ACCEPT', 'owner_decision': 'ACCEPT',
            'review_decision_provenance': {**PROVENANCE, 'provenance_artifact': PROV_PATH}
        })
        reviews.append(review)
    rec['question_reviews'] = reviews

writej(records_path, records)

# Reflect human approval separately from machine comparison in the Final validation report.
validation_path = AUTH/'ground_truth_validation_final.json'
validation = readj(validation_path)
result_by_id = {r['group_id']: r for r in validation['results']}
assert final_ids == set(result_by_id)
for gid, result in result_by_id.items():
    if result.get('candidate_sql_executed') is not True or result.get('rows_match_set_comparator') is not True:
        raise RuntimeError(f'{gid} lacks successful matching automation evidence; cannot record technical PASS')
    result['machine_validation_status'] = 'VALIDATED_BY_AUTOMATION'
    result['human_review_status'] = 'APPROVED'
    result['owner_approval_provenance'] = PROV_PATH
    result['status'] = 'APPROVED_BY_OWNER'
    result['known_review_limitation'] = 'Q01/Q02 common framing pattern accepted by Owner; this does not establish strong paraphrase diversity.'
validation['summary'] = {'APPROVED_BY_OWNER': 40}
validation['machine_validation_summary'] = {'VALIDATED_BY_AUTOMATION': 40, 'execution_and_set_comparison_match': 40}
validation['human_approval_provenance'] = PROV_PATH
validation['approval_recorded_at_utc'] = datetime.now(timezone.utc).isoformat()
validation['approval_registry_sha256'] = registry_hash
writej(validation_path, validation)

# Refresh owner-facing review tables while retaining fixture/coverage evidence values.
queue_path = SBERT/'human_review_queue.csv'
rows, fields = readcsv(queue_path)
for row in rows:
    if row.get('group_id') in final_ids:
        row['intent_card_status'] = 'APPROVED'
        row['ground_truth_review'] = 'APPROVED_BY_OWNER'
        row['validation_status'] = 'VALIDATED_BY_AUTOMATION'
        row['human_review_required'] = 'NO'
        row['review_status'] = 'APPROVED_BY_OWNER'
writecsv(queue_path, rows, fields)

audit_path = SBERT/'ground_truth_validation_audit.csv'
rows, fields = readcsv(audit_path)
for row in rows:
    gid = row.get('group_id')
    if gid in final_ids:
        result = result_by_id[gid]
        row['machine_validation_status'] = 'VALIDATED_BY_AUTOMATION'
        row['audit_status'] = 'APPROVED_BY_OWNER'
        row['execution_evidence_present'] = str(bool(result.get('candidate_sql_executed')))
        row['execution_evidence_status'] = 'EXECUTED_AND_MATCHED' if result.get('rows_match_set_comparator') else 'MISMATCH_OR_ERROR'
        row['human_review_status'] = 'APPROVED'
        row['human_approval_provenance'] = PROV_PATH
        row['limitation'] = 'Explicit Benchmark Owner approval recorded. Fixture status remains as recorded and is not promoted by approval; Q01/Q02 framing similarity is an acknowledged limitation. Automated agreement is supporting evidence, not the approval source.'
writecsv(audit_path, rows, fields)

gaps_path = SBERT/'intent_sql_evidence_gaps.csv'
rows, fields = readcsv(gaps_path)
for row in rows:
    gid = row.get('group_id')
    if gid in final_ids:
        row['evidence_status'] = 'APPROVED_BY_OWNER_WITH_RECORDED_FIXTURE_STATUS'
        row['gap'] = 'Owner approved current Intent/SQL/expected outputs/questions. Any previously unrecorded fixture evidence remains unrecorded; Q01/Q02 common-framing limitation is accepted and documented.'
writecsv(gaps_path, rows, fields)

# Record approval in the business decision log without rewriting its historical entries.
owner_log = BUSINESS/'OWNER_REVIEW_RECORD.md'
owner_log_marker = '## Benchmark Owner duyệt 40 nhóm Final — 2026-11-17'
owner_log_text = owner_log.read_text(encoding='utf-8') if owner_log.exists() else ''
if owner_log_marker not in owner_log_text:
    with owner_log.open('a', encoding='utf-8') as f:
        f.write('\n\n## Benchmark Owner duyệt 40 nhóm Final — 2026-11-17\n\n')
        f.write('Benchmark Owner xác nhận đã xem xét và chấp nhận 40 nhóm Final. Quyết định bao gồm 40 Intent Cards, 40 SQL chuẩn dự thảo, expected outputs và 440 câu hỏi Q00–Q10 hiện hành. Provenance chi tiết được lưu tại `benchmark_data/authoring/final_owner_approval_provenance_2026-11-17.json`; các quyết định theo nhóm và câu hỏi nằm trong registry và Validation Records.\n\n')
        f.write('Giới hạn được ghi nhận cùng quyết định: Q01/Q02 trong các nhóm có chung phần yêu cầu cốt lõi sau khi bỏ câu dẫn; đây là hạn chế đa dạng cách diễn đạt đã được Benchmark Owner chấp nhận cho bản hiện tại. Trạng thái fixture được giữ nguyên, không biến bằng chứng chưa ghi nhận thành PASS.\n\n')
        f.write('Quyết định này không sửa câu hỏi, SQL, oracle, expected outputs hay SQLite snapshot; không đóng băng registry và không cấp phép chạy Official Evaluation. Các điều kiện phát hành khác vẫn phải được kiểm tra riêng.\n')

# Refresh audit summary and report hashes. Similarity scores remain valid because question strings did not change.
summary_path = SBERT/'summary.json'
summary = readj(summary_path)
summary['registry_sha256'] = registry_hash
summary['manifest_match'] = True
summary['registry_hash_matches_manifest'] = True
summary['ground_truth_status_counts'] = {"('development', 'VALIDATED')": 10, "('final', 'APPROVED_BY_OWNER')": 40}
summary['group_split_status'] = {
    'development_intent_sql_automation_evidence': 10,
    'development_q00_pending_human_review': 10,
    'final_groups_approved_by_owner': 40,
    'final_independently_derived_expected_outputs': 40,
    'final_candidate_sql_matches_independent_outputs': 40,
}
summary['human_review_queue_groups'] = 10
summary['human_review_queue_total_groups'] = 50
summary['slot_validation'] = 'Owner approval recorded for all 40 Final groups and 440 Questions. Development Q00 review remains pending. The known Q01/Q02 common-framing limitation is disclosed; SBERT scores are triage evidence only.'
summary['final_owner_approval_provenance'] = PROV_PATH
summary.setdefault('source_hashes', {})['dataset.json'] = registry_hash
summary['source_hashes']['validation_records.json'] = sha(records_path)
summary['source_hashes']['ground_truth_validation_final.json'] = sha(validation_path)
summary['report_artifact_sha256'] = {
    p.name: sha(p) for p in sorted(SBERT.iterdir())
    if p.is_file() and p.name not in ('summary.json',)
}
writej(summary_path, summary)

# Update manifest hashes for all existing files and the new provenance file.
manifest_path = AUTH/'dev_v6_vietnamese_first_manifest.json'
manifest = readj(manifest_path)
tracked = set(manifest.get('files', {}))
tracked.update({
    'benchmark_data/authoring/dataset.json',
    'benchmark_data/authoring/validation_records.json',
    'benchmark_data/authoring/ground_truth_validation_final.json',
    PROV_PATH,
    'docs/benchmark/business/OWNER_REVIEW_RECORD.md',
    'docs/benchmark/review/full_semantic_validation_sbert/summary.json',
    'docs/benchmark/review/full_semantic_validation_sbert/human_review_queue.csv',
    'docs/benchmark/review/full_semantic_validation_sbert/ground_truth_validation_audit.csv',
    'docs/benchmark/review/full_semantic_validation_sbert/intent_sql_evidence_gaps.csv',
})
manifest['registry_sha256'] = registry_hash
manifest['evidence_revision'] = 'final-owner-approval-2026-11-17'
manifest['scope'] = 'Current BIRD-VN-Robust-50 registry; Benchmark Owner approval recorded for all 40 Final groups and 440 questions. Question strings and technical evidence are unchanged.'
manifest['ground_truth'] = 'Final owner approval is separately recorded from automation. All 40 candidate SQL runs match the independently derived expected outputs by the recorded set comparator; recorded fixture statuses remain unchanged.'
manifest['final_owner_approval_provenance'] = PROV_PATH
manifest['official_evaluation_authorized'] = False
manifest['files'] = {rel: sha(ROOT/rel) for rel in sorted(tracked) if (ROOT/rel).is_file()}
writej(manifest_path, manifest)

# Add the summary hash after summary is final; manifest itself is not self-hashed.
manifest['files']['docs/benchmark/review/full_semantic_validation_sbert/summary.json'] = sha(summary_path)
writej(manifest_path, manifest)

print(json.dumps({
 'approval': 'APPROVED_BY_OWNER', 'approver_role': 'Benchmark Owner', 'date': DATE,
 'final_groups': len(final_groups), 'final_questions': sum(len(questions_by_group[g]) for g in final_ids),
 'automation_match_groups': sum(bool(r.get('candidate_sql_executed') and r.get('rows_match_set_comparator')) for r in validation['results']),
 'question_strings_changed': False, 'sql_expected_outputs_or_snapshots_changed': False,
 'development_status_changed': False, 'registry_sha256': registry_hash,
 'provenance': PROV_PATH,
}, ensure_ascii=False, indent=2))
