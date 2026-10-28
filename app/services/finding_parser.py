"""
Shared JSON-to-Finding parsing for all four LLM-backed agent nodes.

A response that isn't a findings document at all (not JSON, or JSON that
isn't an object/list) raises FindingsParseError: the calling agent reports
itself as failed and the review is marked incomplete, instead of the old
fail-soft [] that read as "clean" (audit P0-1). One malformed finding
inside an otherwise valid document is still skipped on its own.
"""
import json
import logging

from app.graph.state import Finding

logger = logging.getLogger(__name__)


class FindingsParseError(ValueError):
    """The model's response wasn't a findings document at all. Raised (not
    swallowed into []) so the calling agent reports itself as failed and
    the review is marked incomplete instead of 'clean' (audit P0-1)."""


def parse_findings_json(raw: str, agent_name: str) -> list[Finding]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("agent=%s returned non-JSON response", agent_name)
        raise FindingsParseError(f"{agent_name}: response was not JSON") from exc
    if not isinstance(data, (list, dict)):
        raise FindingsParseError(f"{agent_name}: response JSON was {type(data).__name__}, not an object/list")

    # Models sometimes wrap the array in an object (e.g. {"findings": [...]})
    # despite instructions — accept both shapes rather than being brittle.
    items = data if isinstance(data, list) else data.get("findings", [])

    findings: list[Finding] = []
    for item in items:
        try:
            file_path = item.get("file_path") or item.get("file")
            if not file_path:
                raise KeyError("file_path/file")
            line = item.get("line") or item.get("line_number")
            if line is not None:
                line = int(line)

            dependency_edge_ref = item.get("dependency_edge_ref")
            if dependency_edge_ref is not None:
                # Must be an exact (from_file, to_file) pair to be usable by
                # the Critic's exact-lookup check — anything else is a
                # malformed field, not a claim worth carrying forward.
                if not (isinstance(dependency_edge_ref, (list, tuple)) and len(dependency_edge_ref) == 2):
                    dependency_edge_ref = None
                else:
                    dependency_edge_ref = tuple(dependency_edge_ref)

            findings.append(
                Finding(
                    agent=agent_name,
                    file_path=file_path,
                    line=line,
                    description=item["description"],
                    severity=item.get("severity", "low"),
                    suggested_patch=item.get("suggested_patch"),
                    symbol_ref=item.get("symbol_ref"),
                    dependency_edge_ref=dependency_edge_ref,
                )
            )
        except (KeyError, TypeError, ValueError):
            # One malformed finding shouldn't discard every valid one.
            logger.warning("agent=%s produced a malformed finding, skipping it: %r", agent_name, item)
            continue

    return findings
