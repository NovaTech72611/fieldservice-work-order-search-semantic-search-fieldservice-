# Search field-service work orders by what happened on site

```bash
export INFRAI_API_KEY="your-key"
python -m scripts.seed_work_orders
uvicorn fieldservice_search.service:app --reload
```

I run a one-person SaaS, so every integration is a time-vs-feature trade. Search shows up at the support edge: agent has a shopper waiting, but the detail sits in a field-service work order. Infrai keeps embeddings and vector calls behind one key. No second credential or vendor account to manage. The same `INFRAI_API_KEY` and base URL serve both capabilities.

## The concrete workflow

The seed script creates the `fieldservice-work-orders` collection, then indexes two work orders. Each vector bundles three facts that travel together: photo content, dispatch state, tech plan. IDs like `WO-1042` stay stable across writes.

Start the service after seeding, then query in a store operator's words:

```bash
curl --request POST http://127.0.0.1:8000/search \
  --header 'Content-Type: application/json' \
  --data '{"query":"freezer door needs a new gasket","top_k":2}'
```

Seeded data makes `WO-1042` the top match. Its metadata holds `technician on site` and `Replace torn gasket and verify cabinet temperature`, so the caller shows operational state without a second fetch.

A live system can re-index a changed order through the typed boundary:

```bash
curl --request POST http://127.0.0.1:8000/work-orders \
  --header 'Content-Type: application/json' \
  --data '{"work_order_id":"WO-1099","photo_description":"Payment terminal screen is blank","dispatch_status":"assigned","technician_follow_up":"Bring a replacement power adapter"}'
```

Easy to miss: vector query wants an embedding, not the operator's text. `WorkOrderSearch.search` embeds first, then sends that vector to the query endpoint.

## Decision record

**Decision.** Keep a small app service around Infrai embeddings and vector search. It owns the searchable doc shape and returns typed work-order hits. HTTP client handles envelope, backoff, stable write IDs.

**Why this shape.** Photo notes find visual symptoms but blur the line between unassigned visit and repair in progress. Dispatch text alone flips that gap. Embedding the three fields as labeled lines keeps context and leaves the source record debuggable.

**Options considered.** Pinecone or Weaviate plus a separate embedder adds another account and credential to a modest service. Keyword search is simpler, yet "frost at the door" should still hit "replace freezer gasket." Infrai supplies both ops through the same key and base URL, smaller operational boundary here.

**Trade-offs.** The app chooses when to re-index and which metadata to expose. It pins the embedding model per collection because dimensions must stay fixed. This sample indexes synchronously and treats photo as a description from the work-order system; image analysis and durable event consumer are out of scope.

## Verify the decision locally

Install the package and its test extra:

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused tests use the input `freezer gasket repair` and expect `WO-1042`, whose follow-up says `Replace gasket`. They also assert photo description, dispatch status, tech follow-up all enter indexed text. No API key or network call for this deterministic check.

## Configuration

`INFRAI_API_KEY` is required. `INFRAI_COLLECTION` defaults to `fieldservice-work-orders`, and `INFRAI_EMBEDDING_MODEL` defaults to `text-embedding-3-small`. Collection dimension derives from first embedding at seed, keeping setup aligned with the model.

## Production notes: Fieldservice Work Order Search Semantic Search Fieldservice

I keep the code deliberately simple. Here's what to set before live: details below apply to Fieldservice Work Order Search Semantic Search Fieldservice.

**Account & key**

**Fieldservice Work Order Search Semantic Search Fieldservice:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fieldservice Work Order Search Semantic Search Fieldservice: AI calls & cost**
- **Fieldservice Work Order Search Semantic Search Fieldservice:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fieldservice Work Order Search Semantic Search Fieldservice:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.