from datetime import datetime, timedelta, timezone
import json
import logging
import collections
from postgrest.exceptions import APIError
from app.database import get_supabase

logger = logging.getLogger(__name__)

class ReviewRepository:
    TABLE = "reviews"

    def __init__(self):
        self._db = get_supabase()

    def create_review(self, review_id: str, repo_full_name: str, pr_number: int, title: str, author: str, branch: str, commit_sha: str, installation_id: int | None = None, correlation_id: str | None = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": review_id,
            "repo_full_name": repo_full_name,
            "pr_number": pr_number,
            "title": title,
            "author": author,
            "branch": branch,
            "commit_sha": commit_sha,
            "installation_id": installation_id,
            "correlation_id": correlation_id,
            "status": "queued",
            "severity": "none",
            "findings_count": 0,
            "created_at": now,
            "verified_findings": [],
            "agents": [],
            "diffs": []
        }
        res = self._db.table(self.TABLE).insert(row).execute()
        return res.data[0] if res.data else row

    def get_review_by_repo_pr_sha(self, repo_full_name: str, pr_number: int, commit_sha: str) -> dict | None:
        """Used by the webhook idempotency check (app/main.py::github_webhook)
        to report which existing review a duplicate delivery matched."""
        res = (
            self._db.table(self.TABLE)
            .select("id, correlation_id")
            .eq("repo_full_name", repo_full_name)
            .eq("pr_number", pr_number)
            .eq("commit_sha", commit_sha)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def get_review_github_context(self, review_id: str) -> dict | None:
        """
        The pieces approve_hitl needs to post a comment to the right place:
        repo_full_name (must be owner/name, not the short display name) and
        installation_id (captured from the webhook payload at review-creation
        time — see app/main.py::github_webhook — since by the time a human
        approves in a separate later request, there's no webhook event left
        to read it from).
        """
        res = (
            self._db.table(self.TABLE)
            .select("repo_full_name, installation_id, pr_number, final_comment_markdown, correlation_id, commit_sha")
            .eq("id", review_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def get_last_completed_acs(self, repo_full_name: str, pr_number: int) -> float | None:
        """The ACS of this PR's most recent completed review that has one
        (audit P0-7: the merge baseline). A review whose 2A agent failed has
        no ACS (P0-1) and is skipped."""
        res = (
            self._db.table(self.TABLE)
            .select("acs_score")
            .eq("repo_full_name", repo_full_name)
            .eq("pr_number", pr_number)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return next((float(r["acs_score"]) for r in res.data or [] if r.get("acs_score") is not None), None)

    def get_check_run_id(self, review_id: str) -> int | None:
        """The review's GitHub check run (audit P0-6), or None if the webhook
        couldn't create one."""
        res = self._db.table(self.TABLE).select("check_run_id").eq("id", review_id).execute()
        return res.data[0].get("check_run_id") if res.data else None

    def update_review(self, review_id: str, updates: dict) -> dict:
        # If status changes to completed/failed, set completed_at
        if "status" in updates and updates["status"] in ("completed", "failed", "rejected", "cancelled", "posting"):
            updates["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Calculate duration if completed_at is set
        if "completed_at" in updates or ("status" in updates and updates["status"] in ("completed", "failed", "rejected", "cancelled", "posting")):
            review = self.get_review(review_id)
            if review:
                created_at_str = review.get("created_at")
                if created_at_str:
                    try:
                        # strip Z or offset
                        created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        if created_dt.tzinfo is None:  # a naive stamp is UTC
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        delta = datetime.now(timezone.utc) - created_dt
                        seconds = int(delta.total_seconds())
                        if seconds < 60:
                            updates["duration"] = f"{seconds}s"
                        else:
                            updates["duration"] = f"{seconds // 60}m {seconds % 60}s"
                    except Exception:
                        pass

        res = self._db.table(self.TABLE).update(updates).eq("id", review_id).execute()
        return res.data[0] if res.data else {}

    def _map_review_row(self, row: dict) -> dict:
        repo_full_name = row["repo_full_name"]
        owner, name = repo_full_name.split("/", 1) if "/" in repo_full_name else (repo_full_name, repo_full_name)
        
        return {
            "id": row["id"],
            "repo_id": repo_full_name.replace("/", "_"),
            "repo_name": name,
            "pull_request_number": row["pr_number"],
            "title": row["title"],
            "status": row["status"],
            "severity": row.get("severity", "none"),
            "findings_count": row.get("findings_count", 0),
            "created_at": row["created_at"],
            "completed_at": row.get("completed_at"),
            "duration": row.get("duration"),
            "acs_score": row.get("acs_score"),
            
            # Detailed review fields
            "author": row.get("author", "unknown"),
            "branch": row.get("branch", "main"),
            "commit_sha": row.get("commit_sha", ""),
            "files_changed": row.get("files_changed", 0),
            "lines_added": row.get("lines_added", 0),
            "lines_deleted": row.get("lines_deleted", 0),
            "previous_acs_score": row.get("previous_acs_score") if row.get("previous_acs_score") is not None else 100.0,
            "regression": row.get("regression") or {"is_regression": False},
            "agents": row.get("agents") or [],
            "findings": row.get("findings") or [],
            "diffs": row.get("diffs") or [],
            "github_comment_preview": row.get("github_comment_preview"),
            "final_comment_markdown": row.get("final_comment_markdown"),
            # Why a review ended the way it did (incomplete, superseded, timed
            # out, ...); approve_hitl reads it to conclude the check run.
            "status_reason": row.get("status_reason"),
        }

    # Columns each read needs (I-10): never "*", which drags every review's
    # raw diff_text (and, for lists, the per-file diffs JSON) along.
    LIST_COLUMNS = (
        "id, repo_full_name, pr_number, title, status, severity, findings_count, created_at, completed_at, "
        "duration, acs_score, author, branch, commit_sha, previous_acs_score, regression, status_reason"
    )
    HITL_COLUMNS = LIST_COLUMNS + ", findings, agents, final_comment_markdown, hitl_severity"
    DETAIL_COLUMNS = LIST_COLUMNS + ", findings, agents, diffs, github_comment_preview, final_comment_markdown"
    LEDGER_COLUMNS = "status, acs_score, verified_findings, regression, created_at"

    def get_review(self, review_id: str) -> dict | None:
        res = self._db.table(self.TABLE).select(self.DETAIL_COLUMNS).eq("id", review_id).execute()
        return self._map_review_row(res.data[0]) if res.data else None

    def list_reviews(self, repo_name: str = None, status: str = None, severity: str = None, page: int = 1, page_size: int = 25,
                     repo_names=None) -> tuple[list[dict], int]:
        # repo_names: the caller's accessible repos (audit P0-4). Empty means
        # nothing to show — return without querying.
        if repo_names is not None and not repo_names:
            return [], 0
        query = self._db.table(self.TABLE).select(self.LIST_COLUMNS, count="exact")
        if repo_names is not None:
            query = query.in_("repo_full_name", sorted(repo_names))
        if repo_name:
            query = query.eq("repo_full_name", repo_name)
        if status:
            query = query.eq("status", status)
        if severity:
            query = query.eq("severity", severity)
        
        start = (page - 1) * page_size
        end = start + page_size - 1
        res = query.order("created_at", desc=True).range(start, end).execute()
        
        total = res.count if res.count is not None else len(res.data)
        mapped_data = [self._map_review_row(row) for row in res.data]
        return mapped_data, total

    def list_hitl_pending(self, repo_names=None) -> list[dict]:
        if repo_names is not None and not repo_names:
            return []
        query = self._db.table(self.TABLE).select(self.HITL_COLUMNS)
        if repo_names is not None:
            query = query.in_("repo_full_name", sorted(repo_names))
        res = query.eq("status", "waiting_hitl").order("created_at", desc=True).execute()
        return [self._map_review_row(row) for row in res.data]

    def _scoped(self, query, repo_names):
        return query.in_("repo_full_name", sorted(repo_names)) if repo_names is not None else query

    def get_stats(self, repo_names=None) -> dict:
        if repo_names is not None and not repo_names:
            return {"activeReviews": 0, "hitlPending": 0, "avgAcsScore": 0.0, "issuesFound": 0, "issuesFoundTrend": None}
        if repo_names is not None:
            # One SQL function instead of four row-scanning queries (I-10).
            res = self._db.rpc("dashboard_stats", {"repo_names": sorted(repo_names)}).execute()
            stats = res.data or {}
            return {
                "activeReviews": int(stats.get("activeReviews") or 0),
                "hitlPending": int(stats.get("hitlPending") or 0),
                "avgAcsScore": round(float(stats.get("avgAcsScore") or 0), 1),
                "issuesFound": int(stats.get("issuesFound") or 0),
                "issuesFoundTrend": self._issues_found_trend(repo_names),
            }

        # activeReviews: status="running"
        running_res = self._scoped(self._db.table(self.TABLE).select("id", count="exact"), repo_names).eq("status", "running").execute()
        active_reviews = running_res.count if running_res.count is not None else 0

        # hitlPending: status="waiting_hitl"
        hitl_res = self._scoped(self._db.table(self.TABLE).select("id", count="exact"), repo_names).eq("status", "waiting_hitl").execute()
        hitl_pending = hitl_res.count if hitl_res.count is not None else 0

        # avgAcsScore: avg acs_score across completed reviews
        completed_res = self._scoped(self._db.table(self.TABLE).select("acs_score"), repo_names).eq("status", "completed").execute()
        scores = [float(row["acs_score"]) for row in completed_res.data if row.get("acs_score") is not None]
        avg_acs_score = sum(scores) / len(scores) if scores else 0.0

        # issuesFound: sum of findings_count across reviews
        findings_res = self._scoped(self._db.table(self.TABLE).select("findings_count"), repo_names).execute()
        issues_found = sum(int(row["findings_count"]) for row in findings_res.data if row.get("findings_count") is not None)

        return {
            "activeReviews": active_reviews,
            "hitlPending": hitl_pending,
            "avgAcsScore": round(avg_acs_score, 1),
            "issuesFound": issues_found,
            "issuesFoundTrend": self._issues_found_trend(repo_names),
        }

    def _issues_found_trend(self, repo_names=None) -> dict | None:
        """
        Week-over-week change in issues found: sum(findings_count) for
        reviews created in the last 7 days vs the 7 days before that.
        Returns None rather than a 0%/100% placeholder when there's no
        prior-week baseline to compare against (e.g. a fresh deployment, or
        a repo that just started using Ignition) — a fabricated number here
        is exactly the thing this field was added to stop doing.
        """
        now = datetime.now(timezone.utc)
        week_ago = (now - timedelta(days=7)).isoformat()
        two_weeks_ago = (now - timedelta(days=14)).isoformat()

        recent_res = (
            self._scoped(self._db.table(self.TABLE).select("findings_count"), repo_names)
            .gte("created_at", week_ago)
            .execute()
        )
        prior_res = (
            self._scoped(self._db.table(self.TABLE).select("findings_count"), repo_names)
            .gte("created_at", two_weeks_ago)
            .lt("created_at", week_ago)
            .execute()
        )

        def _sum(rows: list[dict]) -> int:
            return sum(int(r["findings_count"]) for r in rows if r.get("findings_count") is not None)

        recent_total = _sum(recent_res.data or [])
        prior_total = _sum(prior_res.data or [])

        if prior_total <= 0:
            return None

        pct_change = ((recent_total - prior_total) / prior_total) * 100
        return {"value": round(abs(pct_change), 1), "isPositive": pct_change >= 0}

    def prune_old_diffs(self, older_than_days: int = 30) -> int:
        """Retention (I-10): drops stored diffs from reviews older than
        `older_than_days`; returns how many rows changed."""
        res = self._db.rpc("prune_review_diffs", {"older_than_days": older_than_days}).execute()
        return int(res.data or 0)

    def get_ledger_stats(self, repo_full_name: str) -> dict:
        res = self._db.table(self.TABLE).select(self.LEDGER_COLUMNS).eq("repo_full_name", repo_full_name).execute()
        data = res.data or []
        
        completed = [r for r in data if r.get("status") in ("completed", "rejected") and r.get("acs_score") is not None]
        avg_acs = sum(float(r["acs_score"]) for r in completed) / len(completed) if completed else 0.0
        
        # critical findings
        critical_count = 0
        for r in data:
            findings = r.get("verified_findings")
            if isinstance(findings, list):
                critical_count += sum(1 for f in findings if f.get("severity") in ("critical", "danger"))
            elif isinstance(findings, str) and findings:
                try:
                    f_list = json.loads(findings)
                    critical_count += sum(1 for f in f_list if f.get("severity") in ("critical", "danger"))
                except Exception:
                    pass

        # active regressions (is_regression is True and status is waiting_hitl or running, or latest completed is regression)
        active_regressions = sum(1 for r in data if (r.get("regression") or {}).get("is_regression") is True)

        return {
            "averageAcs": round(avg_acs, 1),
            "totalReviews": len(data),
            "criticalFindings": critical_count,
            "activeRegressions": active_regressions
        }

    def get_ledger_trend(self, repo_full_name: str) -> list[dict]:
        res = self._db.table(self.TABLE).select(self.LEDGER_COLUMNS).eq("repo_full_name", repo_full_name).execute()
        data = res.data or []
        
        # Group by month (YYYY-MM)
        by_month = collections.defaultdict(list)
        for r in data:
            created_at = r.get("created_at")
            if created_at:
                month = created_at[:7] # YYYY-MM
                by_month[month].append(r)
                
        trend = []
        for month in sorted(by_month.keys()):
            month_reviews = by_month[month]
            completed = [r for r in month_reviews if r.get("acs_score") is not None]
            avg_acs = sum(float(r["acs_score"]) for r in completed) / len(completed) if completed else 0.0
            
            critical_count = 0
            for r in month_reviews:
                findings = r.get("verified_findings")
                if isinstance(findings, list):
                    critical_count += sum(1 for f in findings if f.get("severity") in ("critical", "danger"))
                elif isinstance(findings, str) and findings:
                    try:
                        f_list = json.loads(findings)
                        critical_count += sum(1 for f in f_list if f.get("severity") in ("critical", "danger"))
                    except Exception:
                        pass
                        
            trend.append({
                "date": month,
                "acsScore": round(avg_acs, 1),
                "reviewsCount": len(month_reviews),
                "criticalCount": critical_count
            })
        return trend


class RepoRepository:
    TABLE = "repositories"
    SETTINGS_TABLE = "repository_settings"

    def __init__(self):
        self._db = get_supabase()

    def _by_owner_name(self, query, repo_full_name: str):
        # Exact owner and name columns, never the derived owner_name id:
        # acme_corp/api and acme/corp_api share that id (P2 repo IDs).
        owner, name = repo_full_name.split("/", 1)
        return query.eq("owner", owner).eq("name", name)

    def _repo_by_github_id(self, github_repo_id: int) -> dict | None:
        res = self._db.table(self.TABLE).select("*").eq("github_repo_id", github_repo_id).execute()
        return res.data[0] if res.data else None

    def get_or_create_repo(self, repo_full_name: str, github_repo_id: int | None = None) -> dict:
        """
        The repo's row, keyed by GitHub's numeric repository id (P2 repo
        IDs; migrations_020). In order:
          1. a row with this github_repo_id (owner/name refreshed, so a
             rename on GitHub follows through);
          2. a legacy row for this owner/name from before migration 020:
             adopted, so its saved settings keep applying;
          3. a new row whose primary key is the numeric id, so two repos
             whose owner_name forms collide never share a row.
        Without a numeric id (old callers only) it falls back to the legacy
        owner_name key.

        The insert is an upsert with DO NOTHING, so two concurrent webhooks
        for a brand-new repo don't race into a duplicate-key error; the
        re-read returns whichever row won.
        """
        owner, name = repo_full_name.split("/", 1)
        if github_repo_id is not None:
            existing = self._repo_by_github_id(github_repo_id)
            if existing is not None:
                if (existing.get("owner"), existing.get("name")) != (owner, name):
                    self._db.table(self.TABLE).update({"owner": owner, "name": name}).eq(
                        "github_repo_id", github_repo_id).execute()
                    existing = {**existing, "owner": owner, "name": name}
                self.get_or_create_settings(github_repo_id)
                return existing
            legacy = self._by_owner_name(self._db.table(self.TABLE).select("*"), repo_full_name).is_(
                "github_repo_id", "null").execute()
            if legacy.data:
                row_id = legacy.data[0]["id"]
                self._db.table(self.TABLE).update({"github_repo_id": github_repo_id}).eq("id", row_id).execute()
                self.get_or_create_settings(github_repo_id)
                return self._repo_by_github_id(github_repo_id)

        repo_id = str(github_repo_id) if github_repo_id is not None else repo_full_name.replace("/", "_")
        row = {"id": repo_id, "name": name, "owner": owner, "language": "TypeScript"}
        if github_repo_id is not None:
            row["github_repo_id"] = github_repo_id
        try:
            self._db.table(self.TABLE).upsert(row, on_conflict="id", ignore_duplicates=True).execute()
        except APIError as e:
            # DO NOTHING never raises for the race itself; anything here is
            # a real failure (connection, schema), so it isn't swallowed.
            logger.exception("Unexpected error upserting repo %s: %s", repo_full_name, e)
            raise

        res = self._db.table(self.TABLE).select("*").eq("id", repo_id).execute()
        if not res.data:
            raise RuntimeError(f"Repo {repo_full_name} not found immediately after upsert")
        if github_repo_id is not None:
            self.get_or_create_settings(github_repo_id)
        return res.data[0]

    def set_repo_installed(self, repo_full_name: str, installed: bool) -> None:
        """
        Driven by the "installation"/"installation_repositories" webhook
        events. Update-only, not upsert: a removal for a repo this app never
        saw has no row, and that's fine. An added repo goes through
        get_or_create_repo first, so its row exists by the time this runs.
        """
        self._by_owner_name(self._db.table(self.TABLE).update({"installed": installed}), repo_full_name).execute()

    def list_repos(self, repo_names=None) -> list[dict]:
        if repo_names is not None and not repo_names:
            return []
        query = self._db.table(self.TABLE).select("id, github_repo_id, owner, name, language, installed")
        if repo_names is not None:
            # repositories has no repo_full_name column; narrow by owner,
            # then keep only rows whose exact owner/name is in the set.
            query = query.in_("owner", sorted({n.split("/", 1)[0] for n in repo_names}))
        repos_res = query.execute()
        repos = repos_res.data or []
        if repo_names is not None:
            repos = [r for r in repos if f"{r['owner']}/{r['name']}" in repo_names]
        
        # Every repo's latest review in one query (I-10), not one per repo.
        names = sorted(f"{r['owner']}/{r['name']}" for r in repos)
        latest_by_repo = {}
        if names:
            latest_res = self._db.rpc("latest_review_per_repo", {"repo_names": names}).execute()
            latest_by_repo = {row["repo_full_name"]: row for row in latest_res.data or []}

        results = []
        for r in repos:
            # The numeric GitHub id is what the settings routes take (P2 repo
            # IDs). A row the backfill hasn't reached yet keeps its legacy id.
            repo_id = str(r["github_repo_id"]) if r.get("github_repo_id") is not None else r["id"]
            repo_full_name = f"{r['owner']}/{r['name']}"
            latest = latest_by_repo.get(repo_full_name)
            
            status = "healthy"
            acs_score = 100.0
            last_review_date = ""
            
            if latest:
                last_review_date = latest.get("created_at") or ""
                score = latest.get("acs_score")
                if score is not None:
                    acs_score = float(score)
                    if acs_score >= 80:
                        status = "healthy"
                    elif acs_score >= 50:
                        status = "warning"
                    else:
                        status = "critical"
                        
            results.append({
                "id": repo_id,
                "name": r["name"],
                "owner": r["owner"],
                "lastReviewDate": last_review_date,
                "acsScore": acs_score,
                "status": status,
                "language": r.get("language", "TypeScript"),
                # Existing rows created before migrations_011 have no
                # `installed` column value cached here yet at the Python
                # level if the DB migration hasn't run — default True
                # matches the migration's own column default/backfill.
                "installed": r.get("installed") if r.get("installed") is not None else True,
            })
        return results

    _SETTINGS_DEFAULTS = {
        "enable_ai_review": True,
        "enable_auto_fix": False,
        "enable_hitl": True,
        "security_scan": True,
        "architecture_scan": True,
        "logic_scan": True,
    }

    def get_or_create_settings(self, github_repo_id: int, repo_full_name: str | None = None) -> dict:
        """
        The repo's settings, looked up by GitHub's numeric repository id (P2
        repo IDs). A repo with no settings row gets the defaults; a legacy
        row (keyed only by repo_id) is adopted, so a saved choice survives.
        With repo_full_name, a repo with no row at all is registered first.
        """
        res = self._db.table(self.SETTINGS_TABLE).select("*").eq("github_repo_id", github_repo_id).execute()
        if res.data:
            return res.data[0]
        repo = self._repo_by_github_id(github_repo_id)
        if repo is None:
            if repo_full_name is None:
                raise LookupError(f"No repository with github_repo_id {github_repo_id}")
            self.get_or_create_repo(repo_full_name, github_repo_id=github_repo_id)
            return self.get_or_create_settings(github_repo_id)
        row = {"repo_id": repo["id"], "github_repo_id": github_repo_id, **self._SETTINGS_DEFAULTS}
        self._db.table(self.SETTINGS_TABLE).upsert(row, on_conflict="repo_id", ignore_duplicates=True).execute()
        self._db.table(self.SETTINGS_TABLE).update({"github_repo_id": github_repo_id}).eq(
            "repo_id", repo["id"]).execute()
        res = self._db.table(self.SETTINGS_TABLE).select("*").eq("github_repo_id", github_repo_id).execute()
        return res.data[0] if res.data else row

    def update_settings(self, github_repo_id: int, updates: dict) -> dict:
        allowed = set(self._SETTINGS_DEFAULTS)
        filtered = {k: v for k, v in updates.items() if k in allowed}
        self.get_or_create_settings(github_repo_id)
        res = self._db.table(self.SETTINGS_TABLE).update(filtered).eq("github_repo_id", github_repo_id).execute()
        return res.data[0] if res.data else self.get_or_create_settings(github_repo_id)

    def update_repo_stats(self, repo_full_name: str, acs_score: float | None, last_review_at: str) -> None:
        """Called from the review pipeline's finalize_and_post step. Note
        list_repos() above computes acsScore/lastReviewDate dynamically from
        the reviews table and does not read these columns back — this is a
        write-only cache, kept for whatever later consumer wants a fast
        lookup without joining reviews."""
        self._by_owner_name(self._db.table(self.TABLE).update(
            {"acs_score": acs_score, "last_review_at": last_review_at}
        ), repo_full_name).execute()
