import json
import os
from collections import OrderedDict
from datetime import datetime
from threading import Lock


class ReviewStore:
    """Thread-safe in-memory store for review results. Persists to JSON on disk."""

    def __init__(self, path: str = "data/reviews.json", max_items: int = 200):
        self.path = path
        self.max_items = max_items
        self._lock = Lock()
        self._data: OrderedDict = OrderedDict()
        self._load()

    def _load(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            if os.path.exists(self.path):
                with open(self.path) as f:
                    items = json.load(f)
                    for item in items:
                        self._data[item["id"]] = item
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(list(self._data.values()), f, indent=2)
        except Exception as e:
            print(f"Store save error: {e}")

    def upsert(self, review_id: str, updates: dict):
        with self._lock:
            existing = self._data.get(review_id, {"id": review_id})
            existing.update(updates)
            existing["updated_at"] = datetime.utcnow().isoformat()
            self._data[review_id] = existing

            # Evict oldest if over limit
            while len(self._data) > self.max_items:
                self._data.popitem(last=False)

            self._save()

    def get(self, review_id: str) -> dict | None:
        with self._lock:
            return self._data.get(review_id)

    def get_all(self) -> list:
        with self._lock:
            items = list(self._data.values())
            items.reverse()  # newest first
            return items[:50]

    def get_stats(self) -> dict:
        with self._lock:
            items = list(self._data.values())
            completed = [i for i in items if i.get("status") == "completed"]
            all_findings = [f for i in completed for f in i.get("findings", [])]
            return {
                "total_reviews": len(items),
                "completed": len(completed),
                "failed": sum(1 for i in items if i.get("status") == "failed"),
                "running": sum(1 for i in items if i.get("status") == "running"),
                "total_findings": len(all_findings),
                "critical_findings": sum(1 for f in all_findings if f.get("severity") == "critical"),
                "warning_findings": sum(1 for f in all_findings if f.get("severity") == "warning"),
            }
