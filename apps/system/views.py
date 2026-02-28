from drf_spectacular.utils import extend_schema
from django.shortcuts import render
from rest_framework import mixins, permissions, viewsets

from .models import SystemContact, AccountDeletionRequest
from .serializers import SystemContactSerializer
from .forms import DeleteAccountForm


@extend_schema(tags=["System"])
class SystemContactViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SystemContactSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            SystemContact.objects.filter(is_active=True)
            .select_related("type")
            .only("id", "value", "type__slug", "type__name_tm", "type__name_ru", "type__icon", "priority")
            .order_by("priority", "id")
        )


def delete_account_view(request):
    success = False
    if request.method == "POST":
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            AccountDeletionRequest.objects.create(phone=form.cleaned_data["phone"])
            success = True
            form = DeleteAccountForm()
    else:
        form = DeleteAccountForm()

    return render(
        request,
        "delete_account.html",
        {
            "form": form,
            "success": success,
            "app_name": "Kejebe",
            "developer_name": "Rovshen Berdimyradov",
        },
    )
