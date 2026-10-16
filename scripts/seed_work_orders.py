import asyncio
import os

from fieldservice_search.infrai_client import InfraiClient
from fieldservice_search.service import build_search
from fieldservice_search.work_order_search import WorkOrder


ORDERS = [
    WorkOrder(
        work_order_id="WO-1042",
        photo_description="Walk-in freezer display shows frost around the upper door seal",
        dispatch_status="technician on site",
        technician_follow_up="Replace torn gasket and verify cabinet temperature",
    ),
    WorkOrder(
        work_order_id="WO-1088",
        photo_description="Checkout lane receipt printer has a red paper warning light",
        dispatch_status="scheduled for tomorrow",
        technician_follow_up="Bring an 80 mm paper roll and inspect the feed sensor",
    ),
]


async def main() -> None:
    client = InfraiClient(os.environ["INFRAI_API_KEY"])
    search = build_search(client)
    try:
        first_vector = await client.embed(
            search.searchable_text(ORDERS[0]), search.embedding_model
        )
        await client.create_collection(search.collection, len(first_vector))
        await client.upsert(
            search.collection,
            [
                {
                    "id": ORDERS[0].work_order_id,
                    "values": first_vector,
                    "metadata": ORDERS[0].model_dump(),
                }
            ],
        )
        await search.index(ORDERS[1])
        print(f"Indexed {len(ORDERS)} work orders into {search.collection}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

