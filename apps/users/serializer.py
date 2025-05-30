from rest_framework import serializers
from .models import User, CustomerProfile, SupplierProfile # Make sure to import all relevant models
from apps.transactions.models import Transaction # Import Transaction

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        # Only include fields directly on the User model for initial registration
        fields = ['username', 'email', 'password', 'role'] 

    def create(self, validated_data):
        # Extract role and password from validated data before creating the user
        role = validated_data.pop('role', 'staff') 
        password = validated_data.pop('password')

        # Create the User instance with the remaining validated data
        user = User(**validated_data) 
        user.role = role
        user.set_password(password) # Hash the password!
        user.save() # This will trigger your User model's save method, handling 'is_approved'

        # Now, conditionally create the associated profile based on the role
        if role == 'customer':
            CustomerProfile.objects.create(user=user)
        elif role == 'supplier':
            SupplierProfile.objects.create(user=user)
        # For 'admin', 'manager', 'staff', 'delivery' roles, no separate profile is needed

        # FOR TRANSACTION HISTORY
        Transaction.objects.create(
            user=user,
            transaction_type='user_registration',
            description=f"New user '{user.username}' registered with role '{role}'.",
            status='completed' # Or 'pending_email_verification' if you have that step
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    # For retrieving user data, you'll likely want to include profile details.
    # You can use nested serializers or SerializerMethodField for this.

    # Option 1: Read-only PrimaryKeyRelatedField (simpler, returns ID)
    customer_profile = serializers.PrimaryKeyRelatedField(read_only=True) 
    supplier_profile = serializers.PrimaryKeyRelatedField(read_only=True) 

    # Option 2: Nested Serializers (more detailed, returns full profile object)
    # customer_profile = CustomerProfileSerializer(read_only=True)
    # supplier_profile = SupplierProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_approved', 'date_requested', 'customer_profile', 'supplier_profile']
        read_only_fields = ['is_approved', 'date_requested'] # These are managed by the model