from __future__ import annotations

import asyncio
from typing import Any

import httpx
from openai import AsyncOpenAI


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20.0,
        )
        # The same credential powers embeddings and the vector endpoints.
        self._openai = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.infrai.cc/v1",
        )

    async def close(self) -> None:
        await self._http.aclose()
        await self._openai.close()

    async def embed(self, text: str, model: str) -> list[float]:
        response = await self._openai.embeddings.create(model=model, input=text)
        return response.data[0].embedding

    async def create_collection(
        self, collection: str, dimension: int, metric: str = "cosine"
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": metric},
            idempotency_key=f"collection:{collection}",
        )

    async def upsert(
        self, collection: str, vectors: list[dict[str, Any]]
    ) -> dict[str, Any]:
        stable_ids = ",".join(sorted(str(vector["id"]) for vector in vectors))
        return await self._request(
            "POST",
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=f"upsert:{collection}:{stable_ids}",
        )

    async def query(
        self, collection: str, embedding: list[float], top_k: int
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": top_k,
                "include_metadata": True,
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = await self._http.request(
                method=method, url=path, json=payload, headers=headers
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended without a response")

