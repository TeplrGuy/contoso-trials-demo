#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from itertools import islice
from typing import Any, Iterable, Iterator


INDEX_NAME = "trial-docs"
QUARTERS = ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1"]
DRUGS = [
    "Axumab",
    "Belvex",
    "Coryl",
    "Dovamir",
    "Elarix",
    "Fenlora",
    "Gavent",
    "Heliqa",
    "Ibracen",
    "Jorvex",
    "Kelmora",
    "Lunatrex",
    "Mavoryn",
    "Nexalor",
    "Orphena",
    "Praxilan",
    "Quenavir",
    "Rovalent",
    "Solmira",
    "Trevaxon",
    "Umbralis",
    "Velnora",
    "Wexorin",
    "Xandrel",
    "Yorvanta",
    "Zelquar",
    "Adervex",
    "Brimora",
    "Cendrix",
    "Deltava",
    "Embracen",
    "Fostrel",
    "Glenavir",
    "Harmoxel",
    "Iverna",
    "Jastorin",
    "Kovalen",
    "Lumetra",
    "Mirevon",
    "Norvixa",
]


def run(*args: str) -> str:
    result = subprocess.run(
        args, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def azd_value(name: str) -> str:
    return run("azd", "env", "get-value", name)


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            content = response.read()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc


def chunked(items: Iterable[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def repeated_passage(seed: str, detail: str) -> str:
    paragraph = (
        f"{seed} This is synthetic Contoso Trials data, not real patient or "
        f"proprietary data. {detail} The quarterly review records aggregate "
        "study-level evidence only. Reviewers should interpret the passage in "
        "the context of the cited drug, study, quarter, and section. The source "
        "pattern represents a pre-built clinical summary generated from governed "
        "row-level inputs during the quarterly publish, rather than generation "
        "over the full warehouse at question time. "
    )
    return (paragraph * 9).strip()


def study_pairs() -> list[tuple[str, str, str]]:
    studies = [("STD-1044", "Axumab"), ("STD-2201", "Belvex"), ("STD-3301", "Coryl")]
    studies.extend((f"STD-{3000 + index}", DRUGS[(index + 3) % len(DRUGS)]) for index in range(197))
    return [
        (study_id, primary, DRUGS[(DRUGS.index(primary) + 11) % len(DRUGS)])
        for study_id, primary in studies
    ]


def canary_detail(drug: str, study_id: str, doc_type: str) -> str:
    if drug == "Axumab" and study_id == "STD-1044" and doc_type == "safety":
        return (
            "DRUG-CANARY-AXIMAB. The serious infection rate is 1.8 percent. "
            "Section 6.2 requires treatment hold for suspected serious infection, "
            "fever with hemodynamic instability, or pending culture confirmation."
        )
    if drug == "Belvex" and study_id == "STD-2201" and doc_type == "efficacy":
        return (
            "DRUG-CANARY-BELVEX. The primary endpoint was met with a hazard "
            "ratio of 0.74 in the synthetic efficacy review."
        )
    if drug == "Coryl" and study_id == "STD-3301" and doc_type == "eligibility":
        return (
            "DRUG-CANARY-CORYL. Screening requires eGFR of at least 45 and "
            "excludes prior biologic use within 90 days."
        )
    return (
        f"Synthetic aggregate review for {drug} in {study_id}; no real patient "
        "records are represented."
    )


def document_set() -> Iterator[dict[str, Any]]:
    sections = [
        ("summary", "Drug-study summary"),
        ("summary", "Protocol excerpt"),
        ("safety", "Safety review"),
        ("efficacy", "Efficacy table note"),
        ("eligibility", "Eligibility rule"),
    ]
    for study_index, (study_id, primary, secondary) in enumerate(study_pairs()):
        phase = f"Phase {(study_index % 3) + 1}"
        for quarter in QUARTERS:
            for drug in (primary, secondary):
                parent_id = f"{drug}-{study_id}-{quarter}".lower()
                for section_index, (doc_type, section) in enumerate(sections):
                    is_parent = section_index == 0
                    detail = canary_detail(drug, study_id, doc_type)
                    content = (
                        f"{drug} {study_id} {quarter} synthetic Contoso Trials "
                        f"{section.lower()}. {detail}"
                        if is_parent
                        else repeated_passage(
                            f"{drug} {study_id} {quarter} {section}.", detail
                        )
                    )
                    yield {
                        "id": parent_id if is_parent else f"{parent_id}-{doc_type}-{section_index}",
                        "parent_id": parent_id,
                        "drug_name": drug,
                        "study_id": study_id,
                        "phase": phase,
                        "quarter": quarter,
                        "doc_type": doc_type,
                        "title": f"{drug} {study_id} {quarter}",
                        "section": section,
                        "content": content,
                        "sponsor_name": "Contoso Trials",
                        "summary_boost": 5 if is_parent else 1,
                        "source_url": f"https://contoso.example/trials/{study_id}/{quarter}/{section_index}",
                    }


def q2_documents() -> list[dict[str, Any]]:
    parent_id = "axumab-std-1044-2026q2"
    details = {
        "summary": (
            "DRUG-CANARY-AXIMAB-Q2. The synthetic 2026Q2 safety publish changed "
            "the serious infection rate from 1.8 percent to 1.5 percent. Section "
            "6.2 hold rules remain in effect."
        ),
        "safety": (
            "DRUG-CANARY-AXIMAB-Q2. The serious infection rate is 1.5 percent, "
            "changed from 1.8 percent in the prior review. Section 6.2 requires "
            "treatment hold for suspected serious infection, fever with "
            "hemodynamic instability, or pending culture confirmation."
        ),
        "efficacy": "DRUG-CANARY-AXIMAB-Q2. No material efficacy conclusion changed.",
        "eligibility": "DRUG-CANARY-AXIMAB-Q2. Eligibility rules did not change.",
    }
    sections = [
        ("summary", "Drug-study summary"),
        ("summary", "Protocol excerpt"),
        ("safety", "Safety review"),
        ("efficacy", "Efficacy table note"),
        ("eligibility", "Eligibility rule"),
    ]
    documents = []
    for index, (doc_type, section) in enumerate(sections):
        is_parent = index == 0
        detail = details[doc_type]
        documents.append(
            {
                "id": parent_id if is_parent else f"{parent_id}-{doc_type}-{index}",
                "parent_id": parent_id,
                "drug_name": "Axumab",
                "study_id": "STD-1044",
                "phase": "Phase 1",
                "quarter": "2026Q2",
                "doc_type": doc_type,
                "title": "Axumab STD-1044 2026Q2",
                "section": section,
                "content": detail if is_parent else repeated_passage(section, detail),
                "sponsor_name": "Contoso Trials",
                "summary_boost": 5 if is_parent else 1,
                "source_url": f"https://contoso.example/trials/STD-1044/2026Q2/{index}",
            }
        )
    return documents


def index_schema() -> dict[str, Any]:
    string = "Edm.String"
    return {
        "name": INDEX_NAME,
        "fields": [
            {"name": "id", "type": string, "key": True, "filterable": True},
            {"name": "parent_id", "type": string, "filterable": True},
            {
                "name": "drug_name",
                "type": string,
                "searchable": True,
                "filterable": True,
                "facetable": True,
            },
            {"name": "study_id", "type": string, "searchable": True, "filterable": True},
            {"name": "phase", "type": string, "filterable": True},
            {
                "name": "quarter",
                "type": string,
                "searchable": True,
                "filterable": True,
                "sortable": True,
            },
            {"name": "doc_type", "type": string, "filterable": True, "facetable": True},
            {"name": "title", "type": string, "searchable": True},
            {"name": "section", "type": string, "searchable": True},
            {"name": "content", "type": string, "searchable": True},
            {"name": "sponsor_name", "type": string, "filterable": True},
            {"name": "summary_boost", "type": "Edm.Int32", "filterable": True},
            {"name": "source_url", "type": string, "retrievable": True},
        ],
        "semantic": {
            "configurations": [
                {
                    "name": "contoso-trials-semantic",
                    "prioritizedFields": {
                        "titleField": {"fieldName": "title"},
                        "prioritizedContentFields": [
                            {"fieldName": "section"},
                            {"fieldName": "content"},
                        ],
                        "prioritizedKeywordsFields": [
                            {"fieldName": "drug_name"},
                            {"fieldName": "study_id"},
                            {"fieldName": "quarter"},
                        ],
                    },
                }
            ]
        },
        "scoringProfiles": [
            {
                "name": "summary-first",
                "text": {"weights": {"title": 3, "section": 2, "content": 1}},
                "functions": [
                    {
                        "type": "magnitude",
                        "fieldName": "summary_boost",
                        "boost": 3,
                        "interpolation": "linear",
                        "magnitude": {
                            "boostingRangeStart": 1,
                            "boostingRangeEnd": 5,
                            "constantBoostBeyondRange": True,
                        },
                    }
                ],
                "functionAggregation": "sum",
            }
        ],
        "defaultScoringProfile": "summary-first",
    }


def main() -> int:
    resource_group = azd_value("AZURE_RESOURCE_GROUP_NAME")
    search_name = azd_value("AZURE_SEARCH_SERVICE_NAME")
    storage_name = azd_value("AZURE_STORAGE_ACCOUNT_NAME")
    search_key = json.loads(
        run(
            "az",
            "search",
            "admin-key",
            "show",
            "--resource-group",
            resource_group,
            "--service-name",
            search_name,
            "--output",
            "json",
        )
    )["primaryKey"]
    storage_key = json.loads(
        run(
            "az",
            "storage",
            "account",
            "keys",
            "list",
            "--resource-group",
            resource_group,
            "--account-name",
            storage_name,
            "--output",
            "json",
        )
    )[0]["value"]

    endpoint = f"https://{search_name}.search.windows.net"
    api_version = "2024-07-01"
    headers = {"Content-Type": "application/json", "api-key": search_key}
    request_json(
        "PUT",
        f"{endpoint}/indexes/{INDEX_NAME}?api-version={api_version}",
        headers=headers,
        body=index_schema(),
    )

    uploaded = 0
    for batch in chunked(document_set(), 100):
        actions = [{"@search.action": "mergeOrUpload", **document} for document in batch]
        response = request_json(
            "POST",
            f"{endpoint}/indexes/{INDEX_NAME}/docs/index?api-version={api_version}",
            headers=headers,
            body={"value": actions},
        )
        failed = [item for item in response.get("value", []) if not item.get("status")]
        if failed:
            raise RuntimeError(f"Search upload failed for {len(failed)} document(s)")
        uploaded += len(batch)
        if uploaded % 1000 == 0:
            print(f"Uploaded {uploaded} synthetic Contoso Trials documents")

    q2_payload = json.dumps(
        {
            "sponsor_name": "Contoso Trials",
            "classification": "synthetic Contoso Trials data",
            "documents": q2_documents(),
        }
    )
    storage_env = os.environ.copy()
    storage_env["AZURE_STORAGE_KEY"] = storage_key
    subprocess.run(
        [
            "az",
            "storage",
            "blob",
            "upload",
            "--account-name",
            storage_name,
            "--container-name",
            "trial-drops",
            "--name",
            "2026Q2/axumab-STD-1044.json",
            "--overwrite",
            "true",
            "--data",
            q2_payload,
            "--output",
            "none",
        ],
        check=True,
        env=storage_env,
    )

    count = request_json(
        "GET",
        f"{endpoint}/indexes/{INDEX_NAME}/docs/$count?api-version={api_version}",
        headers=headers,
    )
    print(
        json.dumps(
            {
                "index": INDEX_NAME,
                "document_count": int(count),
                "parents": 2000,
                "chunks": 8000,
                "q2_blob": "2026Q2/axumab-STD-1044.json",
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
