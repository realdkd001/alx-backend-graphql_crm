from celery import shared_task
from datetime import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import requests


LOG_FILE = "/tmp/crm_report_log.txt"
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"


@shared_task
def generate_crm_report():
    """Generates a weekly CRM report with total customers, orders, revenue."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - Report: "

    try:
        transport = RequestsHTTPTransport(
            url=GRAPHQL_ENDPOINT,
            verify=True,
            retries=3,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        query = gql(
            """
            query {
              customers { id }
              orders { id totalAmount }
            }
            """
        )

        result = client.execute(query)
        customers = result.get("customers", [])
        orders = result.get("orders", [])

        total_customers = len(customers)
        total_orders = len(orders)
        total_revenue = sum([float(order["totalAmount"]) for order in orders])

        message += f"{total_customers} customers, {total_orders} orders, {total_revenue} revenue"

    except Exception as e:
        message += f"Failed to generate report: {e}"

    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")