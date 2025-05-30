# apps/store/views.py

from django.shortcuts import render, get_object_or_404
from apps.inventory.models import Product,Category # Import Product from inventory
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages # Import messages for user feedback
from apps.inventory.models import Product
from .models import Cart, CartItem, ProductVariant
from django.contrib.auth.decorators import login_required
from django.db import transaction # For atomic operations

def product_list_view(request):
    """
    Displays a list of all active products.
    """
    # Only display products that are not soft-deleted
    products = Product.objects.filter(is_active=True, is_deleted=False).order_by('name')
    categories = Category.objects.filter(is_active=True).order_by('name')
    context = {
        'products': products,
        'categories': categories,
        'page_title': 'All Products',
    }
    return render(request, 'store/store_view.html', context)

def product_detail_view(request, slug):
    """
    Displays the detailed view of a single product.
    """
    # Only retrieve products that are not soft-deleted
    product = get_object_or_404(Product, slug=slug, is_active=True, is_deleted=False)
    context = {
        'product': product,
        'page_title': product.name,
    }
    return render(request, 'store/store_detail_view.html', context)

def category_product_list_view(request, slug):
    """
    Displays products belonging to a specific category.
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)
    # Ensure you use the correct related_name if you changed it in Product model
    products = category.inventory_products.filter(is_active=True, is_deleted=False).order_by('name') 
    categories = Category.objects.filter(is_active=True).order_by('name')
    context = {
        'category': category,
        'products': products,
        'categories': categories,
        'page_title': f'Products in {category.name}',
    }
    return render(request, 'store/store_view.html', context)

# ... (Your existing product_list_view, product_detail_view, category_product_list_view) ...

def get_or_create_cart(request):
    """
    Helper function to get the user's cart or create a new one.
    Handles both authenticated and anonymous users.
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        # If an anonymous cart exists with this session, merge it
        if request.session.session_key:
            try:
                anon_cart = Cart.objects.get(session_key=request.session.session_key, user__isnull=True)
                if anon_cart != cart: # Avoid merging cart with itself
                    for item in anon_cart.items.all():
                        existing_item = cart.items.filter(product_variant=item.product_variant).first()
                        if existing_item:
                            existing_item.quantity += item.quantity
                            existing_item.save()
                        else:
                            item.cart = cart
                            item.save()
                    anon_cart.delete() # Delete the old anonymous cart
                del request.session['session_key'] # Clear the session key after merging
            except Cart.DoesNotExist:
                pass # No anonymous cart to merge
    else:
        # For anonymous users, use session_key
        if not request.session.session_key:
            request.session.save() # Ensure a session key exists
        cart, created = Cart.objects.get_or_create(session_key=request.session.session_key, user__isnull=True)
    return cart


@transaction.atomic
def add_to_cart_view(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
        quantity = int(request.POST.get('quantity', 1))

        if quantity <= 0:
            messages.error(request, "Quantity must be at least 1.")
            return redirect(request.META.get('HTTP_REFERER', 'store:product_list'))

        if product.stock_quantity < quantity:
            messages.error(request, f"Not enough stock for {product.name}. Available: {product.stock_quantity}.")
            return redirect(request.META.get('HTTP_REFERER', 'store:product_list')) # Use product_list or store_view consistently

        try:
            # Try to get an existing variant for the product (e.g., if there's only one, or a "default" one)
            product_variant = ProductVariant.objects.get(product=product)
        except ProductVariant.DoesNotExist:
            # If no variant exists, create a basic one for the product
            # Now, 'price' is a real field, so you can assign to it.
            product_variant = ProductVariant.objects.create(
                product=product,
                sku=f"{product.product_id}-DEF",
                price=product.price # Assign to the actual price field
            )
            messages.warning(request, f"Default variant created for {product.name}.")
        except ProductVariant.MultipleObjectsReturned:
            # If multiple variants exist and none is explicitly selected, pick the first active one
            product_variant = ProductVariant.objects.filter(product=product, is_active=True).first()
            if not product_variant:
                messages.error(request, f"No active variant found for {product.name}.")
                return redirect(request.META.get('HTTP_REFERER', 'store:product_list'))

        cart = get_or_create_cart(request)

        try:
            cart_item = CartItem.objects.get(cart=cart, product_variant=product_variant)
            cart_item.quantity += quantity
            cart_item.save()
            messages.success(request, f"Added {quantity} more of {product.name} to your cart.")
        except CartItem.DoesNotExist:
            CartItem.objects.create(cart=cart, product_variant=product_variant, quantity=quantity)
            messages.success(request, f"Added {quantity} {product.name} to your cart.")

        return redirect(request.META.get('HTTP_REFERER', 'store:product_list')) # Use product_list or store_view consistently
    
    messages.error(request, "Invalid request to add item to cart.")
    return redirect('store:product_list') # Use product_list or store_view consistently


def cart_view(request):
    cart = get_or_create_cart(request)
    # Calculate cart total
    cart_total = sum(item.item_total for item in cart.items.all())
    
    context = {
        'cart': cart,
        'cart_total': cart_total,
        'page_title': 'Your Shopping Cart',
    }
    return render(request, 'store/cart.html', context)
@transaction.atomic
def update_cart_item_view(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id)
        # Ensure the item belongs to the current user's/session's cart
        cart = get_or_create_cart(request)
        if cart_item.cart != cart:
            messages.error(request, "Access denied: This cart item does not belong to your cart.")
            return redirect('store:cart_view')

        try:
            new_quantity = int(request.POST.get('quantity', 0))
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect('store:cart_view')

        if new_quantity <= 0:
            # If quantity is 0 or less, remove the item
            cart_item.delete()
            messages.success(request, f"'{cart_item.product_variant.product.name}' removed from cart.")
        else:
            # Check product stock before updating
            product = cart_item.product_variant.product
            if new_quantity > product.stock_quantity:
                messages.error(request, f"Cannot update. Not enough stock for {product.name}. Available: {product.stock_quantity}.")
                return redirect('store:cart_view')

            cart_item.quantity = new_quantity
            cart_item.save()
            messages.success(request, f"Quantity of '{product.name}' updated to {new_quantity}.")
    
    return redirect('store:cart_view')


# NEW: Remove from Cart View
@transaction.atomic
def remove_from_cart_view(request, item_id):
    if request.method == 'POST': # Use POST for destructive actions
        cart_item = get_object_or_404(CartItem, id=item_id)
        # Ensure the item belongs to the current user's/session's cart
        cart = get_or_create_cart(request)
        if cart_item.cart != cart:
            messages.error(request, "Access denied: This cart item does not belong to your cart.")
            return redirect('store:cart_view')

        product_name = cart_item.product_variant.product.name
        cart_item.delete()
        messages.success(request, f"'{product_name}' has been removed from your cart.")
    return redirect('store:cart_view')

