from .models import Cart

def cart_item_count(request):
    cart = None
    item_count = 0

    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()

        if cart:
            item_count = cart.items.count()  # Count unique items (not total quantity)

    except Exception as e:
        # Optional: log this if needed for debugging
        print("Context processor error:", e)

    return {'cart_item_count': item_count}
