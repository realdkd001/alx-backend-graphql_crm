import re
from decimal import Decimal
import graphene
from graphene_django import DjangoObjectType
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from graphql import GraphQLError

from .models import Customer, Product, Order

# -----------------------------
# GraphQL Types
# -----------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# -----------------------------
# Input Types (Relay-style)
# -----------------------------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False, default_value=0)


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
    order_date = graphene.DateTime(required=False)


# -----------------------------
# Mutations
# -----------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input: CustomerInput):
        # Validate email uniqueness
        if Customer.objects.filter(email=input.email).exists():
            raise GraphQLError("Email already exists.")

        # Validate phone (if provided)
        if input.phone and not re.match(r"^(\+?\d{7,15}|(\d{3}-\d{3}-\d{4}))$", input.phone):
            raise GraphQLError("Invalid phone format. Use +1234567890 or 123-456-7890.")

        customer = Customer.objects.create(
            name=input.name,
            email=input.email,
            phone=input.phone or None,
        )
        return CreateCustomer(customer=customer, message="Customer created successfully.")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(graphene.NonNull(CustomerInput), required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @staticmethod
    @transaction.atomic
    def mutate(root, info, input):
        """
        - Runs inside a single request.
        - Uses per-item savepoints to allow partial success while keeping the request atomic.
        """
        created_customers = []
        errors = []

        for idx, c in enumerate(input):
            sp = transaction.savepoint()
            try:
                if Customer.objects.filter(email=c.email).exists():
                    raise ValidationError(f"Email already exists: {c.email}")

                if c.phone and not re.match(r"^(\+?\d{7,15}|(\d{3}-\d{3}-\d{4}))$", c.phone):
                    raise ValidationError(
                        f"Invalid phone format for {c.email}. Use +1234567890 or 123-456-7890."
                    )

                customer = Customer.objects.create(
                    name=c.name,
                    email=c.email,
                    phone=c.phone or None,
                )
                created_customers.append(customer)
                transaction.savepoint_commit(sp)
            except Exception as e:
                # rollback only this item
                transaction.savepoint_rollback(sp)
                errors.append(f"Row {idx+1}: {str(e)}")

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    @staticmethod
    def mutate(root, info, input: ProductInput):
        # Validate price
        try:
            price = Decimal(str(input.price))
        except Exception:
            raise GraphQLError("Price must be a valid decimal.")

        if price <= Decimal("0"):
            raise GraphQLError("Price must be positive.")

        # Validate stock
        stock = input.stock if input.stock is not None else 0
        if stock < 0:
            raise GraphQLError("Stock cannot be negative.")

        product = Product.objects.create(
            name=input.name,
            price=price.quantize(Decimal("0.01")),
            stock=stock,
        )
        return CreateProduct(product=product)


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)

    @staticmethod
    @transaction.atomic
    def mutate(root, info, input: OrderInput):
        # Validate customer
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            raise GraphQLError("Invalid customer ID.")

        # Validate product IDs
        if not input.product_ids:
            raise GraphQLError("At least one product must be selected.")

        products = list(Product.objects.filter(pk__in=input.product_ids))
        if not products:
            raise GraphQLError("No valid product IDs provided.")

        # Detect invalid IDs (user-friendly message)
        found_ids = {str(p.pk) for p in products}
        requested_ids = {str(pid) for pid in input.product_ids}
        missing = requested_ids - found_ids
        if missing:
            raise GraphQLError(f"Invalid product ID(s): {', '.join(sorted(missing))}")

        order_date = input.order_date or timezone.now()

        # Create order, associate products, compute total using Decimal
        order = Order.objects.create(customer=customer, order_date=order_date)
        order.products.set(products)

        # Accurate Decimal sum
        total = Decimal("0.00")
        for p in products:
            total += p.price
        order.total_amount = total.quantize(Decimal("0.01"))
        order.save(update_fields=["total_amount"])

        return CreateOrder(order=order)


# -----------------------------
# Query (simple list endpoints)
# -----------------------------
class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(self, info):
        return Customer.objects.all()

    def resolve_products(self, info):
        return Product.objects.all()

    def resolve_orders(self, info):
        return Order.objects.all()


# -----------------------------
# Root Mutation
# -----------------------------
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
