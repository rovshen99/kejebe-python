from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .models import User
from .serializers import RegisterSerializer, UserSerializer, UserUpdateSerializer


@extend_schema(
    request=RegisterSerializer,
    responses={201: UserSerializer},
    tags=["Auth"],
    summary="Регистрация нового пользователя",
    description="Создает нового пользователя с указанной ролью и данными."
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@extend_schema(
    responses={200: UserSerializer},
    tags=["Auth"],
    summary="Получить данные текущего пользователя",
    description="Возвращает информацию об авторизованном пользователе (требуется токен)."
)
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    request=UserUpdateSerializer,
    responses={200: UserSerializer},
    tags=["Auth"],
    summary="Обновление имени и email текущего пользователя",
    description="Позволяет авторизованному пользователю изменить только имя и email."
)
class MeUpdateView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
