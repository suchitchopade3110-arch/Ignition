"""
In-memory stand-in for the supabase-py client, for tests that need the real
repository/query-building code to run (so a missing .in_()/.eq() filter
actually changes the result) without a database.

Supports the subset of the PostgREST builder this codebase uses: select
(with count="exact", column projection and one-level embeds like
"*, users(*)"), insert, update, upsert, delete, eq/neq/in_/gt/gte/lt/lte/
is_, order, range, limit, and rpc() against registered Python functions.
Every executed query is recorded in `queries` so a test can assert that no
query ran at all. execute() holds a lock, so a conditional update
(update().eq("status", "waiting_hitl")) is atomic the way a single
PostgREST UPDATE ... WHERE ... is.
"""
import copy
import threading
import uuid
from datetime import datetime, timezone

from postgrest.exceptions import APIError


class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, db: "FakeSupabase", table: str):
        self._db = db
        self._table = table
        self._op = "select"
        self._cols = "*"
        self._count = None
        self._payload = None
        self._filters: list[tuple] = []
        self._orders: list[tuple[str, bool]] = []
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None
        self._on_conflict = None
        self._ignore_duplicates = False

    # --- builders -----------------------------------------------------
    def select(self, *cols, count=None):
        if self._op == "select":
            self._cols = ",".join(cols) if cols else "*"
        self._count = count
        return self

    def insert(self, rows):
        self._op, self._payload = "insert", rows
        return self

    def update(self, values):
        self._op, self._payload = "update", values
        return self

    def upsert(self, rows, on_conflict=None, ignore_duplicates=False, **_):
        self._op, self._payload = "upsert", rows
        self._on_conflict, self._ignore_duplicates = on_conflict, ignore_duplicates
        return self

    def delete(self):
        self._op = "delete"
        return self

    def _f(self, op, col, val):
        self._filters.append((op, col, val))
        return self

    def eq(self, col, val):
        return self._f("eq", col, val)

    def neq(self, col, val):
        return self._f("neq", col, val)

    def in_(self, col, vals):
        return self._f("in", col, list(vals))

    def gt(self, col, val):
        return self._f("gt", col, val)

    def gte(self, col, val):
        return self._f("gte", col, val)

    def lt(self, col, val):
        return self._f("lt", col, val)

    def lte(self, col, val):
        return self._f("lte", col, val)

    def is_(self, col, val):
        return self._f("is", col, val)

    def order(self, col, desc=False, **_):
        self._orders.append((col, desc))
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def limit(self, n):
        self._limit = n
        return self

    # --- evaluation ---------------------------------------------------
    @staticmethod
    def _cmp(a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return (a > b) - (a < b)
        return (str(a) > str(b)) - (str(a) < str(b))

    def _match(self, row: dict) -> bool:
        for op, col, val in self._filters:
            v = row.get(col)
            if op == "eq" and v != val:
                return False
            if op == "neq" and v == val:
                return False
            if op == "in" and v not in val:
                return False
            if op == "is" and not ((val in (None, "null") and v is None) or v == val):
                return False
            if op in ("gt", "gte", "lt", "lte"):
                if v is None:
                    return False
                c = self._cmp(v, val)
                if (op == "gt" and c <= 0) or (op == "gte" and c < 0) or (op == "lt" and c >= 0) or (op == "lte" and c > 0):
                    return False
        return True

    def _project(self, row: dict) -> dict:
        tokens = [t.strip() for t in self._cols.split(",") if t.strip()]
        out: dict = {}
        for tok in tokens:
            if tok == "*":
                out.update(row)
            elif tok.endswith("(*)"):
                rel = tok[:-3]
                fk = row.get(f"{rel[:-1]}_id") if rel.endswith("s") else row.get(f"{rel}_id")
                match = next((r for r in self._db.tables.get(rel, []) if r.get("id") == fk), None)
                out[rel] = copy.deepcopy(match)
            elif tok in row:
                # A key a sparse fixture row doesn't have is left out, as
                # "*" would; a real row always has every column.
                out[tok] = row[tok]
        return copy.deepcopy(out)

    def _sorted(self, rows):
        for col, desc in reversed(self._orders):
            rows = sorted(rows, key=lambda r: (r.get(col) is None, str(r.get(col)) if not isinstance(r.get(col), (int, float)) else r.get(col)), reverse=desc)
        return rows

    def execute(self):
        db = self._db
        with db.lock:
            db.queries.append((self._table, self._op, tuple(self._filters)))
            if self._op == "select":
                db.selects.append((self._table, self._cols))
            rows = db.tables.setdefault(self._table, [])
            if self._op == "select":
                matched = self._sorted([r for r in rows if self._match(r)])
                count = len(matched) if self._count == "exact" else None
                if self._range:
                    matched = matched[self._range[0]: self._range[1] + 1]
                if self._limit is not None:
                    matched = matched[: self._limit]
                return FakeResult([self._project(r) for r in matched], count)
            if self._op in ("insert", "upsert"):
                payload = self._payload if isinstance(self._payload, list) else [self._payload]
                written = []
                for new in payload:
                    new = copy.deepcopy(new)
                    if self._op == "upsert" and self._on_conflict:
                        keys = [k.strip() for k in self._on_conflict.split(",")]
                        existing = next((r for r in rows if all(r.get(k) == new.get(k) for k in keys)), None)
                        if existing is not None:
                            if not self._ignore_duplicates:
                                existing.update(new)
                                written.append(copy.deepcopy(existing))
                            continue
                    new.setdefault("id", str(uuid.uuid4()))
                    new.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                    db._check_unique(self._table, new, rows)
                    rows.append(new)
                    written.append(copy.deepcopy(new))
                return FakeResult(written)
            if self._op == "update":
                updated = []
                for r in rows:
                    if self._match(r):
                        r.update(copy.deepcopy(self._payload))
                        updated.append(copy.deepcopy(r))
                return FakeResult(updated)
            if self._op == "delete":
                keep, gone = [], []
                for r in rows:
                    (gone if self._match(r) else keep).append(r)
                db.tables[self._table] = keep
                return FakeResult(copy.deepcopy(gone))
        raise AssertionError(f"unsupported op {self._op}")


class FakeRpc:
    def __init__(self, db, name, params):
        self._db, self._name, self._params = db, name, params

    def execute(self):
        with self._db.lock:
            self._db.queries.append(("rpc", self._name, tuple(sorted(self._params.items()))))
            return FakeResult(self._db.rpcs[self._name](self._db, self._params))


class FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]] | None = None, unique: dict | None = None):
        self.tables = {k: [copy.deepcopy(r) for r in v] for k, v in (tables or {}).items()}
        # table -> list of (columns tuple, optional predicate(row) -> bool)
        self.unique = unique or {}
        # Python mirrors of the SQL functions the app calls (migrations_019);
        # a test can override any of them.
        self.rpcs: dict = {
            "dashboard_stats": _dashboard_stats,
            "latest_review_per_repo": _latest_review_per_repo,
            "prune_review_diffs": _prune_review_diffs,
        }
        self.queries: list[tuple] = []
        # (table, selected columns) for every select, to check column lists.
        self.selects: list[tuple[str, str]] = []
        self.lock = threading.RLock()

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)

    def rpc(self, name: str, params: dict) -> FakeRpc:
        return FakeRpc(self, name, params)

    def _check_unique(self, table, new, rows):
        for cols, predicate in self.unique.get(table, []):
            if predicate is not None and not predicate(new):
                continue
            for r in rows:
                if predicate is not None and not predicate(r):
                    continue
                if all(r.get(c) == new.get(c) for c in cols):
                    raise APIError({"code": "23505", "message": "duplicate key value violates unique constraint"})

    def queries_on(self, table: str) -> list[tuple]:
        return [q for q in self.queries if q[0] == table]


class FakeAsyncRedis:
    """get/setex/delete/set, enough for the per-user repo cache and heartbeats."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = ttl

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    async def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)
        return len(keys)

    async def exists(self, *keys):
        return sum(1 for k in keys if k in self.store)


# --- Python mirrors of migrations_019's SQL functions -------------------------

def _dashboard_stats(db, params):
    names = set(params["repo_names"])
    rows = [r for r in db.tables.get("reviews", []) if r.get("repo_full_name") in names]
    completed = [float(r["acs_score"]) for r in rows if r.get("status") == "completed" and r.get("acs_score") is not None]
    return {
        "activeReviews": sum(1 for r in rows if r.get("status") == "running"),
        "hitlPending": sum(1 for r in rows if r.get("status") == "waiting_hitl"),
        "avgAcsScore": round(sum(completed) / len(completed), 1) if completed else 0,
        "issuesFound": sum(int(r.get("findings_count") or 0) for r in rows),
    }


def _latest_review_per_repo(db, params):
    latest: dict = {}
    for r in db.tables.get("reviews", []):
        name = r.get("repo_full_name")
        if name in params["repo_names"] and (name not in latest or str(r["created_at"]) > str(latest[name]["created_at"])):
            latest[name] = r
    return [{k: latest[n].get(k) for k in ("repo_full_name", "acs_score", "status", "created_at")} for n in sorted(latest)]


def _prune_review_diffs(db, params):
    cutoff = datetime.now(timezone.utc).timestamp() - params.get("older_than_days", 30) * 86400
    pruned = 0
    for r in db.tables.get("reviews", []):
        created = datetime.fromisoformat(str(r["created_at"]).replace("Z", "+00:00")).timestamp()
        if created < cutoff and (r.get("diff_text") is not None or r.get("diffs") is not None):
            r["diff_text"], r["diffs"] = None, None
            pruned += 1
    return pruned
