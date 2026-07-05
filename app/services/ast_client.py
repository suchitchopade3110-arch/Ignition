"""
Async bridge to the persistent Bun/ts-morph HTTP service.

Deliberately NOT a subprocess-per-PR call — that re-pays full Project
initialization (tsconfig resolution, module graph) every time and discards
the benefit of a warm per-repo cache. This client assumes server.ts is
already running and holding that cache.

Sends a `source` descriptor rather than just a diff_url: the analyzer
supports either a public git remote (HTTPS recommended — SSH requires a
key mounted on the analyzer container) or a downloadable zip.
"""
import httpx

from app.schemas.ast_payload import ASTAnalyzerPayload


class ASTClient:
    def __init__(self, base_url: str, timeout: float = 90.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def analyze_git(
        self, repo_full_name: str, pr_number: int, clone_url: str, ref: str
    ) -> ASTAnalyzerPayload:
        return await self._post_analyze(
            repo_full_name, pr_number, {"type": "git", "url": clone_url, "ref": ref}
        )

    async def analyze_zip(
        self, repo_full_name: str, pr_number: int, zip_url: str
    ) -> ASTAnalyzerPayload:
        return await self._post_analyze(
            repo_full_name, pr_number, {"type": "zip", "url": zip_url}
        )

    async def _post_analyze(self, repo_full_name: str, pr_number: int, source: dict) -> ASTAnalyzerPayload:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/analyze",
                json={
                    "repo_full_name": repo_full_name,
                    "pr_number": pr_number,
                    "source": source,
                },
            )
            response.raise_for_status()
            return ASTAnalyzerPayload.model_validate(response.json())