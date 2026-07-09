"""
Shared JSON-to-Finding parsing for all four LLM-backed agent nodes.

Deliberately fails soft: a malformed or unexpected LLM response results in
an empty findings list for that agent, not a crashed graph run. Losing one
agent's findings for a single PR is recoverable; taking down the whole
review pipeline on a JSON parsing error is not.
"""
import json
import logging

from app.graph.state import Finding

logger = logging.getLogger(__name__)


def parse_findings_json(raw: str, agent_name: str) -> list[Finding]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("agent=%s returned non-JSON response, treating as no findings", agent_name)
        return []

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
            findings.append(
                Finding(
                    agent=agent_name,
                    file_path=file_path,
                    line=line,
                    description=item["description"],
                    severity=item.get("severity", "low"),
                    suggested_patch=item.get("suggested_patch"),
                )
            )
        except (KeyError, TypeError, ValueError):
            # One malformed finding shouldn't discard every valid one.
            logger.warning("agent=%s produced a malformed finding, skipping it: %r", agent_name, item)
            continue

    return findings
