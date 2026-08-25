"""
Golden-PR fixtures for the review-quality eval harness.

Each fixture is a realistic (diff, AST payload) pair a real PR could
produce, plus a hand-labeled list of findings a good review should
surface. This is the piece the CTO audit correctly flagged as missing
entirely: routing/scoring/verification all had tests proving the plumbing
works, but nothing measured whether the agents' actual output is any
good. This file is the fixture format that question needs; see
scripts/run_golden_eval.py for how to point it at a real model.

Deliberately small (2 fixtures) to start — this is meant to grow as real
false-positive/false-negative examples get promoted into it from
production reviews, not to be exhaustive on day one.
"""
from dataclasses import dataclass

from app.schemas.ast_payload import ASTAnalyzerPayload, DependencyEdge, SymbolRef
from tests.eval.metrics import ExpectedFinding


@dataclass(frozen=True)
class GoldenPR:
    name: str
    diff_text: str
    ast_payload: ASTAnalyzerPayload
    expected_findings: list[ExpectedFinding]


GOLDEN_PRS: list[GoldenPR] = [
    GoldenPR(
        name="layer_crossing_repository_to_http_client",
        diff_text=(
            "diff --git a/src/repositories/user_repo.ts b/src/repositories/user_repo.ts\n"
            "--- a/src/repositories/user_repo.ts\n"
            "+++ b/src/repositories/user_repo.ts\n"
            "@@ -1,3 +1,4 @@\n"
            "+import { httpClient } from '../http/client';\n"
            " export class UserRepo {\n"
            "   async getUser(id: string) {\n"
            "+    return httpClient.get(`/users/${id}`);\n"
            "   }\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=101,
            changed_files=["src/repositories/user_repo.ts"],
            symbols=[
                SymbolRef(file_path="src/repositories/user_repo.ts", symbol_name="UserRepo", kind="class", line=2),
                SymbolRef(file_path="src/repositories/user_repo.ts", symbol_name="getUser", kind="function", line=3),
            ],
            dependency_graph=[
                DependencyEdge(
                    from_file="src/repositories/user_repo.ts",
                    to_file="src/http/client.ts",
                    imported_symbols=["httpClient"],
                ),
            ],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/repositories/user_repo.ts",
                severity="high",
                description_contains="layer",
            ),
        ],
    ),
    GoldenPR(
        name="clean_pr_no_findings_expected",
        diff_text=(
            "diff --git a/src/utils/format_date.ts b/src/utils/format_date.ts\n"
            "--- a/src/utils/format_date.ts\n"
            "+++ b/src/utils/format_date.ts\n"
            "@@ -1,3 +1,3 @@\n"
            "-export function formatDate(d: Date): string {\n"
            "+export function formatDate(d: Date, locale = 'en-US'): string {\n"
            "   return d.toLocaleDateString();\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=102,
            changed_files=["src/utils/format_date.ts"],
            symbols=[
                SymbolRef(file_path="src/utils/format_date.ts", symbol_name="formatDate", kind="function", line=1),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],  # a good reviewer stays quiet on a trivial, correct change
    ),
]
