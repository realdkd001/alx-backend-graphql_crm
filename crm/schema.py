import graphene
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from django.utils import timezone
import django_filters
from graphene_django.filter import DjangoFilterConnectionField

from .models import Customer, Product, Order

# -----------------------------
# GraphQL Types
# -----------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = "__all__"
        filter_fields = {"name": ["icontains", "istartswith"], "email": ["icontains"], "phone": ["icontains"]}
        interfaces = (graphene.relay.Node,)


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = "__all__"
        filter_fields = {"name": ["icontains"], "price": ["gte", "lte"]}
        interfaces = (graphene.relay.Node,)


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = "__all__"
        filter_fields = {"order_date": ["gte", "lte"], "total_amount": ["gte", "lte"]}
        interfaces = (graphene.relay.Node,)


# -----------------------------
# Input Types
# -----------------------------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=True)


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False, default_value=0)


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True, name="customerId")
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True, name="productIds")
    order_date = graphene.DateTime(required=False, name="orderDate")


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
        if Customer.objects.filter(email=input.email).exists():
            raise GraphQLError("Customer with this email already exists.")

        try:
            validate_email(input.email)
        except ValidationError:
            raise GraphQLError("Invalid email format.")

        if not input.phone.startswith("+233") or len(input.phone) < 10:
            raise GraphQLError("Phone number must start with +233 and be valid.")

        customer = Customer.objects.create(
            name=input.name,
            email=input.email,
            phone=input.phone
        )
        return CreateCustomer(customer=customer, message="Customer created successfully.")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        inputs = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, inputs):
        customers = []
        errors = []

        with transaction.atomic():
            for i, input in enumerate(inputs):
                sid = transaction.savepoint()
                try:
                    if Customer.objects.filter(email=input.email).exists():
                        raise GraphQLError(f"Duplicate email: {input.email}")

                    validate_email(input.email)

                    if not input.phone.startswith("+233") or len(input.phone) < 10:
                        raise GraphQLError("Phone number must start with +233 and be valid.")

                    customer = Customer.objects.create(
                        name=input.name,
                        email=input.email,
                        phone=input.phone
                    )
                    customers.append(customer)
                except Exception as e:
                    errors.append(f"Row {i+1}: {str(e)}")
                    transaction.savepoint_rollback(sid)
                else:
                    transaction.savepoint_commit(sid)

        return BulkCreateCustomers(
            customers=customers,
            errors=errors,
            message="Bulk customer insert completed."
        )


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input: ProductInput):
        try:
            price = Decimal(str(input.price))
        except (InvalidOperation, TypeError):
            raise GraphQLError("Price must be a valid decimal.")

        if price <= 0:
            raise GraphQLError("Price must be positive.")

        stock = input.stock if input.stock is not None else 0
        if stock < 0:
            raise GraphQLError("Stock cannot be negative.")

        product = Product.objects.create(
            name=input.name,
            price=price.quantize(Decimal("0.01")),
            stock=stock,
        )
        return CreateProduct(product=product, message="Product created successfully.")


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input: OrderInput):
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            raise GraphQLError("Customer does not exist.")

        products = Product.objects.filter(id__in=input.product_ids)
        if products.count() != len(input.product_ids):
            missing_ids = set(input.product_ids) - set(str(p.id) for p in products)
            raise GraphQLError(f"Invalid product IDs: {', '.join(missing_ids)}")

        order = Order.objects.create(
            customer=customer,
            total_amount=Decimal("0.00"),
            order_date=input.order_date or timezone.now()
        )
        order.products.set(products)

        total = sum([p.price for p in products])
        order.total_amount = total.quantize(Decimal("0.01"))
        order.save()

        return CreateOrder(order=order, message="Order created successfully.")


# -----------------------------
# Root Schema
# -----------------------------
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


class Query(graphene.ObjectType):
    customer = graphene.relay.Node.Field(CustomerType)
    all_customers = DjangoFilterConnectionField(CustomerType, order_by=graphene.List(of_type=graphene.String))

    product = graphene.relay.Node.Field(ProductType)
    all_products = DjangoFilterConnectionField(ProductType, order_by=graphene.List(of_type=graphene.String))

    order = graphene.relay.Node.Field(OrderType)
    all_orders = DjangoFilterConnectionField(OrderType, order_by=graphene.List(of_type=graphene.String))

    def resolve_all_customers(root, info, order_by=None, **kwargs):
        qs = Customer.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_products(root, info, order_by=None, **kwargs):
        qs = Product.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_orders(root, info, order_by=None, **kwargs):
        qs = Order.objects.all()
        if order_by:
            qs = qs.order_by(*order_by)
        return qs


schema = graphene.Schema(query=Query, mutation=Mutation)
