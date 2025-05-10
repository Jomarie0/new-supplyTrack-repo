from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from django.contrib.auth import login, logout
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import User
from .serializer import UserRegistrationSerializer, UserSerializer
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
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
        
        
def register_view(request):
    success = False  # Flag to indicate registration success
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            success = True  # Set success flag to True
            return render(request, "users/register.html", {"form": form, "success": success})

    else:
        form = CustomUserCreationForm()

    return render(request, "users/register.html", {"form": form, "success": success})

def redirect_based_on_role(user):
    if user.role == "admin":
        return redirect("inventory:admin_dashboard")
    elif user.role == "manager":
        return redirect("inventory:manager_dashboard")
    elif user.role == "staff":
        return redirect("inventory:staff_dashboard")
    else:
        return redirect("inventory:staff_dashboard") 

def login_view(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)  
    
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect_based_on_role(user)
        else:
            messages.error(request, "Invalid username or password.")
    
    else:
        form = AuthenticationForm()
    
    return render(request, "users/login.html", {"form": form})



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
    return redirect("users:login")

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def is_authenticated(request):
    return Response({'authenticated': True})

@login_required
def dashboard_view(request):
    return render(request, "users/dashboard.html", {"user": request.user})



@login_required
def user_management(request):
    # Only admin can access this view
    if request.user.role != 'admin':
        return HttpResponseForbidden("You do not have permission to view this page.")  # Return 403 for unauthorized access

    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('new_role')

        # Ensure the new role is valid
        valid_roles = ['admin', 'manager', 'staff', 'delivery_confirmation']
        if new_role not in valid_roles:
            messages.error(request, "Invalid role selected.")
            return redirect('users:user_management')

        try:
            user = User.objects.get(id=user_id)
            user.role = new_role
            user.save()
            messages.success(request, f"User role updated to {new_role}.")
            return redirect('users:user_management')  # reload the page after update
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('users:user_management')  # redirect with error message

    context = {
        'users': users,
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
