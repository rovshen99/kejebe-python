from django.db.models import Exists, OuterRef, Value, BooleanField

from .models import Favorite


class FavoriteAnnotateMixin:
    favorite_field = None

    def annotate_is_favorite(self, queryset):
        user = getattr(self, 'request', None)
        user = getattr(user, 'user', None)
        if self.favorite_field not in {'service', 'product'}:
            return queryset

        if user and getattr(user, 'is_authenticated', False):
            return queryset.annotate(
                is_favorite=Exists(
                    Favorite.objects.filter(user=user, **{self.favorite_field: OuterRef('pk')})
                )
            )
        return queryset.annotate(is_favorite=Value(False, output_field=BooleanField()))
