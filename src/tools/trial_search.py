from pydantic import BaseModel, Field

from azure_functions_agents import tool

from _trial_index_core import search_trials


class TrialSearchParams(BaseModel):
    query: str = Field(description="Natural-language Contoso Trials question.")
    drug_name: str | None = Field(
        default=None, description="Exact drug filter when the user names a drug."
    )
    study_id: str | None = Field(
        default=None, description="Exact study ID filter when the user names a study."
    )
    quarter: str | None = Field(
        default=None, description="Exact quarter filter such as 2026Q1 or 2026Q2."
    )


@tool(
    name="trial_search",
    description="Search synthetic Contoso Trials drug, study, safety, efficacy, and eligibility evidence.",
    schema=TrialSearchParams,
)
def trial_search(params: TrialSearchParams) -> list[dict[str, str]]:
    return search_trials(
        query=params.query,
        drug_name=params.drug_name,
        study_id=params.study_id,
        quarter=params.quarter,
    )
