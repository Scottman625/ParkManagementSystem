from django.contrib.auth import get_user_model, authenticate

from rest_framework import serializers
from modelCore.models import User
from django.utils.translation import gettext_lazy as _

class UserSerializer(serializers.ModelSerializer):
    """Serializer for the users object"""
    # is_gotten_line_id = serializers.BooleanField(default=False)

    class Meta:
        model = get_user_model()
        fields = ('email', 'password', 'first_name', 'last_name', 'name', 'line_id', 'apple_id')
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 5},
            'line_id': {'write_only': True},
            'apple_id': {'write_only': True},
        }

    def create(self, validated_data):
        """Create a new user with encrypted password and return it"""
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """Update a user, setting the password correctly and return it"""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user

class UpdateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'first_name', 'last_name', 'name', 'gender', 'address', 'image')
        read_only_fields = ('id', 'email', 'image')

class AuthTokenSerializer(serializers.Serializer):
    """Serializer for the user authentication object"""
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
    )
    line_id = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        allow_null=True,
        required=False,
    )
    apple_id = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        allow_null=True,
        required=False,
    )

    def validate(self, attrs):
        """Validate and authenticate the user"""
        email = attrs.get('email')
        password = attrs.get('password')
        line_id = attrs.get('line_id')
        apple_id = attrs.get('apple_id')
        
        user = None

        if email and password and password != '00000':
            # 使用 authenticate 進行認證
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
        
        if not user and line_id:
            try:
                user = User.objects.get(line_id=line_id)
            except User.DoesNotExist:
                pass
        
        if not user and apple_id:
            try:
                user = User.objects.get(apple_id=apple_id)
            except User.DoesNotExist:
                pass

        if not user:
            msg = 'Unable to authenticate with provided credentials'
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return attrs

class GetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ('password',)
        read_only_fields = ('email',)

class LoginSerializer(serializers.Serializer):
    """使用者登入序列化器"""
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        """驗證並認證使用者"""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # 使用 authenticate 進行認證
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if user:
                attrs['user'] = user
                return attrs
            
            msg = _('無法使用提供的認證資訊登入')
            raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('必須包含"email"和"password"')
            raise serializers.ValidationError(msg, code='authorization')

class RegisterSerializer(serializers.ModelSerializer):
    """使用者註冊序列化器"""

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name',]
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 5},
            'first_name': {'required': False},
            'last_name': {'required': False},
            # 'name': {'required': False},
            # 'gender': {'required': False},
        }

    def validate(self, attrs):
        
        # 驗證電子郵件是否已被註冊
        email = attrs['email']
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "此電子郵件已被註冊"})
        
        return attrs

    def create(self, validated_data):
        # 創建用戶
        return User.objects.create_user(**validated_data)

class RefreshTokenSerializer(serializers.Serializer):
    """令牌刷新序列化器"""
    token = serializers.CharField()

    def validate_token(self, value):
        from rest_framework.authtoken.models import Token
        
        try:
            # 驗證令牌是否存在
            token = Token.objects.get(key=value)
            return value
        except Token.DoesNotExist:
            raise serializers.ValidationError("提供的令牌無效")

