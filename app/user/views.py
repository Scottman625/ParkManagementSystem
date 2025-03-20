from modelCore.models import User 
from rest_framework import generics, authentication, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework import viewsets, mixins
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

from user.serializers import (
    UserSerializer, 
    AuthTokenSerializer, 
    UpdateUserSerializer, 
    GetUserSerializer,
    LoginSerializer,
    RegisterSerializer,
    RefreshTokenSerializer
)
from django.db.models import Q

# 添加UserViewSet
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """用戶視圖集，只提供讀取功能"""
    queryset = User.objects.all()
    serializer_class = GetUserSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """限制只有管理員可以查看所有用戶，普通用戶只能查看自己"""
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """獲取當前用戶的詳細信息"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='post',
        operation_description="更新密碼",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['old_password', 'new_password'],
            properties={
                'old_password': openapi.Schema(type=openapi.TYPE_STRING),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(
                description="密碼更新成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "密碼更新失敗",
        }
    )
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """更新密碼"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response({'detail': '必須提供舊密碼和新密碼'}, status=400)
        
        if not user.check_password(old_password):
            return Response({'detail': '舊密碼不正確'}, status=400)
        
        user.set_password(new_password)
        user.save()
        
        # 重新生成 token
        Token.objects.filter(user=user).delete()
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': '密碼更新成功',
            'token': token.key
        })

class RegisterView(APIView):
    """使用者註冊"""
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        operation_description="使用者註冊",
        responses={
            201: openapi.Response(
                description="註冊成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    }
                )
            ),
            400: "註冊失敗"
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name if user.name else user.email.split('@')[0]  # 如果未設置名稱則使用郵箱名
            }
        }, status=201)

class CreateUserView(generics.CreateAPIView):
    """管理員創建新用戶"""
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAdminUser,)

    @swagger_auto_schema(
        operation_description="管理員創建新用戶（需要管理員權限）",
        responses={
            201: UserSerializer()
        }
    )
    def perform_create(self, serializer):
        user = serializer.save()
        return user

#http://localhost:8000/api/user/token/  要用 post, 並帶參數
class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user"""
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

#http://localhost:8000/api/user/me/  要有 token
class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user"""
    serializer_class = UpdateUserSerializer
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        """Retrieve and return authentication user"""
        # if self.request.user.line_id != None and self.request.user.line_id != '':
        #     self.request.user.is_gotten_line_id = True
        
        user = self.request.user

        return user

class UpdateUserLineIdView(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    def put(self, request, format=None):
        try:
            # print(self.request.user)
            # print(self.request.data.get('line_id'))
            user = self.request.user
            user.line_id = self.request.data.get('line_id')
            user.save()
            return Response({'message': 'success update!'})
        except Exception as e:
            raise APIException("wrong token or null line_id")

class UpdateUserPassword(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    def put(self, request, format=None):
        user = self.request.user
        old_password = self.request.data.get('old_password')

        if user.check_password(old_password):
            new_password = self.request.data.get('new_password')
            user.set_password(new_password)
            user.save()
            return Response({'message': 'success update!'})
        else:
            raise APIException("wrong old password")


class UpdateUserImage(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    def put(self, request, format=None):
        user = self.request.user
        image = request.data.get('image')
        if image != None:
            user.image = image
        user.save()
        serializer = GetUserSerializer(user)
        return Response(serializer.data)

class GetUpdateUserFCMNotify(APIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        user = self.request.user
        return Response({'is_fcm_notify':user.is_fcm_notify})

    def put(self, request, format=None):
        user = self.request.user
        is_fcm_notify = request.data.get('is_fcm_notify')
        if is_fcm_notify =='true' or is_fcm_notify =='True':
            user.is_fcm_notify = True
        else:
             user.is_fcm_notify = False
        user.save()
        return Response({'message':'ok'})

class DeleteUser(generics.DestroyAPIView):
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer
    queryset = User.objects.all()
    # lookup_field = 'pk'
    def delete(self, request, pk, format=None):
        
        auth_user = self.request.user
        user = User.objects.get(id=pk)
        if user == auth_user:
            if qualifications_to_delete_user(user) == False:
                return Response("continuous order exists")
            else:
                user.delete()
                return Response('delete user')
        else:
            return Response('not auth')


def qualifications_to_delete_user(user):
    for order in user.user_orders.all():
        if order.case.state == 'unComplete':
            return False
    for order in user.servant_orders.all():
        if order.case.state == 'unComplete':
            return False

class LoginView(APIView):
    """使用者登入"""
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        request_body=LoginSerializer,
        operation_description="使用者登入並獲取 Token",
        responses={
            200: openapi.Response(
                description="登入成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_admin': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            }
                        )
                    }
                )
            ),
            400: "認證失敗"
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_admin': user.is_staff
            }
        })

class LogoutView(APIView):
    """使用者登出"""
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="使用者登出並刪除 Token",
        responses={
            200: openapi.Response(
                description="登出成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def post(self, request):
        # 刪除用戶的 token
        request.user.auth_token.delete()
        return Response({'message': '成功登出'})

class RefreshTokenView(APIView):
    """刷新用戶的令牌"""
    serializer_class = RefreshTokenSerializer
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        request_body=RefreshTokenSerializer,
        operation_description="刷新用戶的令牌",
        responses={
            200: openapi.Response(
                description="令牌刷新成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "令牌無效"
        }
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_token_key = serializer.validated_data['token']
        try:
            old_token = Token.objects.get(key=old_token_key)
            user = old_token.user
            
            # 刪除舊令牌
            old_token.delete()
            
            # 創建新令牌
            new_token, _ = Token.objects.get_or_create(user=user)
            
            return Response({
                'token': new_token.key
            })
        except Token.DoesNotExist:
            return Response({"detail": "令牌無效"}, status=400)