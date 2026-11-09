"""Build, seed, validate, and reproduce BIRD-VN-Robust-50 databases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bird_vn_benchmark import __version__
from bird_vn_benchmark.schema import ERP_SCHEMA, WMS_SCHEMA, initialize
from bird_vn_benchmark.seed import seed_erp, seed_wms
from bird_vn_benchmark.validate import connect_db, sha256_file, validate_database, write_reports

DEFAULT_OUT = ROOT / "benchmark_data" / "physical"
TABLES = {
    "erp_sales": ["CUSTOMERS", "EMPLOYEES", "PRODUCT_CATEGORIES", "PRODUCTS", "SALES_ORDERS",
                   "SALES_ORDER_LINES", "SALES_SHIPMENTS", "SALES_RETURNS", "SALES_RETURN_LINES", "PAYMENT_TRANSACTIONS"],
    "wms_inventory": ["PRODUCT_CATEGORIES", "PRODUCTS", "SUPPLIERS", "CUSTOMERS", "WAREHOUSES", "LOCATIONS",
                      "INVENTORY_DOCUMENTS", "INVENTORY_DOCUMENT_LINES", "INVENTORY_MOVEMENTS"],
}


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_one(domain: str, db_path: Path, seed: int) -> dict:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA foreign_keys = ON")
        initialize(conn, domain)
        conn.execute("PRAGMA user_version = 1")
        (seed_erp if domain == "erp_sales" else seed_wms)(conn, seed)
        if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RuntimeError(f"FK enforcement disabled during {domain} build")
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign key failures while building {domain}: {fk_errors[:5]}")
        conn.commit()
        conn.execute("VACUUM")
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES[domain]}
    finally:
        conn.close()
    return {"row_counts": counts, "sha256": sha256_file(db_path)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Build and validate deterministic benchmark SQLite databases")
    parser.add_argument("--seed", type=int, default=6002)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    schemas = {"erp_sales": ERP_SCHEMA, "wms_inventory": WMS_SCHEMA}
    schema_files = {}
    for domain, schema in schemas.items():
        name = "schema_erp_sales.sql" if domain == "erp_sales" else "schema_wms_inventory.sql"
        path = output / name
        path.write_text(schema.strip() + "\n", encoding="utf-8", newline="\n")
        schema_files[domain] = {"path": name, "sha256": sha256_file(path)}

    config = {"benchmark": "BIRD-VN-Robust-50", "physical_schema_version": 1,
              "generator_version": __version__, "seed": args.seed,
              "domain_seeds": {"erp_sales": args.seed, "wms_inventory": args.seed ^ 0x5A17}}
    config_path = output / "seed_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    built = {}
    for domain in ("erp_sales", "wms_inventory"):
        suffix = "erp_sales" if domain == "erp_sales" else "wms_inventory"
        final_db = output / f"{suffix}.sqlite"
        with tempfile.TemporaryDirectory(prefix=f".{suffix}_repro_", dir=output) as temp_dir:
            first = Path(temp_dir) / f"{suffix}_first.sqlite"
            second = Path(temp_dir) / f"{suffix}_second.sqlite"
            first_info = build_one(domain, first, config["domain_seeds"][domain])
            second_info = build_one(domain, second, config["domain_seeds"][domain])
            reproducible = first_info["sha256"] == second_info["sha256"]
            if not reproducible:
                raise RuntimeError(f"Reproducibility check failed for {domain}: {first_info['sha256']} != {second_info['sha256']}")
            os.replace(first, final_db)
        built[domain] = {**first_info, "reproducibility": "PASS", "database_file": final_db.name}

    reports_dir = output / "validation"
    validation = {}
    for domain in built:
        report = validate_database(output / built[domain]["database_file"], domain)
        validation[domain] = {"status": report["status"], "failed": report["invariants_failed"]}
        write_reports(report, reports_dir)
        if report["status"] != "PASS":
            raise RuntimeError(f"Validator failed for {domain}; see {reports_dir}")

    manifest = {
        "benchmark": "BIRD-VN-Robust-50",
        "build_status": "PASS",
        "build_script_version": __version__,
        "seed": args.seed,
        "python_version": sys.version,
        "sqlite_version": sqlite3.sqlite_version,
        "schema_version": 1,
        "seed_config_sha256": sha256_file(config_path),
        "source_sha256": {
            "schema_module": sha256_file(ROOT / "bird_vn_benchmark" / "schema.py"),
            "seed_generator": sha256_file(ROOT / "bird_vn_benchmark" / "seed.py"),
            "validator": sha256_file(ROOT / "bird_vn_benchmark" / "validate.py"),
            "build_cli": sha256_file(Path(__file__).resolve()),
            "fixture_test_runner": sha256_file(ROOT / "scripts" / "run_bird_vn_physical_tests.py"),
        },
        "test_evidence": {
            name: {"path": name, "sha256": sha256_file(output / name),
                   "status": json.loads((output / name).read_text(encoding="utf-8")).get("status", "UNKNOWN")}
            for name in ("fixture_test_results.json", "all_test_results.json")
            if (output / name).exists()
        },
        "schemas": schema_files,
        "databases": built,
        "validation": validation,
        "scope_note": "Physical synthetic DB only. No Intent Cards, benchmark questions, or canonical benchmark SQL are included.",
    }
    manifest_path = output / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = ["# BIRD-VN-Robust-50 physical database build", "", "- Build: **PASS**",
             f"- Seed: `{args.seed}`", f"- Python: `{platform_python()}`", f"- SQLite: `{sqlite3.sqlite_version}`",
             "- Reproducibility: byte-identical SHA-256 on two clean builds", "",
             "| Database | Rows by table | SHA-256 | Validator |", "|---|---|---|---|"]
    for domain, result in built.items():
        counts = ", ".join(f"{table}={count}" for table, count in result["row_counts"].items())
        lines.append(f"| {domain} | {counts} | `{result['sha256']}` | {validation[domain]['status']} |")
    lines.extend(["", "See `validation/` for per-invariant evidence and `build_manifest.json` for versions and hashes.",
                  "No benchmark questions or canonical SQL were created."])
    (output / "BUILD_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Build PASS: {output}")
    print(f"Seed: {args.seed}; Python {platform_python()}; SQLite {sqlite3.sqlite_version}")
    for domain, info in built.items():
        print(f"{domain}: {info['sha256']} (validator {validation[domain]['status']})")
    return 0


def platform_python() -> str:
    return sys.version.split()[0]


if __name__ == "__main__":
    raise SystemExit(main())
