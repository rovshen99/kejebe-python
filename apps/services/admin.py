import nested_admin
from django import forms
from django.conf import settings
from django.contrib import admin
from django.db.models import Max
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError

from core.mixins import IconPreviewMixin
from .models import (
    AttributeOption,
    Service,
    ServiceAttributeValue,
    ServiceContact,
    ServiceImage,
    ServiceVideo,
    Review,
    Favorite,
    ServiceTag,
    Attribute,
    CategoryAttribute,
    ContactType,
    ProductAttributeValue,
    ServiceProductImage,
    ServiceProduct,
    ServiceApplication,
    ServiceApplicationImage,
    ServiceApplicationLink,
)


def _allowed_attribute_queryset(category_id, scope):
    if not category_id:
        return Attribute.objects.none()
    return (
        Attribute.objects.filter(
            is_active=True,
            category_links__category_id=category_id,
            category_links__scope=scope,
        )
        .distinct()
        .order_by("name_tm", "id")
    )


class ScopedAttributeValueAdminForm(forms.ModelForm):
    scope = None

    def __init__(self, *args, parent_instance=None, scope=None, **kwargs):
        self.parent_instance = parent_instance
        self.scope = scope or self.scope
        super().__init__(*args, **kwargs)
        self._configure_attribute_queryset()
        self._configure_option_queryset()

    def _get_service(self):
        if isinstance(self.parent_instance, Service):
            return self.parent_instance
        if isinstance(self.parent_instance, ServiceProduct):
            return getattr(self.parent_instance, "service", None)
        if getattr(self.instance, "service_id", None):
            return self.instance.service
        product = getattr(self.instance, "product", None)
        if product is not None:
            return getattr(product, "service", None)
        return None

    def _configure_attribute_queryset(self):
        service = self._get_service()
        category_id = getattr(service, "category_id", None)
        if category_id and self.scope:
            queryset = _allowed_attribute_queryset(category_id, self.scope)
        elif getattr(self.instance, "attribute_id", None):
            queryset = Attribute.objects.filter(pk=self.instance.attribute_id)
        else:
            queryset = Attribute.objects.none()
        self.fields["attribute"].queryset = queryset

    def _configure_option_queryset(self):
        attribute_id = None
        if self.is_bound:
            attribute_id = self.data.get(self.add_prefix("attribute")) or None
        elif getattr(self.instance, "attribute_id", None):
            attribute_id = self.instance.attribute_id

        if attribute_id:
            queryset = AttributeOption.objects.filter(
                attribute_id=attribute_id,
                is_active=True,
            ).order_by("sort_order", "id")
        elif getattr(self.instance, "option_id", None):
            queryset = AttributeOption.objects.filter(pk=self.instance.option_id)
        else:
            queryset = AttributeOption.objects.none()
        self.fields["option"].queryset = queryset

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("DELETE"):
            return cleaned_data

        attribute = cleaned_data.get("attribute")
        option = cleaned_data.get("option")
        service = self._get_service()
        category_id = getattr(service, "category_id", None)

        if attribute and (
            not category_id
            or not CategoryAttribute.objects.filter(
                category_id=category_id,
                attribute=attribute,
                scope=self.scope,
            ).exists()
        ):
            self.add_error("attribute", "This attribute is not allowed for the selected category and scope.")

        if option and attribute and option.attribute_id != attribute.id:
            self.add_error("option", "This option does not belong to the selected attribute.")

        return cleaned_data


class ScopedAttributeValueInlineFormSet(BaseInlineFormSet):
    scope = None

    def _construct_form(self, i, **kwargs):
        kwargs["parent_instance"] = self.instance
        kwargs["scope"] = self.scope
        return super()._construct_form(i, **kwargs)


class ServiceAttributeValueAdminForm(ScopedAttributeValueAdminForm):
    scope = CategoryAttribute.Scope.SERVICE

    class Meta:
        model = ServiceAttributeValue
        fields = "__all__"


class ServiceAttributeValueInlineFormSet(ScopedAttributeValueInlineFormSet):
    scope = CategoryAttribute.Scope.SERVICE


class ProductAttributeValueAdminForm(ScopedAttributeValueAdminForm):
    scope = CategoryAttribute.Scope.PRODUCT

    class Meta:
        model = ProductAttributeValue
        fields = "__all__"


class ProductAttributeValueInlineFormSet(ScopedAttributeValueInlineFormSet):
    scope = CategoryAttribute.Scope.PRODUCT


class ServiceContactInline(nested_admin.NestedTabularInline):
    model = ServiceContact
    extra = 1


class ServiceImageInline(nested_admin.NestedTabularInline):
    model = ServiceImage
    extra = 1


class ServiceVideoAdminForm(forms.ModelForm):
    class Meta:
        model = ServiceVideo
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Existing rows must remain editable even when the original upload was deleted after HLS generation.
        self.fields["file"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("DELETE"):
            return cleaned_data

        uploaded_file = cleaned_data.get("file")
        if not getattr(self.instance, "pk", None) and not uploaded_file:
            self.add_error("file", "This field is required.")
        return cleaned_data


class ServiceVideoInline(IconPreviewMixin, nested_admin.NestedTabularInline):
    model = ServiceVideo
    form = ServiceVideoAdminForm
    extra = 1
    icon_field_name = "preview"
    icon_width = 80
    icon_height = 80
    readonly_fields = ("icon_preview", "hls_ready", "hls_playlist")
    fields = ("file", "preview", "icon_preview", "position", "hls_ready", "hls_playlist")


class ServiceAttributeValueInline(nested_admin.NestedTabularInline):
    model = ServiceAttributeValue
    form = ServiceAttributeValueAdminForm
    formset = ServiceAttributeValueInlineFormSet
    extra = 0
    fields = (
        'attribute',
        'option',
        'value_text_tm', 'value_text_ru',
        'value_number', 'value_boolean',
    )


class ServiceProductAttributeValueInline(nested_admin.NestedTabularInline):
    model = ProductAttributeValue
    form = ProductAttributeValueAdminForm
    formset = ProductAttributeValueInlineFormSet
    extra = 0
    fields = (
        'attribute',
        'option',
        'value_text_tm', 'value_text_ru',
        'value_number', 'value_boolean',
    )


class ServiceProductImageInline(nested_admin.NestedTabularInline):
    model = ServiceProductImage
    extra = 0


class ServiceProductInline(nested_admin.NestedStackedInline):
    model = ServiceProduct
    extra = 0
    inlines = [ServiceProductAttributeValueInline, ServiceProductImageInline]


class ServiceAvailableCityInline(nested_admin.NestedTabularInline):
    model = Service.available_cities.through
    extra = 0
    verbose_name = 'Available City'
    verbose_name_plural = 'Available Cities'
    autocomplete_fields = ['city']
    fields = ('city',)
    can_delete = True


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return [single_file_clean(data, initial)]


class ServiceAdminForm(forms.ModelForm):
    bulk_images = MultipleFileField(
        required=False,
        label="Upload images (multiple)",
        help_text="You can upload multiple service images at once.",
    )
    bulk_videos = MultipleFileField(
        required=False,
        label="Upload videos (multiple)",
        help_text="You can upload multiple service videos at once.",
    )

    class Meta:
        model = Service
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        additional_categories = cleaned_data.get("additional_categories")

        if category and additional_categories and additional_categories.filter(pk=category.pk).exists():
            self.add_error("additional_categories", "Primary category must not be duplicated.")

        if additional_categories and additional_categories.count() > 3:
            self.add_error("additional_categories", "No more than 3 additional categories are allowed.")

        video_files = cleaned_data.get("bulk_videos") or []
        if video_files:
            validators = ServiceVideo._meta.get_field("file").validators
            for video_file in video_files:
                for validator in validators:
                    try:
                        validator(video_file)
                    except ValidationError as exc:
                        self.add_error("bulk_videos", exc.messages)
                        break

        return cleaned_data


@admin.register(Service)
class ServiceAdmin(nested_admin.NestedModelAdmin):
    form = ServiceAdminForm
    list_display = (
        'title_tm', 'vendor', 'category', 'additional_categories_list',
        'city', 'show_location', 'work_experience_years', 'is_active', 'is_verified', 'is_vip', 'priority'
    )
    list_filter = ('category', 'city', 'show_location', 'is_active', 'is_verified', 'is_vip')
    search_fields = ('title_tm', 'title_ru', 'vendor__name', 'category__name_tm')
    ordering = ('priority', '-created_at')
    filter_horizontal = ('regions', 'tags', 'additional_categories')
    inlines = [
        ServiceContactInline,
        ServiceImageInline,
        ServiceVideoInline,
        ServiceAttributeValueInline,
        ServiceAvailableCityInline,
        ServiceProductInline,
    ]

    class Media:
        css = {
            "all": (
                "admin/css/service_map.css",
                "vendor/leaflet/leaflet.css",
            )
        }
        js = (
            "vendor/leaflet/leaflet.js",
            "admin/js/service_map.js",
        )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("additional_categories")

    def additional_categories_list(self, obj):
        return ", ".join(category.name_tm for category in obj.additional_categories.all())

    additional_categories_list.short_description = "Additional Categories"

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["osm_tile_url"] = getattr(settings, "OSM_TILE_URL", "")
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["osm_tile_url"] = getattr(settings, "OSM_TILE_URL", "")
        return super().add_view(request, form_url, extra_context=extra_context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        service = form.instance
        image_files = form.cleaned_data.get("bulk_images") or []
        video_files = form.cleaned_data.get("bulk_videos") or []
        self._save_bulk_images(service, image_files)
        self._save_bulk_videos(service, video_files)

    @staticmethod
    def _next_position(model, service):
        max_position = (
            model.objects.filter(service=service).aggregate(max_position=Max("position")).get("max_position") or 0
        )
        return int(max_position) + 1

    def _save_bulk_images(self, service, image_files):
        if not image_files:
            return
        next_position = self._next_position(ServiceImage, service)
        for image_file in image_files:
            ServiceImage.objects.create(
                service=service,
                image=image_file,
                position=next_position,
            )
            next_position += 1

    def _save_bulk_videos(self, service, video_files):
        if not video_files:
            return
        next_position = self._next_position(ServiceVideo, service)
        for video_file in video_files:
            ServiceVideo.objects.create(
                service=service,
                file=video_file,
                position=next_position,
            )
            next_position += 1


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('service', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'service')
    search_fields = ('comment', 'user__name', 'service__title_tm')
    ordering = ('-created_at',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_target')
    search_fields = (
        'user__name',
        'service__title_tm', 'service__title_ru',
        'product__title_tm', 'product__title_ru',
    )

    def get_target(self, obj):
        return obj.service or obj.product
    get_target.short_description = 'Target'


@admin.register(ServiceTag)
class ServiceTagAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru')
    search_fields = ('name_tm', 'name_ru')


class AttributeOptionInline(admin.TabularInline):
    model = AttributeOption
    extra = 0
    fields = ("value", "label_tm", "label_ru", "sort_order", "is_active")


@admin.register(Attribute)
class ServiceAttributeAdmin(IconPreviewMixin, admin.ModelAdmin):
    list_display = (
        'name_tm', 'slug', 'icon_preview', 'input_type', 'unit_tm', 'unit_ru',
        'min_value', 'max_value', 'step',
        'is_required', 'is_active',
    )
    list_filter = ('input_type', 'is_active')
    search_fields = ('name_tm', 'name_ru', 'slug')
    readonly_fields = ('icon_preview',)
    inlines = [AttributeOptionInline]


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):
    list_display = (
        'category', 'attribute', 'scope', 'section_tm',
        'is_required', 'show_in_card', 'show_in_detail', 'show_in_filters',
        'filter_type', 'filter_order', 'sort_order'
    )
    list_filter = ('scope', 'is_required', 'show_in_card', 'show_in_detail', 'show_in_filters', 'category')
    search_fields = ('category__name_tm', 'category__name_ru', 'attribute__name_tm', 'attribute__name_ru', 'attribute__slug')
#
#
# @admin.register(ProductAttributeValue)
# class ServiceAttributeValueAdmin(admin.ModelAdmin):
#     list_display = ('product', 'attribute', 'get_display_value')
#     list_filter = ('attribute__category', 'attribute__input_type')
#     search_fields = (
#         'product__title_tm', 'product__title_ru', 'product__title_en',
#         'attribute__name_tm', 'attribute__name_ru', 'attribute__name_en',
#     )
#
#     def get_display_value(self, obj):
#         return obj.value
#     get_display_value.short_description = "Value"


@admin.register(ContactType)
class ContactTypeAdmin(IconPreviewMixin, admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru', 'icon_preview')
    search_fields = ('name_tm', 'name_ru')
    readonly_fields = ('slug',)


class ServiceApplicationImageInline(IconPreviewMixin, admin.TabularInline):
    model = ServiceApplicationImage
    extra = 0
    icon_field_name = 'image'
    icon_width = 80
    icon_height = 80
    readonly_fields = ('icon_preview',)
    fields = ('icon_preview', 'image',)


class ServiceApplicationLinkInline(admin.TabularInline):
    model = ServiceApplicationLink
    extra = 0
    fields = ("url",)


@admin.register(ServiceApplication)
class ServiceApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'phone', 'email', 'category', 'category_name', 'city', 'city_name',
        'price_from', 'work_experience_years', 'status', 'created_at'
    )
    list_filter = ('status', 'category', 'city')
    search_fields = ('title', 'phone', 'email', 'description', 'contact_name', 'category_name', 'city_name', 'address')
    readonly_fields = ('created_at',)
    inlines = [ServiceApplicationLinkInline, ServiceApplicationImageInline]
