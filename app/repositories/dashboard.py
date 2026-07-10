from datetime import datetime
import json
import collections
from app.database import get_supabase

class ReviewRepository:
    TABLE = "reviews"

    def __init__(self):
        self._db = get_supabase()

    def create_review(self, review_id: str, repo_full_name: str, pr_number: int, title: str, author: str, branch: str, commit_sha: str) -> dict:
        now = datetime.utcnow().isoformat() + "Z"
        row = {
            "id": review_id,
            "repo_full_name": repo_full_name,
            "pr_number": pr_number,
            "title": title,
            "author": author,
            "branch": branch,
            "commit_sha": commit_sha,
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

    def update_review(self, review_id: str, updates: dict) -> dict:
        # If status changes to completed/failed, set completed_at
        if "status" in updates and updates["status"] in ("completed", "failed", "rejected", "cancelled"):
            updates["completed_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Calculate duration if completed_at is set
        if "completed_at" in updates or ("status" in updates and updates["status"] in ("completed", "failed", "rejected", "cancelled")):
            review = self.get_review(review_id)
            if review:
                created_at_str = review.get("created_at")
                if created_at_str:
                    try:
                        # strip Z or offset
                        created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        completed_dt = datetime.utcnow()
                        delta = completed_dt - created_dt.replace(tzinfo=None)
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
            "github_comment_preview": row.get("github_comment_preview")
        }

    def get_review(self, review_id: str) -> dict | None:
        res = self._db.table(self.TABLE).select("*").eq("id", review_id).execute()
        return self._map_review_row(res.data[0]) if res.data else None

    def list_reviews(self, repo_name: str = None, status: str = None, severity: str = None, page: int = 1, page_size: int = 25) -> tuple[list[dict], int]:
        query = self._db.table(self.TABLE).select("*", count="exact")
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

    def list_hitl_pending(self) -> list[dict]:
        res = (
            self._db.table(self.TABLE)
            .select("*")
            .eq("status", "waiting_hitl")
            .order("created_at", desc=True)
            .execute()
        )
        return [self._map_review_row(row) for row in res.data]

    def get_stats(self) -> dict:
        # activeReviews: status="running"
        running_res = self._db.table(self.TABLE).select("id", count="exact").eq("status", "running").execute()
        active_reviews = running_res.count if running_res.count is not None else 0

        # hitlPending: status="waiting_hitl"
        hitl_res = self._db.table(self.TABLE).select("id", count="exact").eq("status", "waiting_hitl").execute()
        hitl_pending = hitl_res.count if hitl_res.count is not None else 0

        # avgAcsScore: avg acs_score across completed reviews
        completed_res = self._db.table(self.TABLE).select("acs_score").eq("status", "completed").execute()
        scores = [float(row["acs_score"]) for row in completed_res.data if row.get("acs_score") is not None]
        avg_acs_score = sum(scores) / len(scores) if scores else 0.0

        # issuesFound: sum of findings_count across reviews
        findings_res = self._db.table(self.TABLE).select("findings_count").execute()
        issues_found = sum(int(row["findings_count"]) for row in findings_res.data if row.get("findings_count") is not None)

        return {
            "activeReviews": active_reviews,
            "hitlPending": hitl_pending,
            "avgAcsScore": round(avg_acs_score, 1),
            "issuesFound": issues_found
        }

    def get_ledger_stats(self, repo_full_name: str) -> dict:
        # Fetch reviews for repo
        res = self._db.table(self.TABLE).select("*").eq("repo_full_name", repo_full_name).execute()
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
        res = self._db.table(self.TABLE).select("*").eq("repo_full_name", repo_full_name).execute()
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

    def get_or_create_repo(self, repo_full_name: str) -> dict:
        repo_id = repo_full_name.replace("/", "_")
        res = self._db.table(self.TABLE).select("*").eq("id", repo_id).execute()
        if res.data:
            return res.data[0]
            
        owner, name = repo_full_name.split("/", 1)
        row = {
            "id": repo_id,
            "name": name,
            "owner": owner,
            "language": "TypeScript"
        }
        try:
            self._db.table(self.TABLE).insert(row).execute()
            self.get_or_create_settings(repo_id, repo_full_name)
        except Exception:
            pass
        return row

    def list_repos(self) -> list[dict]:
        repos_res = self._db.table(self.TABLE).select("*").execute()
        repos = repos_res.data or []
        
        results = []
        for r in repos:
            repo_id = r["id"]
            repo_full_name = f"{r['owner']}/{r['name']}"
            
            # Fetch latest review for status & acsScore
            review_res = (
                self._db.table("reviews")
                .select("acs_score", "status", "created_at")
                .eq("repo_full_name", repo_full_name)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            latest = review_res.data[0] if review_res.data else None
            
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
                "language": r.get("language", "TypeScript")
            })
        return results

    def get_or_create_settings(self, repo_id: str, repo_full_name: str = None) -> dict:
        res = self._db.table(self.SETTINGS_TABLE).select("*").eq("repo_id", repo_id).execute()
        if res.data:
            return res.data[0]
            
        row = {
            "repo_id": repo_id,
            "enable_ai_review": True,
            "enable_auto_fix": False,
            "enable_hitl": True,
            "security_scan": True,
            "architecture_scan": True,
            "logic_scan": True
        }
        try:
            self._db.table(self.SETTINGS_TABLE).insert(row).execute()
        except Exception:
            pass
        return row

    def update_settings(self, repo_id: str, updates: dict) -> dict:
        allowed = {
            "enable_ai_review", "enable_auto_fix", "enable_hitl",
            "security_scan", "architecture_scan", "logic_scan"
        }
        filtered = {k: v for k, v in updates.items() if k in allowed}
        res = self._db.table(self.SETTINGS_TABLE).update(filtered).eq("repo_id", repo_id).execute()
        return res.data[0] if res.data else self.get_or_create_settings(repo_id)
