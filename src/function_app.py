import json

import azure.functions as func
from agent_framework import MCPStreamableHTTPTool
from azure_functions_agents import create_function_app
from azurefunctions.extensions.http.fastapi import Request, Response

from contoso_mcp import handle_mcp
from tools._trial_index_core import refresh_trials


_mcp_init = MCPStreamableHTTPTool.__init__


def _init_toolbox_mcp(self, *args, **kwargs):
    # Foundry Toolbox is stateless here; transport termination cancels the
    # enclosing Azure Functions request after the agent run completes.
    kwargs.setdefault("terminate_on_close", False)
    _mcp_init(self, *args, **kwargs)


MCPStreamableHTTPTool.__init__ = _init_toolbox_mcp

app = create_function_app()


@app.route(
    route="contoso-tools/mcp",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
async def contoso_tools_mcp(req: Request) -> Response:
    try:
        payload = await req.json()
    except (ValueError, json.JSONDecodeError):
        return Response(
            content=json.dumps({"error": "Request body must be JSON"}),
            status_code=400,
            media_type="application/json",
        )
    response, status = handle_mcp(payload)
    if response is None:
        return Response(status_code=status)
    return Response(
        content=json.dumps(response), status_code=status, media_type="application/json"
    )


@app.route(
    route="quarterly-refresh",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
async def quarterly_refresh_http(req: Request) -> Response:
    blob_name = None
    try:
        body = await req.json()
        if isinstance(body, dict):
            blob_name = body.get("blob_name")
    except (ValueError, json.JSONDecodeError):
        pass
    try:
        result = refresh_trials(blob_name)
        return Response(
            content=json.dumps(result), status_code=200, media_type="application/json"
        )
    except Exception as exc:
        return Response(
            content=json.dumps({"error": f"{type(exc).__name__}: {exc}"}),
            status_code=500,
            media_type="application/json",
        )
