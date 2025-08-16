import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product

# Add some initial data
Customer.objects.create(name="John Doe", email="john@example.com", phone="+1234567890")
Product.objects.create(name="Phone", price=499.99, stock=5)
Product.objects.create(name="Tablet", price=299.99, stock=8)
print("Database seeded!")
