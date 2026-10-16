import asyncio
from typing import Any

from fieldservice_search.work_order_search import SearchRequest, WorkOrder, WorkOrderSearch


class RecordingBackend:
    def __init__(self) -> None:
        self.embedded_texts: list[str] = []
        self.upserted: list[dict[str, Any]] = []

    async def embed(self, text: str, model: str) -> list[float]:
        self.embedded_texts.append(text)
        return [0.2, 0.8]

    async def upsert(
        self, collection: str, vectors: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.upserted = vectors
        return {}

    async def query(
        self, collection: str, embedding: list[float], top_k: int
    ) -> dict[str, Any]:
        return {
            "matches": [
                {
                    "score": 0.94,
                    "metadata": {
                        "work_order_id": "WO-1042",
                        "photo_description": "Frost around freezer door seal",
                        "dispatch_status": "technician on site",
                        "technician_follow_up": "Replace gasket",
                    },
                }
            ]
        }


def test_search_returns_the_work_order_whose_follow_up_matches_the_intent() -> None:
    backend = RecordingBackend()
    search = WorkOrderSearch(backend, "orders", "embedding-model")

    hits = asyncio.run(search.search(SearchRequest(query="freezer gasket repair")))

    assert hits[0].work_order_id == "WO-1042"
    assert hits[0].technician_follow_up == "Replace gasket"
    assert backend.embedded_texts == ["freezer gasket repair"]


def test_index_combines_photo_dispatch_and_follow_up_into_the_embedding() -> None:
    backend = RecordingBackend()
    search = WorkOrderSearch(backend, "orders", "embedding-model")
    order = WorkOrder(
        work_order_id="WO-7",
        photo_description="Cracked checkout display",
        dispatch_status="assigned",
        technician_follow_up="Bring replacement panel",
    )

    asyncio.run(search.index(order))

    assert backend.embedded_texts == [
        "Photo: Cracked checkout display\n"
        "Dispatch: assigned\n"
        "Technician follow-up: Bring replacement panel"
    ]
    assert backend.upserted[0]["id"] == "WO-7"

