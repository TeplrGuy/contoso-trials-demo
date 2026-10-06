from pydantic import BaseModel, Field

from azure_functions_agents import tool

from _trial_index_core import refresh_trials


class RefreshTrialIndexParams(BaseModel):
    blob_name: str | None = Field(
        default=None,
        description="Optional synthetic batch blob name. Omit to process 2026Q2 drops.",
    )


@tool(
    name="refresh_trial_index",
    description="Merge a synthetic Contoso Trials quarterly blob batch into trial-docs by stable document id.",
    schema=RefreshTrialIndexParams,
)
def refresh_trial_index(params: RefreshTrialIndexParams) -> dict[str, object]:
    return refresh_trials(params.blob_name)
