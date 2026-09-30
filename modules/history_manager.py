"""
Scan History Manager - Persistent Storage & Audit Log for QuishGuard.
Maintains history of all scanned QR codes with search, filter, and CSV/JSON export.
"""
import os
import sys
import json
import csv
import datetime
from typing import List, Dict, Any, Optional


def _get_history_file_path() -> str:
    """Resolves persistent storage path for scan_history.json across both source and PyInstaller executable."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "scan_history.json")


HISTORY_FILE = _get_history_file_path()


class HistoryManager:
    """Handles thread-safe persistence and querying of scan history."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or _get_history_file_path()
        self.records: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        """Loads historical records from disk."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception:
                self.records = []
        else:
            self.records = []

    def save(self):
        """Persists records to disk."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_record(
        self,
        payload: str,
        risk_level: str,
        score: int,
        source: str,
        sha256: str,
        optical_meta: Optional[Dict[str, Any]] = None,
        hops_count: int = 0,
        flags: Optional[List[str]] = None,
        image_b64: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates and prepends a new scan audit record."""
        record = {
            "id": f"SCN-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "payload": payload,
            "risk_level": risk_level.upper(),
            "score": score,
            "source": source,
            "sha256": sha256 or "N/A",
            "optical_meta": optical_meta or {},
            "hops_count": hops_count,
            "flags": flags or [],
            "image_b64": image_b64 or "",
        }
        self.records.insert(0, record)
        # Cap at 500 records to prevent memory bloat
        if len(self.records) > 500:
            self.records = self.records[:500]
        self.save()
        return record

    def get_all(self) -> List[Dict[str, Any]]:
        return self.records

    def filter_records(self, query: str = "", risk_filter: str = "ALL") -> List[Dict[str, Any]]:
        """Filters records by text search and risk category."""
        res = self.records
        if risk_filter.upper() != "ALL":
            if risk_filter.upper() in ["CRITICAL", "HIGH"]:
                res = [r for r in res if r.get("risk_level") in ["CRITICAL", "HIGH"]]
            elif risk_filter.upper() in ["MEDIUM", "WARN", "WARNING"]:
                res = [r for r in res if r.get("risk_level") in ["MEDIUM", "WARN", "WARNING"]]
            elif risk_filter.upper() in ["LOW", "CLEAN", "SECURE"]:
                res = [r for r in res if r.get("risk_level") in ["LOW", "CLEAN", "SECURE"]]

        if query and query.strip():
            q = query.strip().lower()
            res = [
                r for r in res
                if q in r.get("payload", "").lower()
                or q in r.get("source", "").lower()
                or q in r.get("sha256", "").lower()
                or q in r.get("id", "").lower()
            ]

        return res

    def clear(self):
        """Clears all historical records."""
        self.records = []
        self.save()

    def export_csv(self, export_path: str) -> bool:
        """Exports records to a standard CSV audit file."""
        try:
            with open(export_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Timestamp", "Risk Level", "Score", "Source", "SHA-256", "Payload", "Flags"])
                for r in self.records:
                    writer.writerow([
                        r.get("id", ""),
                        r.get("timestamp", ""),
                        r.get("risk_level", ""),
                        r.get("score", 0),
                        r.get("source", ""),
                        r.get("sha256", ""),
                        r.get("payload", ""),
                        "; ".join(r.get("flags", [])),
                    ])
            return True
        except Exception:
            return False

    def export_json(self, export_path: str) -> bool:
        """Exports records to a JSON file."""
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False


history_manager = HistoryManager()
