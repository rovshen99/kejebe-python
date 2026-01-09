from typing import Any, Dict, Optional

from rest_framework import serializers

from apps.banners.models import Banner
from apps.categories.models import Category
from apps.services.models import Service
from core.utils import format_price_text, get_lang_code, localized_value


class BannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    cta = serializers.SerializerMethodField()
    open = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ["id", "image_url", "title", "subtitle", "cta", "open"]

    def get_image_url(self, obj: Banner) -> Optional[str]:
        return obj.image.url if obj.image else None

    def get_title(self, obj: Banner) -> Optional[str]:
        lang = self.context.get("lang") or get_lang_code(self.context.get("request"))
        return localized_value(obj, "title", lang=lang)

    def get_subtitle(self, obj: Banner) -> Optional[str]:
        return None

    def get_cta(self, obj: Banner) -> Optional[str]:
        return None

    def get_open(self, obj: Banner) -> Dict[str, Any]:
        if obj.service_id:
            return {"type": "service", "service_id": obj.service_id}
        if obj.link_url:
            return {"type": "url", "url": obj.link_url}
        return {"type": "navigate", "screen": "Home"}


class CategoryLightSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    icon_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    open = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "title", "icon_url", "image_url", "open"]

    def get_title(self, obj: Category) -> Optional[str]:
        lang = self.context.get("lang") or get_lang_code(self.context.get("request"))
        return localized_value(obj, "name", lang=lang)

    def get_icon_url(self, obj: Category) -> Optional[str]:
        return obj.icon.url if obj.icon else None

    def get_image_url(self, obj: Category) -> Optional[str]:
        return obj.image.url if obj.image else None

    def get_open(self, obj: Category) -> Dict[str, Any]:
        return {"type": "search", "params": {"category_ids": [obj.id]}}


class StoriesRowItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    title = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True, required=False)
    story_cover_url = serializers.CharField(allow_null=True, required=False)
    has_unseen = serializers.BooleanField()
    stories_count = serializers.IntegerField()
    is_owner = serializers.BooleanField(default=False)
    open = serializers.DictField()

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        if isinstance(instance, dict):
            return super().to_representation(instance)
        data = {
            "id": getattr(instance, "id", None) or getattr(instance, "id"),
            "service_id": getattr(instance, "service_id", None) or getattr(instance, "id"),
            "title": getattr(instance, "title", ""),
            "avatar_url": getattr(instance, "avatar_url", None),
            "story_cover_url": getattr(instance, "story_cover_url", None),
            "has_unseen": getattr(instance, "has_unseen", True),
            "stories_count": getattr(instance, "stories_count", 0),
            "is_owner": getattr(instance, "is_owner", False),
            "open": getattr(instance, "open", {"type": "story", "service_id": getattr(instance, "id", None)}),
        }
        return super().to_representation(data)


class HomeServiceSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    city_title = serializers.SerializerMethodField()
    region_title = serializers.SerializerMethodField()
    category_title = serializers.SerializerMethodField()
    price_text = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()
    discount_text = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    open = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "title",
            "cover_url",
            "images",
            "city_title",
            "region_title",
            "category_title",
            "price_text",
            "rating",
            "reviews_count",
            "tags",
            "has_discount",
            "discount_text",
            "is_favorite",
            "open",
        ]

    def _lang(self):
        return get_lang_code(self.context.get("request"))

    def get_title(self, obj):
        return localized_value(obj, "title", lang=self._lang())

    def get_cover_url(self, obj):
        if getattr(obj, "avatar", None):
            return obj.avatar.url
        if getattr(obj, "background", None):
            return obj.background.url
        images = getattr(obj, "prefetched_images", None) or []
        first_image = images[0] if images else None
        if not first_image and hasattr(obj, "serviceimage_set"):
            first_image = obj.serviceimage_set.all().first()
        return first_image.image.url if first_image and getattr(first_image, "image", None) else None

    def get_images(self, obj):
        images = getattr(obj, "prefetched_images", None) or []
        if not images and hasattr(obj, "serviceimage_set"):
            images = obj.serviceimage_set.all()
        urls = []
        for image in images:
            img_field = getattr(image, "image", None)
            if img_field and getattr(img_field, "url", None):
                urls.append(img_field.url)
        return urls

    def _localized_name(self, obj, prefix):
        return localized_value(obj, prefix, lang=self._lang())

    def get_city_title(self, obj):
        return self._localized_name(getattr(obj, "city", None), "name")

    def get_region_title(self, obj):
        city = getattr(obj, "city", None)
        return self._localized_name(getattr(city, "region", None), "name")

    def get_category_title(self, obj):
        return self._localized_name(getattr(obj, "category", None), "name")

    def get_price_text(self, obj):
        return format_price_text(
            getattr(obj, "price_min", None),
            getattr(obj, "price_max", None),
            lang=self._lang(),
        )

    def get_rating(self, obj):
        rating = getattr(obj, "rating", None)
        return round(float(rating), 2) if rating is not None else None

    def get_reviews_count(self, obj):
        count = getattr(obj, "reviews_count", None)
        return int(count) if count is not None else 0

    def get_tags(self, obj):
        tags_rel = getattr(obj, "tags", None)
        if not tags_rel:
            return []
        tags = tags_rel.all() if hasattr(tags_rel, "all") else tags_rel
        lang = self._lang()
        names = []
        for tag in tags:
            name = localized_value(tag, "name", lang=lang)
            if name:
                names.append(name)
        return names

    def get_has_discount(self, obj):
        return bool(self.get_discount_text(obj))

    def get_discount_text(self, obj):
        return getattr(obj, "discount_text", None)

    def get_is_favorite(self, obj):
        annotated = getattr(obj, "is_favorite", None)
        return bool(annotated) if annotated is not None else False

    def get_open(self, obj):
        return {"type": "service", "service_id": obj.id}


class HomeBlockSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField(allow_null=True)
    limit = serializers.IntegerField(required=False)
    style = serializers.DictField(required=False)
    items = serializers.ListField(child=serializers.DictField(), required=False)
    view_all = serializers.DictField(required=False, allow_null=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": instance.get("id"),
            "type": instance.get("type"),
            "title": instance.get("title"),
            "limit": instance.get("limit"),
            "style": instance.get("style", {}),
            "items": instance.get("items", []),
            "view_all": instance.get("view_all"),
        }
