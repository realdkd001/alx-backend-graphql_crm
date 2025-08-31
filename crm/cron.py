from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = "/tmp/low_stock_updates_log.txt"
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"


def update_low_stock():
    """Executes GraphQL mutation to update low-stock products and logs results."""

    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{timestamp} Low stock update run."

    try:
        # GraphQL client
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            verify=True,
            retries=3,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        # Mutation query
        mutation = gql(
            """
            mutation {
              updateLowStockProducts {
                success
                message
                updatedProducts {
                  id
                  name
                  stock
                }
              }
            }
            """
        )

        result = client.execute(mutation)
        data = result["updateLowStockProducts"]

        if data["success"]:
            for p in data["updatedProducts"]:
                message += f"\n - {p['name']} restocked to {p['stock']}"
            message += f"\n{data['message']}"

    except Exception as e:
        message += f"\n GraphQL mutation failed: {e}"

    # Append log
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")