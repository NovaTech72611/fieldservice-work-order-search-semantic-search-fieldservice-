from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .infrai_client import InfraiClient, InfraiError
from .work_order_search import SearchHit, SearchRequest, WorkOrder, WorkOrderSearch


def build_search(client: InfraiClient) -> WorkOrderSearch:
    return WorkOrderSearch(
        backend=client,
        collection=os.environ.get("INFRAI_COLLECTION", "fieldservice-work-orders"),
        embedding_model=os.environ.get("INFRAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    api_key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(api_key)
    app.state.infrai_client = client
    app.state.work_orders = build_search(client)
    yield
    await client.close()


app = FastAPI(title="Field-service work-order search", lifespan=lifespan)


@app.exception_handler(InfraiError)
async def infrai_error_handler(_: Request, exc: InfraiError) -> JSONResponse:
    status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": exc.code, "message": str(exc)}},
    )


@app.post("/work-orders", status_code=204)
async def index_work_order(order: WorkOrder, request: Request) -> None:
    await request.app.state.work_orders.index(order)


@app.post("/search", response_model=list[SearchHit])
async def search_work_orders(
    search: SearchRequest, request: Request
) -> list[SearchHit]:
    return await request.app.state.work_orders.search(search)
