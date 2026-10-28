#!/usr/bin/env python3
"""
Fills repositories.github_repo_id and repository_settings.github_repo_id
(migrations_020, P2 repo IDs) for rows created before that migration, with
one GET /repos/{full_name} per row.

- Idempotent: rows that already have github_repo_id are skipped.
- A repo GitHub no longer knows (deleted, or the App was removed) is
  reported under "not_found" and left as is.
- --dry-run looks the ids up and writes nothing.

Run once after migration 020, from the backend's environment (it needs
SUPABASE_URL, SUPABASE_SERVICE_KEY, GITHUB_APP_ID and GITHUB_PRIVATE_KEY):

    python scripts/backfill_github_repo_ids.py --dry-run
    python scripts/backfill_github_repo_ids.py
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPOS, SETTINGS = "repositories", "repository_settings"


def backfill(db, lookup: Callable[[str], int | None], dry_run: bool = False) -> dict:
    """`lookup(full_name) -> numeric id, or None if GitHub has no such repo`."""
    rows = (db.table(REPOS).select("id, owner, name").is_("github_repo_id", "null")
            .order("owner").order("name").execute().data or [])
    report = {"filled": 0, "not_found": []}
    for row in rows:
        full_name = f"{row['owner']}/{row['name']}"
        github_repo_id = lookup(full_name)
        if github_repo_id is None:
            report["not_found"].append(full_name)
            continue
        if dry_run:
            report["filled"] += 1
            continue
        db.table(REPOS).update({"github_repo_id": github_repo_id}).eq("id", row["id"]).execute()
        db.table(SETTINGS).update({"github_repo_id": github_repo_id}).eq("repo_id", row["id"]).execute()
        report["filled"] += 1
    return report


def github_lookup() -> Callable[[str], int | None]:
    """GET /repos/{full_name} with a token for the installation that has the
    repo, so private repos resolve too."""
    from github import Auth, Github, GithubIntegration, UnknownObjectException

    from app.config import get_settings

    settings = get_settings()
    integration = GithubIntegration(auth=Auth.AppAuth(app_id=settings.github_app_id,
                                                      private_key=settings.github_private_key))

    def lookup(full_name: str) -> int | None:
        owner, name = full_name.split("/", 1)
        try:
            installation = integration.get_repo_installation(owner, name)
            token = integration.get_access_token(installation.id).token
            return Github(auth=Auth.Token(token)).get_repo(full_name).id
        except UnknownObjectException:
            return None

    return lookup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    from app.database import get_supabase
    print(json.dumps(backfill(get_supabase(), github_lookup(), args.dry_run)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
