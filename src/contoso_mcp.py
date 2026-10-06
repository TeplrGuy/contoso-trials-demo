import json
from typing import Any

from tools._trial_index_core import search_trials


_LONG_COMPARISON_NOTE = (
    "This intentionally verbose schema exists only in contoso-toolbox-flat to "
    "measure the prompt cost of sending unused definitions on every turn. It is "
    "not the recommended production description style. The operation returns "
    "synthetic Contoso Trials demonstration metadata and must not be used instead "
    "of trial_search for drug, study, safety, efficacy, or eligibility facts."
)

TOOLS = [
    {
        "name": "trial_search",
        "description": "Search synthetic Contoso Trials drug, study, safety, efficacy, and eligibility evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language question."},
                "drug_name": {"type": "string", "description": "Exact drug filter."},
                "study_id": {"type": "string", "description": "Exact study ID filter."},
                "quarter": {"type": "string", "description": "Exact quarter filter."},
            },
            "required": ["query"],
        },
    },
]

for name, purpose in [
    ("list_studies", "List study catalog metadata by phase and quarter."),
    ("get_site_status", "Read synthetic site activation and recruiting status."),
    ("list_deviations", "List synthetic protocol deviation categories."),
    ("get_lab_trend", "Read synthetic aggregate laboratory trend metadata."),
    ("draft_csr_section", "Draft a non-authoritative CSR section outline."),
    ("lookup_visit_window", "Look up synthetic protocol visit-window metadata."),
    ("safety_narrative", "Create a non-authoritative safety narrative outline."),
    ("regulatory_clock", "Read synthetic regulatory milestone metadata."),
]:
    TOOLS.append(
        {
            "name": name,
            "description": f"{purpose} {_LONG_COMPARISON_NOTE}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Optional synthetic Contoso Trials study ID.",
                    },
                    "drug_name": {
                        "type": "string",
                        "description": "Optional synthetic Contoso Trials drug name.",
                    },
                },
            },
        }
    )


def _result(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "isError": is_error,
    }


def handle_mcp(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    method = payload.get("method")
    request_id = payload.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "Contoso Trials tools", "version": "1.0.0"},
            },
        }, 200
    if method == "notifications/initialized":
        return None, 204
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS},
        }, 200
    if method == "tools/call":
        params = payload.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            if name == "trial_search":
                output = search_trials(
                    query=str(arguments.get("query", "")),
                    drug_name=arguments.get("drug_name"),
                    study_id=arguments.get("study_id"),
                    quarter=arguments.get("quarter"),
                )
            elif name in {tool["name"] for tool in TOOLS[1:]}:
                output = {
                    "status": "comparison_only",
                    "tool": name,
                    "message": (
                        "This synthetic Contoso Trials comparison tool is not "
                        "used for factual retrieval. Use trial_search."
                    ),
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _result({"error": f"Unknown tool: {name}"}, is_error=True),
                }, 200
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": _result(output),
            }, 200
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": _result(
                    {"error": f"{type(exc).__name__}: {exc}"}, is_error=True
                ),
            }, 200
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }, 404
