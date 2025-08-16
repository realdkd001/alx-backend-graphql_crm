import os
import django
from decimal import Decimal
from django.utils import timezone

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product, Order


def run():
    Order.objects.all().delete()
    Product.objects.all().delete()
    Customer.objects.all().delete()

    customers = [
        Customer(name="Alice Johnson", email="alice@example.com", phone="+233541234567"),
        Customer(name="Bob Smith", email="bob@example.com", phone="+233542345678"),
        Customer(name="Charlie Brown", email="charlie@example.com", phone="+233543456789"),
    ]
    Customer.objects.bulk_create(customers)

    # Create Products
    products = [
        Product(name="Laptop", price=Decimal("999.99"), stock=10),
        Product(name="Smartphone", price=Decimal("499.99"), stock=25),
        Product(name="Headphones", price=Decimal("79.99"), stock=50),
    ]
    Product.objects.bulk_create(products)

    # Create Orders
    alice = Customer.objects.get(email="alice@example.com")
    laptop = Product.objects.get(name="Laptop")
    phone = Product.objects.get(name="Smartphone")

    order1 = Order.objects.create(
        customer=alice,
        total_amount=Decimal("0.00"),
        order_date=timezone.now()
    )
    order1.products.set([laptop, phone])
    order1.total_amount = sum([p.price for p in order1.products.all()])
    order1.save()

    print("✅ Database seeded successfully!")


if __name__ == "__main__":
    run()
