import json
import os
from functools import lru_cache
from typing import Any

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient


@lru_cache(maxsize=1)
def _credential() -> DefaultAzureCredential | ManagedIdentityCredential:
    client_id = os.getenv("AZURE_CLIENT_ID")
    if os.getenv("WEBSITE_SITE_NAME"):
        return ManagedIdentityCredential(client_id=client_id)
    return DefaultAzureCredential(managed_identity_client_id=client_id)


@lru_cache(maxsize=1)
def _search_client() -> SearchClient:
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"],
        index_name=os.getenv("TRIAL_INDEX_NAME", "trial-docs"),
        credential=_credential(),
    )


def _escape_filter(value: str) -> str:
    return value.replace("'", "''")


def _concise_passage(content: str, max_sentences: int = 8) -> str:
    unique_sentences: list[str] = []
    seen: set[str] = set()
    for raw_sentence in content.replace("\n", " ").split(". "):
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        normalized = sentence.rstrip(".")
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_sentences.append(f"{normalized}.")
        if len(unique_sentences) >= max_sentences:
            break
    return " ".join(unique_sentences)


def search_trials(
    query: str,
    drug_name: str | None = None,
    study_id: str | None = None,
    quarter: str | None = None,
    top: int = 3,
) -> list[dict[str, str]]:
    filters = ["sponsor_name eq 'Contoso Trials'"]
    normalized_query = query.lower()
    section_doc_type = next(
        (
            doc_type
            for doc_type, terms in {
                "safety": ("safety", "infection", "adverse", "hold rule"),
                "efficacy": ("efficacy", "endpoint", "hazard ratio"),
                "eligibility": ("eligibility", "screening", "renal", "egfr", "biologic"),
            }.items()
            if any(term in normalized_query for term in terms)
        ),
        None,
    )
    if drug_name:
        filters.append(f"drug_name eq '{_escape_filter(drug_name)}'")
    if study_id:
        filters.append(f"study_id eq '{_escape_filter(study_id)}'")
    if quarter:
        filters.append(f"quarter eq '{_escape_filter(quarter)}'")
    if section_doc_type:
        filters.append(f"doc_type eq '{section_doc_type}'")

    search_options: dict[str, Any] = {
        "search_text": query,
        "filter": " and ".join(filters),
        "query_type": "semantic",
        "semantic_configuration_name": "contoso-trials-semantic",
        "select": ["drug_name", "study_id", "quarter", "section", "content"],
        "top": max(1, min(top, 8)),
    }
    if not section_doc_type:
        search_options["scoring_profile"] = "summary-first"

    results = _search_client().search(
        **search_options,
    )
    return [
        {
            "drug": str(item["drug_name"]),
            "study_id": str(item["study_id"]),
            "quarter": str(item["quarter"]),
            "section": str(item["section"]),
            "cited_passage": _concise_passage(str(item["content"])),
        }
        for item in results
    ]


def refresh_trials(blob_name: str | None = None) -> dict[str, Any]:
    blob_service = BlobServiceClient(
        account_url=os.environ["AZURE_STORAGE_BLOB_ENDPOINT"],
        credential=_credential(),
    )
    container = blob_service.get_container_client(
        os.getenv("TRIAL_DROPS_CONTAINER", "trial-drops")
    )
    names = [blob_name] if blob_name else [
        item.name for item in container.list_blobs(name_starts_with="2026Q2")
    ]
    if not names:
        return {"status": "no_batch", "merged": 0, "files": []}

    documents: list[dict[str, Any]] = []
    processed: list[str] = []
    for name in names:
        if not name:
            continue
        payload = json.loads(container.download_blob(name).readall())
        batch = payload.get("documents")
        if not isinstance(batch, list):
            raise ValueError(f"Blob {name} does not contain a documents array")
        documents.extend(batch)
        processed.append(name)

    outcomes = _search_client().merge_or_upload_documents(documents)
    failures = [result.key for result in outcomes if not result.succeeded]
    if failures:
        raise RuntimeError(f"Search merge failed for {len(failures)} document(s)")
    return {
        "status": "merged",
        "merged": len(outcomes),
        "files": processed,
        "latest_canary": "DRUG-CANARY-AXIMAB-Q2",
    }
