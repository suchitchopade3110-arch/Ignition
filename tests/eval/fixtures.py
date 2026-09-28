"""
Golden-PR fixtures for the review-quality eval harness.

Each fixture is a realistic (diff, AST payload) pair a real PR could
produce, plus a hand-labeled list of findings a good review should
surface. This is the piece the CTO audit correctly flagged as missing
entirely: routing/scoring/verification all had tests proving the plumbing
works, but nothing measured whether the agents' actual output is any
good. This file is the fixture format that question needs; see
scripts/run_golden_eval.py for how to point it at a real model.

23 fixtures, hand-authored (not pulled from real GitHub PRs — this is a
demo app with no production history to promote incidents from yet).
Deliberately varied rather than exhaustive:
  - Architecture (agent_2a_struct): a contextual layer-crossing judgment
    call, a genuine `fact_checked` boundary violation, an API contract
    break, a schema/DTO mismatch, a contextual cross-module dependency
    concern, a hallucination "trap" (decoy old symbol name in a comment),
    and a clean same-layer refactor.
  - Logic/chaos (agent_2b_chaos): N+1 query, unhandled-null edge case,
    off-by-one, an unguarded read-modify-write race, plus two clean PRs.
  - Security/supply-chain (agent_2c_security): a known-CVE package, a
    typosquatted package name, two clean dependency bumps, and a mixed
    PR (one vulnerable package, one clean one in the same lockfile bump).
  - Deterministic gate (agent_1_gate): two fixtures that should never
    reach the agents at all — a banned `eval(` call and a direct
    (one-hop) boundary-violating import — both expect zero verified
    findings because the PR is rejected before any agent runs.
  - Clean/no-op PRs: docs-only and test-only changes.

Two notes on realism trade-offs, both deliberate:

1. `ignition.boundaries.yaml`'s layer globs (`app/repositories/**`,
   `app/main.py`, etc.) are THIS repo's own paths — boundary_spec.py
   always loads Ignition's own spec file regardless of which repo a PR
   targets (see load_default_boundary_spec's docstring), so the two
   fixtures that need to exercise real boundary-rule matching
   (fact_checked_*, hard_gate_rejects_direct_boundary_violation_edge) use
   Ignition-style `app/` paths rather than the generic `acme/widgets`
   paths the other fixtures use. Everything else in this file is a
   generic hypothetical target repo, same as the original two fixtures.

2. Security fixtures make REAL network calls when actually run (OSV.dev
   for Phase 1, the live npm registry for Phase 1.5) — see
   agent_2c_security.py. A "freshly-published package" fixture is
   deliberately NOT included: that check depends on real, live publish
   timestamps that can't be hand-authored into a stable fixture. The
   known-CVE and typosquat fixtures below use old, stable, well-documented
   npm packages precisely so their OSV/naming signal won't drift.
"""
from dataclasses import dataclass

from app.schemas.ast_payload import ASTAnalyzerPayload, DependencyEdge, PackageRef, SymbolRef
from tests.eval.metrics import ExpectedFinding


@dataclass(frozen=True)
class GoldenPR:
    name: str
    diff_text: str
    ast_payload: ASTAnalyzerPayload
    expected_findings: list[ExpectedFinding]


GOLDEN_PRS: list[GoldenPR] = [
    # ---------------------------------------------------------------
    # Architecture (agent_2a_struct)
    # ---------------------------------------------------------------
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
        # Exercises the ONE path a genuine fact_checked verdict is
        # reachable through: the gate's boundary check only looks at
        # literal single edges in the dependency graph, so an edge routed
        # through an intermediate file that isn't itself classified into
        # any declared layer (here: "app/shared/index.ts", outside
        # ignition.boundaries.yaml's globs) never trips it. But Agent 2A
        # can still name the *real* two logical endpoints
        # (repositories -> routes) as its dependency_edge_ref, and
        # symbol_lookup.py's barrel-hop resolution confirms that claim as
        # real (not a hallucination) via the two-hop path through the
        # unclassified file — at which point is_boundary_violation checks
        # the true endpoints directly and the Critic can tag it
        # fact_checked. See app/graph/verification/symbol_lookup.py's
        # _find_near_miss_edge and boundary_spec.py's is_boundary_violation.
        name="fact_checked_repository_reaches_routes_via_barrel",
        diff_text=(
            "diff --git a/app/repositories/ledger_repo.py b/app/repositories/ledger_repo.py\n"
            "--- a/app/repositories/ledger_repo.py\n"
            "+++ b/app/repositories/ledger_repo.py\n"
            "@@ -1,4 +1,6 @@\n"
            "+from app.shared import get_current_request_context\n"
            " class LedgerRepo:\n"
            "     def record(self, entry):\n"
            "+        get_current_request_context().attach(entry)\n"
            "         self._db.insert(entry)\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=201,
            changed_files=["app/repositories/ledger_repo.py"],
            symbols=[
                SymbolRef(file_path="app/repositories/ledger_repo.py", symbol_name="LedgerRepo", kind="class", line=2),
                SymbolRef(file_path="app/repositories/ledger_repo.py", symbol_name="record", kind="function", line=3),
            ],
            dependency_graph=[
                # Neither hop matches a boundary rule on its own — the
                # barrel file ("app/shared/index.ts") isn't in any
                # declared layer, so the gate's literal per-edge scan
                # (agent_1_gate.py) never fires on either one.
                DependencyEdge(
                    from_file="app/repositories/ledger_repo.py",
                    to_file="app/shared/index.ts",
                    imported_symbols=["get_current_request_context"],
                ),
                DependencyEdge(
                    from_file="app/shared/index.ts",
                    to_file="app/main.py",
                    imported_symbols=["get_current_request_context"],
                ),
            ],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="app/repositories/ledger_repo.py",
                severity="high",
                description_contains="layer",
            ),
        ],
    ),
    GoldenPR(
        name="contextual_api_contract_break_camelcase_rename",
        diff_text=(
            "diff --git a/src/api/types/UserPayload.ts b/src/api/types/UserPayload.ts\n"
            "--- a/src/api/types/UserPayload.ts\n"
            "+++ b/src/api/types/UserPayload.ts\n"
            "@@ -1,4 +1,4 @@\n"
            " export interface UserPayload {\n"
            "-  userId: string;\n"
            "+  user_id: string;\n"
            "   displayName: string;\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=102,
            changed_files=["src/api/types/UserPayload.ts"],
            symbols=[
                SymbolRef(file_path="src/api/types/UserPayload.ts", symbol_name="UserPayload", kind="interface", line=1),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/api/types/UserPayload.ts",
                severity="high",
                description_contains="contract",
            ),
        ],
    ),
    GoldenPR(
        name="contextual_schema_dto_field_type_mismatch",
        diff_text=(
            "diff --git a/src/services/billing_service.ts b/src/services/billing_service.ts\n"
            "--- a/src/services/billing_service.ts\n"
            "+++ b/src/services/billing_service.ts\n"
            "@@ -1,5 +1,5 @@\n"
            " export interface Invoice {\n"
            "-  amountCents: number;\n"
            "+  amountCents: string;\n"
            "   currency: string;\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=103,
            changed_files=["src/services/billing_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/billing_service.ts", symbol_name="Invoice", kind="interface", line=1),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/services/billing_service.ts",
                severity="medium",
                description_contains="type",
            ),
        ],
    ),
    GoldenPR(
        name="contextual_service_bypasses_orchestration_abstraction",
        diff_text=(
            "diff --git a/src/services/checkout_service.ts b/src/services/checkout_service.ts\n"
            "--- a/src/services/checkout_service.ts\n"
            "+++ b/src/services/checkout_service.ts\n"
            "@@ -1,4 +1,5 @@\n"
            "+import { runWorkflow } from '../orchestration/workflow_engine';\n"
            " export class CheckoutService {\n"
            "   async completeOrder(orderId: string) {\n"
            "+    return runWorkflow('checkout', { orderId });\n"
            "   }\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=104,
            changed_files=["src/services/checkout_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/checkout_service.ts", symbol_name="CheckoutService", kind="class", line=2),
                SymbolRef(file_path="src/services/checkout_service.ts", symbol_name="completeOrder", kind="function", line=3),
            ],
            dependency_graph=[
                DependencyEdge(
                    from_file="src/services/checkout_service.ts",
                    to_file="src/orchestration/workflow_engine.ts",
                    imported_symbols=["runWorkflow"],
                ),
            ],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/services/checkout_service.ts",
                severity="medium",
                description_contains="orchestration",
            ),
        ],
    ),
    GoldenPR(
        # Trap fixture: the diff renames a function and leaves the old
        # name mentioned only in a comment. A good review has nothing
        # real to flag (the rename itself is complete and consistent) —
        # this checks the pipeline doesn't invent a finding about the
        # decoy name rather than checking hallucination-rejection
        # directly (which isn't fixture-controllable; see this file's
        # module docstring on what these fixtures can and can't force).
        name="clean_pr_rename_with_decoy_old_name_in_comment",
        diff_text=(
            "diff --git a/src/services/notification_service.ts b/src/services/notification_service.ts\n"
            "--- a/src/services/notification_service.ts\n"
            "+++ b/src/services/notification_service.ts\n"
            "@@ -1,5 +1,5 @@\n"
            "-// formerly sendAlert(), renamed for clarity\n"
            "-export function sendAlert(userId: string, message: string) {\n"
            "+// formerly notifyUser(), renamed to sendUserAlert for clarity\n"
            "+export function sendUserAlert(userId: string, message: string) {\n"
            "   return dispatch(userId, message);\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=105,
            changed_files=["src/services/notification_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/notification_service.ts", symbol_name="sendUserAlert", kind="function", line=2),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
    GoldenPR(
        name="clean_pr_refactor_within_single_layer",
        diff_text=(
            "diff --git a/src/services/pricing_service.ts b/src/services/pricing_service.ts\n"
            "--- a/src/services/pricing_service.ts\n"
            "+++ b/src/services/pricing_service.ts\n"
            "@@ -1,7 +1,10 @@\n"
            " export class PricingService {\n"
            "   calculateTotal(items: Item[]): number {\n"
            "-    return items.reduce((sum, i) => sum + i.price * i.qty, 0);\n"
            "+    return items.reduce((sum, i) => sum + this._lineTotal(i), 0);\n"
            "   }\n"
            "+\n"
            "+  private _lineTotal(item: Item): number {\n"
            "+    return item.price * item.qty;\n"
            "+  }\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=106,
            changed_files=["src/services/pricing_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/pricing_service.ts", symbol_name="PricingService", kind="class", line=1),
                SymbolRef(file_path="src/services/pricing_service.ts", symbol_name="calculateTotal", kind="function", line=2),
                SymbolRef(file_path="src/services/pricing_service.ts", symbol_name="_lineTotal", kind="function", line=6),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
    # ---------------------------------------------------------------
    # Logic & chaos (agent_2b_chaos)
    # ---------------------------------------------------------------
    GoldenPR(
        name="n_plus_one_query_in_order_summary_loop",
        diff_text=(
            "diff --git a/src/services/order_service.ts b/src/services/order_service.ts\n"
            "--- a/src/services/order_service.ts\n"
            "+++ b/src/services/order_service.ts\n"
            "@@ -8,6 +8,10 @@ export class OrderService {\n"
            "   async getOrderSummaries(orderIds: string[]) {\n"
            "-    return orderIds.map(id => ({ id }));\n"
            "+    const summaries = [];\n"
            "+    for (const id of orderIds) {\n"
            "+      const order = await this.db.orders.findOne({ id });\n"
            "+      summaries.push({ id, total: order.total });\n"
            "+    }\n"
            "+    return summaries;\n"
            "   }\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=201,
            changed_files=["src/services/order_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/order_service.ts", symbol_name="getOrderSummaries", kind="function", line=9),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/services/order_service.ts",
                severity="medium",
                description_contains="n+1",
            ),
        ],
    ),
    GoldenPR(
        name="unhandled_null_after_optional_field_change",
        diff_text=(
            "diff --git a/src/services/user_profile_service.ts b/src/services/user_profile_service.ts\n"
            "--- a/src/services/user_profile_service.ts\n"
            "+++ b/src/services/user_profile_service.ts\n"
            "@@ -1,5 +1,8 @@\n"
            " export interface User {\n"
            "   name: string;\n"
            "-  address: Address;\n"
            "+  address?: Address;\n"
            " }\n"
            "+\n"
            "+export function getCity(user: User): string {\n"
            "+  return user.address.city;\n"
            "+}\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=202,
            changed_files=["src/services/user_profile_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/user_profile_service.ts", symbol_name="User", kind="interface", line=1),
                SymbolRef(file_path="src/services/user_profile_service.ts", symbol_name="getCity", kind="function", line=6),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/services/user_profile_service.ts",
                severity="high",
                description_contains="null",
            ),
        ],
    ),
    GoldenPR(
        name="off_by_one_in_pagination_slice",
        diff_text=(
            "diff --git a/src/services/pagination_service.ts b/src/services/pagination_service.ts\n"
            "--- a/src/services/pagination_service.ts\n"
            "+++ b/src/services/pagination_service.ts\n"
            "@@ -1,4 +1,4 @@\n"
            " export function getPage<T>(items: T[], pageIndex: number, pageSize: number): T[] {\n"
            "-  return items.slice(pageIndex * pageSize, (pageIndex + 1) * pageSize);\n"
            "+  return items.slice(pageIndex * pageSize, pageIndex * pageSize + pageSize - 1);\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=203,
            changed_files=["src/services/pagination_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/pagination_service.ts", symbol_name="getPage", kind="function", line=1),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/services/pagination_service.ts",
                severity="medium",
                description_contains="off-by-one",
            ),
        ],
    ),
    GoldenPR(
        name="unguarded_read_modify_write_race_in_rate_limiter",
        diff_text=(
            "diff --git a/src/services/rate_limiter.ts b/src/services/rate_limiter.ts\n"
            "--- a/src/services/rate_limiter.ts\n"
            "+++ b/src/services/rate_limiter.ts\n"
            "@@ -1,6 +1,10 @@\n"
            " export class RateLimiter {\n"
            "-  increment(key: string) {}\n"
            "+  async increment(key: string) {\n"
            "+    const current = await this.store.get(key);\n"
            "+    await this.store.set(key, current + 1);\n"
            "+  }\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=204,
            changed_files=["src/services/rate_limiter.ts"],
            symbols=[
                SymbolRef(file_path="src/services/rate_limiter.ts", symbol_name="RateLimiter", kind="class", line=1),
                SymbolRef(file_path="src/services/rate_limiter.ts", symbol_name="increment", kind="function", line=2),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="src/services/rate_limiter.ts",
                severity="high",
                description_contains="race",
            ),
        ],
    ),
    GoldenPR(
        name="clean_pr_added_input_validation_guard",
        diff_text=(
            "diff --git a/src/services/signup_service.ts b/src/services/signup_service.ts\n"
            "--- a/src/services/signup_service.ts\n"
            "+++ b/src/services/signup_service.ts\n"
            "@@ -1,4 +1,7 @@\n"
            " export function registerUser(email: string): void {\n"
            "+  if (!email || !email.includes('@')) {\n"
            "+    throw new Error('Invalid email address');\n"
            "+  }\n"
            "   createAccount(email);\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=205,
            changed_files=["src/services/signup_service.ts"],
            symbols=[
                SymbolRef(file_path="src/services/signup_service.ts", symbol_name="registerUser", kind="function", line=1),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
    GoldenPR(
        name="clean_pr_extracted_named_constant_no_behavior_change",
        diff_text=(
            "diff --git a/src/services/retry_policy.ts b/src/services/retry_policy.ts\n"
            "--- a/src/services/retry_policy.ts\n"
            "+++ b/src/services/retry_policy.ts\n"
            "@@ -1,4 +1,5 @@\n"
            "+const MAX_RETRIES = 3;\n"
            " export function shouldRetry(attempt: number): boolean {\n"
            "-  return attempt < 3;\n"
            "+  return attempt < MAX_RETRIES;\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=206,
            changed_files=["src/services/retry_policy.ts"],
            symbols=[
                SymbolRef(file_path="src/services/retry_policy.ts", symbol_name="shouldRetry", kind="function", line=2),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
    # ---------------------------------------------------------------
    # Security & supply chain (agent_2c_security)
    # ---------------------------------------------------------------
    GoldenPR(
        name="known_vulnerable_package_lodash_4_17_15",
        diff_text=(
            "diff --git a/package.json b/package.json\n"
            "--- a/package.json\n"
            "+++ b/package.json\n"
            "@@ -8,6 +8,7 @@\n"
            "   \"dependencies\": {\n"
            "+    \"lodash\": \"4.17.15\",\n"
            "     \"express\": \"4.18.2\"\n"
            "   }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=301,
            changed_files=["package.json"],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[PackageRef(name="lodash", version="4.17.15")],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="package.json",
                severity="high",
                description_contains="vulnerability",
            ),
        ],
    ),
    GoldenPR(
        name="typosquatted_package_crossenv",
        diff_text=(
            "diff --git a/package.json b/package.json\n"
            "--- a/package.json\n"
            "+++ b/package.json\n"
            "@@ -8,6 +8,7 @@\n"
            "   \"dependencies\": {\n"
            "+    \"crossenv\": \"1.0.0\",\n"
            "     \"express\": \"4.18.2\"\n"
            "   }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=302,
            changed_files=["package.json"],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[PackageRef(name="crossenv", version="1.0.0")],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="package.json",
                severity="medium",
                description_contains="typosquat",
            ),
        ],
    ),
    GoldenPR(
        name="clean_pr_adds_legitimate_popular_package",
        diff_text=(
            "diff --git a/package.json b/package.json\n"
            "--- a/package.json\n"
            "+++ b/package.json\n"
            "@@ -8,6 +8,7 @@\n"
            "   \"dependencies\": {\n"
            "+    \"axios\": \"1.6.8\",\n"
            "     \"express\": \"4.18.2\"\n"
            "   }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=303,
            changed_files=["package.json"],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[PackageRef(name="axios", version="1.6.8")],
        ),
        expected_findings=[],
    ),
    GoldenPR(
        name="clean_pr_bumps_existing_dependency_patch_version",
        diff_text=(
            "diff --git a/package.json b/package.json\n"
            "--- a/package.json\n"
            "+++ b/package.json\n"
            "@@ -6,7 +6,7 @@\n"
            "   \"dependencies\": {\n"
            "-    \"express\": \"4.18.2\",\n"
            "+    \"express\": \"4.18.3\",\n"
            "     \"lodash\": \"4.17.21\"\n"
            "   }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=304,
            changed_files=["package.json"],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[PackageRef(name="express", version="4.18.3")],
        ),
        expected_findings=[],
    ),
    GoldenPR(
        name="mixed_lockfile_bump_one_vulnerable_one_clean",
        diff_text=(
            "diff --git a/package.json b/package.json\n"
            "--- a/package.json\n"
            "+++ b/package.json\n"
            "@@ -6,7 +6,9 @@\n"
            "   \"dependencies\": {\n"
            "-    \"lodash\": \"4.17.10\",\n"
            "+    \"lodash\": \"4.17.15\",\n"
            "+    \"axios\": \"1.6.8\",\n"
            "     \"express\": \"4.18.2\"\n"
            "   }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=305,
            changed_files=["package.json"],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[
                PackageRef(name="lodash", version="4.17.15"),
                PackageRef(name="axios", version="1.6.8"),
            ],
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="package.json",
                severity="high",
                description_contains="vulnerability",
            ),
        ],
    ),
    # ---------------------------------------------------------------
    # Deterministic gate (agent_1_gate) — should never reach the agents.
    # Both expect zero verified findings: run_golden_eval.py short-circuits
    # on hard_rule_violation and scores against an empty findings list, so
    # a correctly-functioning gate scores these as a perfect match.
    # ---------------------------------------------------------------
    GoldenPR(
        name="hard_gate_rejects_eval_call_in_added_code",
        diff_text=(
            "diff --git a/src/utils/dynamic_runner.ts b/src/utils/dynamic_runner.ts\n"
            "--- a/src/utils/dynamic_runner.ts\n"
            "+++ b/src/utils/dynamic_runner.ts\n"
            "@@ -1,3 +1,5 @@\n"
            " export function runExpression(expr: string) {\n"
            "+  return eval(expr);\n"
            " }\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=401,
            changed_files=["src/utils/dynamic_runner.ts"],
            symbols=[
                SymbolRef(file_path="src/utils/dynamic_runner.ts", symbol_name="runExpression", kind="function", line=1),
            ],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
    GoldenPR(
        name="hard_gate_rejects_direct_boundary_violation_edge",
        diff_text=(
            "diff --git a/app/repositories/customer_repo.py b/app/repositories/customer_repo.py\n"
            "--- a/app/repositories/customer_repo.py\n"
            "+++ b/app/repositories/customer_repo.py\n"
            "@@ -1,3 +1,4 @@\n"
            "+from app.main import app\n"
            " class CustomerRepo:\n"
            "     def get(self, id):\n"
            "         ...\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=402,
            changed_files=["app/repositories/customer_repo.py"],
            symbols=[
                SymbolRef(file_path="app/repositories/customer_repo.py", symbol_name="CustomerRepo", kind="class", line=2),
            ],
            dependency_graph=[
                DependencyEdge(
                    from_file="app/repositories/customer_repo.py",
                    to_file="app/main.py",
                    imported_symbols=["app"],
                ),
            ],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
    # ---------------------------------------------------------------
    # Clean / no-op PRs
    # ---------------------------------------------------------------
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
    GoldenPR(
        name="clean_pr_documentation_only_change",
        diff_text=(
            "diff --git a/docs/CONTRIBUTING.md b/docs/CONTRIBUTING.md\n"
            "--- a/docs/CONTRIBUTING.md\n"
            "+++ b/docs/CONTRIBUTING.md\n"
            "@@ -1,3 +1,5 @@\n"
            " # Contributing\n"
            "+\n"
            "+Run `npm test` before opening a PR.\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=501,
            changed_files=["docs/CONTRIBUTING.md"],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
    GoldenPR(
        name="clean_pr_test_file_added_no_prod_code_change",
        diff_text=(
            "diff --git a/src/services/__tests__/order_service.test.ts b/src/services/__tests__/order_service.test.ts\n"
            "--- /dev/null\n"
            "+++ b/src/services/__tests__/order_service.test.ts\n"
            "@@ -0,0 +1,5 @@\n"
            "+import { OrderService } from '../order_service';\n"
            "+\n"
            "+test('computes order total', () => {\n"
            "+  expect(new OrderService().calculateTotal([])).toBe(0);\n"
            "+});\n"
        ),
        ast_payload=ASTAnalyzerPayload(
            repo_full_name="acme/widgets",
            pr_number=502,
            changed_files=["src/services/__tests__/order_service.test.ts"],
            symbols=[],
            dependency_graph=[],
            hard_rule_violations=[],
            changed_packages=[],
        ),
        expected_findings=[],
    ),
]
