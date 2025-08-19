from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from apps.categories.models import Category
from apps.regions.models import Region, City
from apps.services.validators import validate_file_size
from apps.users.models import User


class Service(models.Model):
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Vendor"))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_("Category"))
    avatar = models.ImageField(
        upload_to="services/avatars", verbose_name=_("Avatar"), null=True, default=None, blank=True
    )
    regions = models.ManyToManyField(Region, related_name='services', verbose_name=_("Regions"))
    cities = models.ManyToManyField(City, related_name='services', verbose_name=_("Cities"))

    title_tm = models.CharField(max_length=255, verbose_name=_("Title (TM)"))
    title_ru = models.CharField(max_length=255, verbose_name=_("Title (RU)"))
    title_en = models.CharField(max_length=255, verbose_name=_("Title (EN)"))

    description_tm = models.TextField(verbose_name=_("Description (TM)"))
    description_ru = models.TextField(verbose_name=_("Description (RU)"))
    description_en = models.TextField(verbose_name=_("Description (EN)"))

    price_min = models.FloatField(null=True, blank=True, verbose_name=_("Minimum Price"))
    price_max = models.FloatField(null=True, blank=True, verbose_name=_("Maximum Price"))

    is_catalog = models.BooleanField(default=False, verbose_name=_("Show in Catalog"))
    latitude = models.FloatField(null=True, blank=True, verbose_name=_("Latitude"))
    longitude = models.FloatField(null=True, blank=True, verbose_name=_("Longitude"))
    background = models.ImageField(upload_to="services/backgrounds", verbose_name=_("Background"), null=True)

    is_active = models.BooleanField(default=False, verbose_name=_("Is Active"))
    active_until = models.DateTimeField(null=True, blank=True, verbose_name=_("Active Until"))

    tags = models.ManyToManyField("ServiceTag", blank=True, related_name="services", verbose_name=_("Tags"))

    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        ordering = ('priority', '-created_at')

    def __str__(self):
        return self.title_tm


class ServiceContact(models.Model):
    service = models.ForeignKey(Service, related_name='contacts', on_delete=models.CASCADE, verbose_name=_("Service"))
    contact_type = models.CharField(max_length=50, verbose_name=_("Contact Type"))
    value = models.CharField(max_length=255, verbose_name=_("Value"))

    class Meta:
        verbose_name = _("Service Contact")
        verbose_name_plural = _("Service Contacts")

    def __str__(self):
        return f"{self.contact_type}: {self.value}"


class ServiceImage(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    image = models.ImageField(upload_to="services/images", verbose_name=_("Image"), null=True)

    class Meta:
        verbose_name = _("Service Image")
        verbose_name_plural = _("Service Images")

    def __str__(self):
        return self.image


class ServiceVideo(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    file = models.FileField(
        upload_to="services/videos/",
        verbose_name=_("Video file"),
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "mov", "webm", "mkv"]), validate_file_size],
        null=True,
    )

    class Meta:
        verbose_name = _("Service Video")
        verbose_name_plural = _("Service Videos")

    def __str__(self):
        return self.file


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    rating = models.PositiveSmallIntegerField(verbose_name=_("Rating"))
    comment = models.TextField(verbose_name=_("Comment"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.user} – {self.rating}★"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))

    class Meta:
        verbose_name = _("Favorite")
        verbose_name_plural = _("Favorites")
        unique_together = ('user', 'service')

    def __str__(self):
        return f"{self.user} ♥ {self.service}"


class ServiceTag(models.Model):
    name_tm = models.CharField(max_length=100, verbose_name=_("Tag Name (TM)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Tag Name (RU)"))
    name_en = models.CharField(max_length=100, verbose_name=_("Tag Name (EN)"))

    class Meta:
        verbose_name = _("Service Tag")
        verbose_name_plural = _("Service Tags")

    def __str__(self):
        return self.name_tm


class ServiceAttribute(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="attribute_definitions", verbose_name=_("Category")
    )
    name_tm = models.CharField(max_length=100, verbose_name=_("Attribute Name (TM)"))
    name_ru = models.CharField(max_length=100, verbose_name=_("Attribute Name (RU)"))
    name_en = models.CharField(max_length=100, verbose_name=_("Attribute Name (EN)"))

    slug = models.SlugField(db_index=True, verbose_name=_("Attribute Slug"))
    input_type = models.CharField(
        max_length=20,
        choices=[
            ('text', _('Text')),
            ('number', _('Number')),
            ('boolean', _('Boolean')),
            ('choice', _('Choice')),
        ],
        db_index=True,
        verbose_name=_("Input Type")
    )
    is_required = models.BooleanField(default=False, verbose_name=_("Is Required"))

    class Meta:
        verbose_name = _("Attribute")
        verbose_name_plural = _("Attributes")
        unique_together = ('category', 'slug')

    def __str__(self):
        return f"{self.category.name_tm} → {self.name_tm}"


class ServiceAttributeValue(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="attributes", verbose_name=_("Service"))
    attribute = models.ForeignKey(
        ServiceAttribute, on_delete=models.CASCADE, verbose_name=_("Attribute")
    )

    value_text_tm = models.TextField(null=True, blank=True, verbose_name=_("Text Value (TM)"))
    value_text_ru = models.TextField(null=True, blank=True, verbose_name=_("Text Value (RU)"))
    value_text_en = models.TextField(null=True, blank=True, verbose_name=_("Text Value (EN)"))

    value_number = models.FloatField(null=True, blank=True, verbose_name=_("Number Value"))
    value_boolean = models.BooleanField(null=True, blank=True, verbose_name=_("Boolean Value"))

    class Meta:
        verbose_name = _("Attribute Value")
        verbose_name_plural = _("Attribute Values")
        unique_together = ('service', 'attribute')

    def __str__(self):
        return f"{self.service.title_tm} – {self.attribute.name_tm}"

    @property
    def value(self):
        input_type = self.attribute.input_type

        if input_type == 'text':
            lang = translation.get_language()
            if lang == "ru":
                return self.value_text_ru
            elif lang == "en":
                return self.value_text_en
            return self.value_text_tm

        elif input_type == 'number':
            return self.value_number
        elif input_type == 'boolean':
            return self.value_boolean
        return None

    @value.setter
    def value(self, val):
        self.value_text_tm = None
        self.value_text_ru = None
        self.value_text_en = None
        self.value_number = None
        self.value_boolean = None

        input_type = self.attribute.input_type

        if input_type == 'text':
            lang = translation.get_language()
            if lang == "ru":
                self.value_text_ru = str(val)
            elif lang == "en":
                self.value_text_en = str(val)
            else:
                self.value_text_tm = str(val)

        elif input_type == 'number':
            self.value_number = float(val)
        elif input_type == 'boolean':
            self.value_boolean = bool(val)
