import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.inventory.models import Product
from apps.suppliers.models import Supplier

class Command(BaseCommand):
    help = 'Import inventory data from CSV'

    def handle(self, *args, **kwargs):
        self.stdout.write("Running custom import_inventory command...")
        with open('dummy_datas/dummy_inventory.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                supplier = None
                supplier_name = row.get('supplier')
                if supplier_name:
                    try:
                        supplier = Supplier.objects.get(name=supplier_name)
                    except Supplier.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Supplier '{supplier_name}' not found. Skipping product '{row.get('name')}'."))
                        continue

                product, created = Product.objects.update_or_create(
                    name=row['name'],
                    defaults={
                        'description': row.get('description', ''),
                        'supplier': supplier,
                        'price': Decimal(row.get('price', '0')),
                        'stock_quantity': int(row.get('stock_quantity', 0)),
                        'reorder_level': int(row.get('reorder_level', 10)),
                        'unit': row.get('unit', ''),
                        'category': row.get('category', ''),
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created product: {product.name}"))
                else:
                    self.stdout.write(f"Updated product: {product.name}")
