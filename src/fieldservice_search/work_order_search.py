from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkOrder(BaseModel):
    work_order_id: str = Field(min_length=1)
    photo_description: str = Field(min_length=1)
    dispatch_status: str = Field(min_length=1)
    technician_follow_up: str = ""


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    top_k: int = Field(default=3, ge=1, le=20)


class SearchHit(BaseModel):
    work_order_id: str
    score: float
    photo_description: str
    dispatch_status: str
    technician_follow_up: str


class WorkOrderSearch:
    def __init__(
        self,
        backend: Any,
        collection: str,
        embedding_model: str,
    ) -> None:
        self.backend = backend
        self.collection = collection
        self.embedding_model = embedding_model

    @staticmethod
    def searchable_text(order: WorkOrder) -> str:
        return "\n".join(
            (
                f"Photo: {order.photo_description}",
                f"Dispatch: {order.dispatch_status}",
                f"Technician follow-up: {order.technician_follow_up or 'none recorded'}",
            )
        )

    async def index(self, order: WorkOrder) -> None:
        embedding = await self.backend.embed(
            self.searchable_text(order), self.embedding_model
        )
        await self.backend.upsert(
            self.collection,
            [
                {
                    "id": order.work_order_id,
                    "values": embedding,
                    "metadata": order.model_dump(),
                }
            ],
        )

    async def search(self, request: SearchRequest) -> list[SearchHit]:
        embedding = await self.backend.embed(request.query, self.embedding_model)
        result = await self.backend.query(self.collection, embedding, request.top_k)
        matches = result.get("matches", [])
        return [
            SearchHit(score=float(match["score"]), **match["metadata"])
            for match in matches
        ]
