import csv
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.inventory.models import Product
from apps.orders.models import Order

User = get_user_model()

class Command(BaseCommand):
    help = 'Import orders data from CSV'

    def handle(self, *args, **kwargs):
        self.stdout.write("Running custom import_orders command...")

        with open('dummy_datas/dummy_orders.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                product_name = row.get('product_name')
                quantity = row.get('quantity')
                unit_price = row.get('unit_price')
                order_date_str = row.get('order_date')
                expected_delivery_str = row.get('expected_delivery')
                status = row.get('status')
                customer_username = row.get('customer_username')

                # Validate product exists
                try:
                    product = Product.objects.get(name=product_name)
                except Product.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Product '{product_name}' not found. Skipping order."))
                    continue

                # Parse quantity
                try:
                    quantity = int(quantity)
                except (TypeError, ValueError):
                    quantity = 1  # default to 1 if invalid

                # Parse unit_price
                try:
                    unit_price = Decimal(unit_price)
                except (TypeError, ValueError, InvalidOperation):
                    unit_price = Decimal('0.00')

                # Parse order_date
                try:
                    order_date = datetime.strptime(order_date_str, '%Y-%m-%d %H:%M:%S')
                except (TypeError, ValueError):
                    order_date = timezone.now()

                # Parse expected_delivery
                try:
                    expected_delivery = datetime.strptime(expected_delivery_str, '%Y-%m-%d').date()
                except (TypeError, ValueError):
                    expected_delivery = None

                # Get customer User instance if username provided
                customer = None
                if customer_username:
                    try:
                        customer = User.objects.get(username=customer_username)
                    except User.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"User '{customer_username}' not found. Order will have no customer assigned."))

                # Create new Order (don't specify order_id, it will auto-generate)
                order = Order.objects.create(
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    order_date=order_date,
                    expected_delivery=expected_delivery,
                    status=status if status in ['Pending', 'Completed', 'Canceled'] else 'Pending',
                    customer=customer,
                )
                self.stdout.write(self.style.SUCCESS(f"Created order: {order.order_id}"))
