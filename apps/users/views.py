from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.utils.timezone import now
from datetime import timedelta
import random
import json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .forms import CustomUserCreationForm
from .models import User, EmailVerification
from .serializer import UserRegistrationSerializer, UserSerializer
from django.views.decorators.csrf import csrf_exempt


def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_verification_email(email, code):
    send_mail(
        subject="Your Verification Code",
        message=f'Your verification code is: {code}',
        from_email='SupplyTrack <danegela13@gmail.com>',
        recipient_list=[email],
    )

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            tokens = response.data

            access_token = tokens.get("access")
            refresh_token = tokens.get("refresh")

            res = Response({"success": True})

            res.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite=None,
                path="/",
            )

            res.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite=None,
                path="/",
            )

            return res
        except:
            return Response({"success": False}, status=400)

class CustomRefreshTokenView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get('refresh_token')

            if not refresh_token:
                return Response({'refreshed': False}, status=400)

            request.data['refresh'] = refresh_token
            response = super().post(request, *args, **kwargs)

            tokens = response.data
            access_token = tokens.get('access')

            if not access_token:
                return Response({'refreshed': False}, status=400)

            res = Response({'refreshed': True})
            res.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=True,
                samesite=None,
                path='/'
            )
            return res
        except:
            return Response({'refreshed': False}, status=400)

def send_registration_success_email(user):
    send_mail(
        subject="Welcome to SupplyTrack!",
        message=(
            f"Hi {user.username},\n\n"
            "Thank you for registering at SupplyTrack. Your account has been successfully created.\n\n"
            "If you did not create this account, please contact the admin immediately.\n\n"
            "Best regards,\nSupplyTrack Team"
        ),
        from_email='SupplyTrack <danegela13@gmail.com>',
        recipient_list=[user.email],
        fail_silently=False,
    )
    
def send_login_notification_email(user):
    send_mail(
        subject="New Login to Your SupplyTrack Account",
        message=(
            f"Hi {user.username},\n\n"
            "You have just logged into your SupplyTrack account.\n\n"
            "If this wasn't you, please contact the admin immediately.\n\n"
            "Best regards,\nSupplyTrack Team"
        ),
        from_email='SupplyTrack <danegela13@gmail.com>',
        recipient_list=[user.email],
        fail_silently=True,  # don't crash if email fails
    )

def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Check if email already used by ACTIVE user
            if User.objects.filter(email=form.cleaned_data['email'], is_active=True).exists():
                form.add_error('email', 'An active account with this email already exists.')
            else:
                # Store form data in session temporarily
                request.session['temp_user_data'] = {
                    'username': form.cleaned_data['username'],
                    'email': form.cleaned_data['email'],
                    'password': form.cleaned_data['password1'],
                }

                # Generate and store verification code
                code = generate_verification_code()
                request.session['verification_code'] = code
                request.session.set_expiry(180)  # expires in 3 mins
                send_verification_email(form.cleaned_data['email'], code)

                messages.success(request, "📧 A verification code has been sent to your email.")
                return redirect('users:verify_email')

        # Convert form errors into messages for modal display
        for field in form:
            for error in field.errors:
                messages.error(request, error)
    else:
        form = CustomUserCreationForm()

    return render(request, "users/register.html", {"form": form})

def verify_email_view(request):
    code = request.session.get('verification_code')
    temp_user_data = request.session.get('temp_user_data')

    if not temp_user_data:
        messages.error(request, "Session expired or invalid. Please register again.")
        return redirect('users:register')

    if request.method == 'POST':
        input_code = request.POST.get('code')
        if input_code == code:
            user = User.objects.create_user(
                username=temp_user_data['username'],
                email=temp_user_data['email'],
                password=temp_user_data['password']
            )
            user.is_active = True
            user.save()

            # Send welcome email after successful registration
            send_registration_success_email(user)

            del request.session['temp_user_data']
            del request.session['verification_code']

            messages.success(request, "✅ Email verified successfully!")
            return redirect('users:login')
        else:
            messages.error(request, "Invalid or expired code.")

    expiration_time = now() + timedelta(minutes=3)
    return render(request, 'users/verify_email.html', {
        'expiration_timestamp': int(expiration_time.timestamp() * 1000)
    })


def resend_verification_code_view(request):
    temp_user_data = request.session.get('temp_user_data')

    if not temp_user_data:
        messages.error(request, "No registration in progress.")
        return redirect('users:register')

    code = generate_verification_code()
    request.session['verification_code'] = code
    request.session.set_expiry(180)

    send_verification_email(temp_user_data['email'], code)
    messages.success(request, "📧 A new verification code has been sent to your email.")
    return redirect('users:verify_email')


def redirect_based_on_role(user):
    if user.role == "admin":
        return redirect("inventory:dashboard")
    elif user.role == "manager":
        return redirect("inventory:dashboard")
    elif user.role == "staff":
        return redirect("inventory:dashboard")
    elif user.role == "supplier":
        return redirect("suppliers:supplier_order_list")
    elif user.role == "customer":
        return redirect("store:product_list")
    else:
        return redirect("delivery:delivery_list") 

def login_view(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Send login notification email
            send_login_notification_email(user)

            redirect_url = redirect_based_on_role(user).url
            messages.success(request, f"Welcome back, {user.username}!")
            return render(request, "users/login.html", {
                "form": AuthenticationForm(),
                "redirect_after_login": redirect_url
            })
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, "users/login.html", {"form": form})


# Generate reset code and send to user's email
def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            code = generate_verification_code()
            request.session['reset_code'] = code
            request.session['reset_email'] = email
            request.session.set_expiry(180)  # expires in 3 mins
            send_verification_email(email, code)

            # ✅ SUCCESS MESSAGE ADDED HERE
            messages.success(request, '📨 A verification code has been sent to your email.')
            return redirect('users:verify_reset_code')
        except User.DoesNotExist:
            messages.error(request, 'No account with this email was found.')

    return render(request, 'users/forgot_password.html')

# Code verification for reset
def verify_reset_code_view(request):
    code = request.session.get('reset_code')
    if not code:
        messages.error(request, "Session expired or invalid. Please try again.")
        return redirect('users:forgot_password')

    if request.method == 'POST':
        input_code = request.POST.get('code')
        if input_code == code:
            request.session['code_verified'] = True
            return redirect('users:reset_password')
        else:
            messages.error(request, 'Invalid or expired code.')

    expiration_time = now() + timedelta(minutes=3)
    return render(request, 'users/verify_reset_code.html', {
        'expiration_timestamp': int(expiration_time.timestamp() * 1000)
    })

# Resend reset code
def resend_reset_code_view(request):
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, "No reset request found.")
        return redirect('users:forgot_password')

    code = generate_verification_code()
    request.session['reset_code'] = code
    request.session.set_expiry(180)
    send_verification_email(email, code)
    messages.success(request, "A new reset code has been sent.")
    return redirect('users:verify_reset_code')

# Final password reset
def reset_password_view(request):
    if not request.session.get('code_verified'):
        messages.error(request, "You must verify the code first.")
        return redirect('users:forgot_password')

    if request.method == 'POST':
        password = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, "Passwords do not match.")
        else:
            email = request.session.get('reset_email')
            try:
                user = User.objects.get(email=email)
                user.set_password(password)
                user.save()
                # Clear reset session
                for key in ['reset_code', 'reset_email', 'code_verified']:
                    if key in request.session:
                        del request.session[key]
                messages.success(request, "Password reset successful!")
                return redirect('users:login')
            except User.DoesNotExist:
                messages.error(request, "Error resetting password. Please try again.")

    return render(request, 'users/reset_password.html')

@api_view(['POST'])
def logout(request):
    try:
        res = Response()
        res.data = {'success': True}
        res.delete_cookie('access_token', path='/', samesite='None')
        res.delete_cookie('refresh_token', path='/', samesite='None')
        return res   
    except:
        return Response({'success': False}, status=400)
    
def logout_view(request):
    logout(request)  
    request.session.flush()  
    return redirect("store:product_list")

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def is_authenticated(request):
    return Response({'authenticated': True})

@login_required
def dashboard_view(request):
    return render(request, "users/dashboard.html", {"user": request.user})



@login_required
def user_management(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("You do not have permission to view this page.")

    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role')
        username = request.POST.get('username')
        email = request.POST.get('email')

        valid_roles = ['admin', 'manager', 'staff', 'supplier', 'delivery']

        if role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect('users:user_management')

        if user_id:  # Update existing user
            try:
                user = User.objects.get(id=user_id)
                user.username = username
                user.email = email
                user.role = role
                user.save()
                messages.success(request, f"User '{username}' updated successfully.")
                return redirect('users:user_management')
            except User.DoesNotExist:
                messages.error(request, "User not found.")
                return redirect('users:user_management')

        else:  # Add new user
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return redirect('users:user_management')
            user = User.objects.create_user(username=username, email=email, role=role)
            # Optionally set a default password or require password input
            user.set_password('defaultpassword123')  # Change or generate password securely
            user.save()
            messages.success(request, f"User '{username}' added successfully.")
            return redirect('users:user_management')

    context = {
        'users': users,
        'admins': User.objects.filter(role='admin'),
        'managers': User.objects.filter(role='manager'),
        'staffs': User.objects.filter(role='staff'),
        'customers': User.objects.filter(role='customer'),
        'suppliers': User.objects.filter(role='supplier'),
        'deliverys': User.objects.filter(role='delivery'),

    }
    return render(request, 'users/user_management.html', context)


@csrf_exempt 
@login_required
def delete_users(request):
    # Only admin can delete users
    if request.user.role != 'admin':
        return HttpResponseForbidden("You do not have permission to delete users.")  # 403 Forbidden if not admin

    if request.method == 'POST':
        try:
            # Parse JSON data from the request body
            data = json.loads(request.body)
            user_ids_to_delete = data.get('ids', [])
            
            if not user_ids_to_delete:
                return JsonResponse({'success': False, 'error': 'No user IDs provided to delete.'})

            # Delete users with the provided user_ids
            deleted_count, _ = User.objects.filter(id__in=user_ids_to_delete).delete()

            if deleted_count > 0:
                messages.success(request, f'{deleted_count} user(s) deleted successfully.')
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'No users found to delete.'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error occurred: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})