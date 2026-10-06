# Contoso Trials demo

This sample extends the Azure Functions agents runtime with a synthetic Contoso Trials retrieval demo:

- `Contoso Trials Assistant` uses the tool-search toolbox.
- `Contoso Trials Assistant Flat` exposes the same tools without tool search for the token comparison.
- `Quarterly Refresh` runs at 06:00 UTC on the first day of Jan/Apr/Jul/Oct and calls a Python merge tool.
- Azure AI Search stores 2,000 parent drug-study-quarter summaries and 8,000 section chunks.
- The Function App hosts a custom MCP server for `trial_search` and eight comparison-only tools.
- `POST /quarterly-refresh` runs the same Python refresh path on demand.

All indexed content is synthetic Contoso Trials data. It is not real patient or proprietary data.

## Deploy

```bash
cd samples/daily-azure-report
azd env new contoso-trials
azd env set AZURE_LOCATION canadacentral
azd env set TO_EMAIL demo@contoso.com
azd up
python3 scripts/provision_data.py
python3 scripts/provision_toolboxes.py
```

`azd up` must finish before the data and toolbox scripts run. The scripts do not print Search keys, storage keys, access tokens, connection strings, or Function keys.

The supported sample regions are `canadacentral`, `canadaeast`, `centralus`, `eastus`, `eastus2`, and `northcentralus`. Do not switch regions after a failed deployment without recording the exact Azure error in `DEMO.md`.

## Main files

- `infra/main.bicep`: Contoso Trials Function App, storage, Foundry, model, Search, and RBAC.
- `scripts/provision_data.py`: creates `trial-docs`, uploads exactly 10,000 documents, and seeds the `2026Q2` blob drop.
- `scripts/provision_toolboxes.py`: creates the two Foundry toolbox versions and configures the Function App to consume them.
- `src/trial_assistant.agent.md`: tool-search chat agent.
- `src/trial_assistant_flat.agent.md`: flat-toolbox comparison agent.
- `foundry-agents/azure.yaml`: two saved Foundry prompt agents for testing the two deployed toolbox endpoints.
- `src/quarterly_refresh.agent.md`: quarterly timer agent.
- `src/tools/refresh_trial_index.py`: merge-only quarterly write tool.
- `src/contoso_mcp.py`: MCP server exposing `trial_search` plus eight comparison schemas.
- `DEMO.md`: deployment status, architecture, evidence, prompts, measurements, and best-practice checklist.

## Local settings

Copy `src/local.settings.template.json` to `src/local.settings.json` and fill in the deployed resource endpoints. The toolbox endpoint uses Entra ID scope `https://ai.azure.com/.default`; do not paste bearer tokens into settings or source files.

## Foundry prompt-agent comparison

Deploy the two saved prompt agents after the toolboxes exist:

```bash
cd foundry-agents
azd env new contoso-trials-agents \
  --subscription 8fcc5e8e-6540-4288-89e7-849e94290205 \
  --location canadacentral
azd env set AZURE_RESOURCE_GROUP rg-contoso-trials-canadacentral
azd env set AZURE_AI_PROJECT_ID \
  /subscriptions/8fcc5e8e-6540-4288-89e7-849e94290205/resourceGroups/rg-contoso-trials-canadacentral/providers/Microsoft.CognitiveServices/accounts/cog-contosotrials-5legl5fcrx/projects/cog-contosotrials-5legl5fcrx-proj
azd env set FOUNDRY_PROJECT_ENDPOINT \
  https://cog-contosotrials-5legl5fcrx.services.ai.azure.com/api/projects/cog-contosotrials-5legl5fcrx-proj
azd env set USE_EXISTING_AI_PROJECT true
azd deploy --all
```

The agents are:

- `contoso-trials-tool-search-agent`, connected to `contoso-toolbox` version 3.
- `contoso-trials-flat-toolbox-agent`, connected to `contoso-toolbox-flat` version 2.

Run the same grounded question against both:

```bash
azd ai agent invoke contoso-trials-tool-search-agent --new-session \
  "Give me a safety summary for Axumab and what the hold rules are."
azd ai agent invoke contoso-trials-flat-toolbox-agent --new-session \
  "Give me a safety summary for Axumab and what the hold rules are."
```

The subscription does not currently enable the `github_copilot_preview` harness required for native prompt-agent toolbox attachment. These agents therefore consume each toolbox's managed MCP endpoint through a project-managed-identity Foundry connection. They still test the distinct toolbox runtime surfaces without copying individual tool definitions onto the agents.

## Function App chat UI authentication

The generated chat UI stores its Function host key in browser local storage and adds
it to `/chatstream` requests. Do not append `?code=` to the UI page URL; the page does
not import that query parameter.

Open the UI, select the gear icon, and enter:

- Base URL: `https://func-contoso-trials-5legl5fcrx.azurewebsites.net`
- Key: the Function App `default` host key from **App keys**

Alternatively, initialize the UI through its URL fragment. URL-encode the key first:

```bash
BASE='https://func-contoso-trials-5legl5fcrx.azurewebsites.net'
KEY=$(az functionapp keys list \
  --resource-group rg-contoso-trials-canadacentral \
  --name func-contoso-trials-5legl5fcrx \
  --query 'functionKeys.default' -o tsv)
ENCODED_KEY=$(jq -rn --arg value "$KEY" '$value|@uri')

open "$BASE/agents/trial_assistant/#key=$ENCODED_KEY"
open "$BASE/agents/trial_assistant_flat/#key=$ENCODED_KEY"

unset KEY ENCODED_KEY
```

If the UI previously saved a wrong key or base URL, use a private browser window or
clear site data for the Function App hostname before reopening it.
