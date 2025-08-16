from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone

phone_validator = RegexValidator(
    regex=r"^(\+?\d{7,15}|(\d{3}-\d{3}-\d{4}))$",
    message="Invalid phone format. Use +1234567890 or 123-456-7890."
)

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True, validators=[phone_validator])

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} - {self.price}"


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    products = models.ManyToManyField(Product, related_name="orders")
    order_date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"Order #{self.pk} - {self.customer}"

    def recalc_total(self):
        """
        Recalculate total_amount from current products.
        """
        total = Decimal("0.00")
        for p in self.products.all():
            # ensure Decimal math
            total += p.price
        # normalize to 2 dp
        self.total_amount = total.quantize(Decimal("0.01"))
        return self.total_amount
