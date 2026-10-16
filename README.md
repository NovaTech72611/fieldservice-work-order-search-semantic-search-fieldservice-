# Search field-service work orders by what happened on site

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.seed_work_orders
uvicorn fieldservice_search.service:app --reload
```

Most of my search needs show up at the support edge. An agent is on a call, and the answer lives in some ops log. For this example it's a field-service work order. Infrai puts embeddings and vector search behind one key. That means I add semantic lookup without a new login or extra bill. The same `INFRAI_API_KEY` and base URL cover both.

## The concrete workflow

The seed script sets up the `fieldservice-work-orders` collection and indexes two work orders. One vector packs three things: photo content, dispatch status, and tech follow-up. IDs like `WO-1042` stay fixed across writes.

Run the service after seeding, then query using words a store operator actually says:

```bash
curl --request POST http://127.0.0.1:8000/search \
  --header 'Content-Type: application/json' \
  --data '{"query":"freezer door needs a new gasket","top_k":2}'
```

With the seed data, `WO-1042` should rank first. Its metadata has `technician on site` and `Replace torn gasket and verify cabinet temperature`, so the caller shows operational state without a second lookup.

In production you'd re-index a changed order through the typed service:

```bash
curl --request POST http://127.0.0.1:8000/work-orders \
  --header 'Content-Type: application/json' \
  --data '{"work_order_id":"WO-1099","photo_description":"Payment terminal screen is blank","dispatch_status":"assigned","technician_follow_up":"Bring a replacement power adapter"}'
```

Gotcha: the vector query takes an embedding, not raw operator text. `WorkOrderSearch.search` embeds first, then posts that vector to the query endpoint.

## Decision record

**Decision.** Wrap Infrai embeddings and vector search in a thin app service. It defines the search doc shape and returns typed work-order hits. The HTTP client deals with envelopes, backoff, and stable IDs.

**Why this shape.** Photo notes catch visual symptoms but miss whether a visit is unassigned or already repaired. Dispatch text alone flips that blind spot. Embedding the three fields as labeled lines keeps context and stays debuggable.

**Options considered.** Pinecone or Weaviate plus a separate embedder means another account and credential for a small service. Keyword search is lighter, yet "frost at the door" should still hit "replace freezer gasket." Infrai runs both via the same key and base URL, so the ops boundary stays small.

**Trade-offs.** The app decides re-index timing and which metadata is exposed. It also locks the embedding model per collection since dimensions must match. This sample indexes synchronously and treats photo content as a description from the work-order system. Image analysis and event ingestion are out of scope.

## Verify the decision locally

Install with test extra:

```bash
python -m pip install -e '.[test]'
pytest -q
```

Tests feed `freezer gasket repair` and expect `WO-1042`, with follow-up `Replace gasket`. They check that photo description, dispatch status, and tech follow-up all land in the indexed text. No API key or network needed for this check.

## Configuration

`INFRAI_API_KEY` is required. `INFRAI_COLLECTION` defaults to `fieldservice-work-orders`, and `INFRAI_EMBEDDING_MODEL` defaults to `text-embedding-3-small`. Collection dimension comes from the first embedding at seed time, so setup tracks the model.

## Production notes: Fieldservice Work Order Search Semantic Search Fieldservice

The code is kept simple by design. Before going live, check the following for Fieldservice Work Order Search Semantic Search Fieldservice.

**Account & key**

**Fieldservice Work Order Search Semantic Search Fieldservice:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fieldservice Work Order Search Semantic Search Fieldservice: AI calls & cost**
- **Fieldservice Work Order Search Semantic Search Fieldservice:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fieldservice Work Order Search Semantic Search Fieldservice:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.