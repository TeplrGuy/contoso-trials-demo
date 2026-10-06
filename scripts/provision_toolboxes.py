#!/usr/bin/env python3
import json
import subprocess
import sys
from urllib.parse import urlparse
import urllib.error
import urllib.request
from typing import Any


def run(*args: str) -> str:
    return subprocess.run(
        args, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def azd_value(name: str) -> str:
    return run("azd", "env", "get-value", name)


def run_json(*args: str) -> dict[str, Any]:
    return json.loads(run(*args))


def request_json(
    method: str, url: str, token: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            content = response.read()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc


def create_toolbox(
    endpoint: str,
    token: str,
    name: str,
    mcp_url: str,
    connection_id: str,
    tool_search: bool,
) -> str:
    tools: list[dict[str, Any]] = []
    if tool_search:
        tools.append({"type": "toolbox_search"})
    mcp_tool: dict[str, Any] = {
        "type": "mcp",
        "server_label": "contoso-trials-tools",
        "server_url": mcp_url,
        "require_approval": "never",
        "project_connection_id": connection_id,
    }
    if tool_search:
        mcp_tool["tool_configs"] = {"trial_search": {"pin": True}}
    tools.append(mcp_tool)
    result = request_json(
        "POST",
        f"{endpoint}/toolboxes/{name}/versions?api-version=v1",
        token,
        {
            "description": (
                "Contoso Trials toolbox with pinned trial_search and tool search."
                if tool_search
                else "Contoso Trials flat toolbox for schema-token comparison only."
            ),
            "tools": tools,
        },
    )
    version = str(result["version"])
    if version != "1":
        run(
            "azd",
            "ai",
            "toolbox",
            "publish",
            name,
            version,
            "--project-endpoint",
            endpoint,
            "--no-prompt",
            "--output",
            "json",
        )
    return version


def main() -> int:
    endpoint = azd_value("FOUNDRY_PROJECT_ENDPOINT").rstrip("/")
    function_name = azd_value("AZURE_FUNCTION_NAME")
    resource_group = azd_value("AZURE_RESOURCE_GROUP_NAME")
    subscription_id = azd_value("AZURE_SUBSCRIPTION_ID")
    mcp_url = f"https://{function_name}.azurewebsites.net/contoso-tools/mcp"

    parsed_endpoint = urlparse(endpoint)
    account_name = parsed_endpoint.hostname.split(".", 1)[0]
    project_name = parsed_endpoint.path.removeprefix("/api/projects/")
    connection_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices"
        f"/accounts/{account_name}/projects/{project_name}/connections"
        "/contoso-trials-tools?api-version=2025-06-01"
    )
    connection = run_json(
        "az",
        "rest",
        "--method",
        "put",
        "--url",
        connection_url,
        "--body",
        json.dumps(
            {
                "properties": {
                    "category": "RemoteTool",
                    "target": mcp_url,
                    "authType": "None",
                }
            }
        ),
    )
    connection_id = connection.get("id")
    if not connection_id:
        raise RuntimeError("Foundry connection response did not contain an id")

    token = run_json(
        "az",
        "account",
        "get-access-token",
        "--scope",
        "https://ai.azure.com/.default",
        "--output",
        "json",
    )["accessToken"]
    search_version = create_toolbox(
        endpoint,
        token,
        "contoso-toolbox",
        mcp_url,
        connection_id,
        tool_search=True,
    )
    flat_version = create_toolbox(
        endpoint,
        token,
        "contoso-toolbox-flat",
        mcp_url,
        connection_id,
        tool_search=False,
    )
    search_endpoint = f"{endpoint}/toolboxes/contoso-toolbox/mcp?api-version=v1"
    flat_endpoint = f"{endpoint}/toolboxes/contoso-toolbox-flat/mcp?api-version=v1"
    run("azd", "env", "set", "TOOLBOX_CONTOSO_TOOLBOX_MCP_ENDPOINT", search_endpoint)
    run(
        "azd",
        "env",
        "set",
        "TOOLBOX_CONTOSO_TOOLBOX_FLAT_MCP_ENDPOINT",
        flat_endpoint,
    )
    run(
        "az",
        "functionapp",
        "config",
        "appsettings",
        "set",
        "--resource-group",
        resource_group,
        "--name",
        function_name,
        "--settings",
        f"TOOLBOX_CONTOSO_TOOLBOX_MCP_ENDPOINT={search_endpoint}",
        f"TOOLBOX_CONTOSO_TOOLBOX_FLAT_MCP_ENDPOINT={flat_endpoint}",
        "--output",
        "none",
    )
    run(
        "az",
        "functionapp",
        "restart",
        "--resource-group",
        resource_group,
        "--name",
        function_name,
    )
    print(
        json.dumps(
            {
                "contoso-toolbox_version": search_version,
                "contoso-toolbox-flat_version": flat_version,
                "mcp_source": mcp_url,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
