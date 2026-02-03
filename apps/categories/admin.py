from django import http
from django.contrib import admin, messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.db import IntegrityError, transaction
from image_cropping import ImageCroppingMixin
from mptt.admin import DraggableMPTTAdmin
from mptt.exceptions import InvalidMove
from .models import Category
from django.utils.translation import gettext_lazy as _


@admin.register(Category)
class CategoryAdmin(ImageCroppingMixin, DraggableMPTTAdmin):
    mptt_indent_field = "name_tm"
    list_display = (
        'tree_actions',
        'indented_title',
        'slug',
        'priority',
        'parent',
        'has_image',
        'has_icon',
    )
    list_display_links = ('indented_title',)
    list_filter = ('parent',)
    search_fields = ('name_tm', 'name_ru', 'slug')
    prepopulated_fields = {'slug': ('name_tm',)}
    ordering = ('priority',)

    def indented_title(self, instance):
        return instance.name_tm
    indented_title.short_description = _("Name (TM)")

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = _("Image")

    def has_icon(self, obj):
        return bool(obj.icon)
    has_icon.boolean = True
    has_icon.short_description = _("Icon")

    @transaction.atomic
    def _move_node(self, request):
        position = request.POST.get("position")
        if position not in ("last-child", "left", "right"):
            self.message_user(
                request,
                _("Did not understand moving instruction."),
                level=messages.ERROR,
            )
            return http.HttpResponse("FAIL, unknown instruction.")

        queryset = self.get_queryset(request)
        try:
            cut_item = queryset.get(pk=request.POST.get("cut_item"))
            pasted_on = queryset.get(pk=request.POST.get("pasted_on"))
        except (self.model.DoesNotExist, TypeError, ValueError):
            self.message_user(
                request, _("Objects have disappeared, try again."), level=messages.ERROR
            )
            return http.HttpResponse("FAIL, invalid objects.")

        if not self.has_change_permission(request, cut_item):
            self.message_user(request, _("No permission"), level=messages.ERROR)
            return http.HttpResponse("FAIL, no permission.")

        data_before_update = self.get_data_before_update(request, cut_item, pasted_on)
        mptt_opts = self.model._mptt_meta
        parent_attr = mptt_opts.parent_attr
        old_parent_id = getattr(cut_item, f"{parent_attr}_id")

        try:
            self.model._tree_manager.move_node(cut_item, pasted_on, position)
        except InvalidMove as e:
            self.message_user(request, "%s" % e, level=messages.ERROR)
            return http.HttpResponse("FAIL, invalid move.")
        except IntegrityError as e:
            self.message_user(
                request, _("Database error: %s") % e, level=messages.ERROR
            )
            raise

        new_parent_id = getattr(cut_item, f"{parent_attr}_id")
        self._sync_priority(parent_attr, old_parent_id)
        if new_parent_id != old_parent_id:
            self._sync_priority(parent_attr, new_parent_id)

        change_message = self.get_move_node_change_message(
            request, cut_item, pasted_on, data_before_update
        )

        LogEntry.objects.log_actions(
            user_id=request.user.pk,
            queryset=[cut_item],
            action_flag=CHANGE,
            change_message=change_message,
            single_object=True,
        )
        self.message_user(request, _("%s has been successfully moved.") % cut_item)
        return http.HttpResponse("OK, moved.")

    def _sync_priority(self, parent_attr: str, parent_id):
        mptt_opts = self.model._mptt_meta
        ordering = (mptt_opts.tree_id_attr, mptt_opts.left_attr)
        if parent_id is None:
            filter_kwargs = {f"{parent_attr}__isnull": True}
        else:
            filter_kwargs = {f"{parent_attr}_id": parent_id}
        siblings = self.model.objects.filter(**filter_kwargs).order_by(*ordering)
        updates = []
        for index, obj in enumerate(siblings, start=1):
            if obj.priority != index:
                obj.priority = index
                updates.append(obj)
        if updates:
            self.model.objects.bulk_update(updates, ["priority"])
