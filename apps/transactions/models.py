from django.db import models
from django.utils import timezone
import datetime

# Assuming your User model is in the same file or can be imported easily# If Order model is in another app, import it like:

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('user_registration', 'User Registered'),
        ('supplier_approval', 'Supplier Approved'),
        ('order_placed', 'Order Placed'),
        ('order_status_change', 'Order Status Changed'),
        ('payment_received', 'Payment Received'),
        ('delivery_completed', 'Delivery Completed'),
        # Add more basic types as your system evolves
    ]

    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='transactions', 
                             help_text="The user primarily associated with this transaction.")
    
    # Optional: If you have an Order model, uncomment and adjust the import.
    # This links transactions directly to specific orders.
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions',
                              help_text="The order related to this transaction, if any.")

    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES, 
                                        help_text="Type of action or event recorded.")
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                 help_text="Amount involved in the transaction (e.g., payment, order total).")
    timestamp = models.DateTimeField(auto_now_add=True, 
                                     help_text="Date and time when the transaction occurred.")
    description = models.TextField(blank=True, 
                                   help_text="A brief explanation or context for the transaction.")
    
    class Meta:
        ordering = ['-timestamp'] # Most recent transactions first
        verbose_name = "Transaction History"
        verbose_name_plural = "Transaction Histories"

    def __str__(self):
        amount_str = f"₱{self.amount:,.2f}" if self.amount is not None else ""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.get_transaction_type_display()} by {self.user.username if self.user else 'N/A'} {amount_str}"