
#!/usr/bin/env python3
"""
Script to query pending orders (last 7 days) from GraphQL API
and log reminders with timestamp.
"""

import sys
import asyncio
from datetime import datetime, timedelta
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# GraphQL endpoint
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"

# Log file
LOG_FILE = "/tmp/order_reminders_log.txt"


async def main():
    try:
        # Define transport
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            verify=True,
            retries=3,
        )

        client = Client(transport=transport, fetch_schema_from_transport=True)

        # Calculate cutoff date
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # GraphQL query (adjust field names if different in your schema)
        query = gql(
            """
            query GetRecentOrders($cutoff: Date!) {
              orders(filter: {orderDate_Gte: $cutoff}) {
                id
                customer {
                  email
                }
              }
            }
            """
        )

        variables = {"cutoff": cutoff_date}
        result = await client.execute_async(query, variable_values=variables)

        orders = result.get("orders", [])

        with open(LOG_FILE, "a") as f:
            for order in orders:
                log_line = f"{datetime.now()} - Order ID: {order['id']} - Customer Email: {order['customer']['email']}\n"
                f.write(log_line)

        print("Order reminders processed!")

    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
