from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema

from .models import User
from .serializers import RegisterSerializer, UserSerializer, UserUpdateSerializer


@extend_schema(
    request=RegisterSerializer,
    responses={201: UserSerializer},
    tags=["Auth"],
    summary="Register a new user",
    description="Creates a new user with the provided role and details."
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@extend_schema(
    responses={200: UserSerializer},
    tags=["Auth"],
    summary="Get current user",
    description="Returns information about the authenticated user (requires token)."
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
    summary="Update current user's profile",
    description="Allows the authenticated user to update name, surname, email, role, and avatar."
)
class MeUpdateView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        return self.request.user
