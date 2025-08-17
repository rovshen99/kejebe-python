from django.contrib import admin
from .models import Region, City


class CityInline(admin.TabularInline):
    model = City
    extra = 1
    fields = ('name_tm', 'name_ru', 'name_en')
    show_change_link = True


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru', 'name_en')
    search_fields = ('name_tm', 'name_ru', 'name_en')
    ordering = ('name_tm',)
    inlines = [CityInline]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'region', 'name_ru', 'name_en')
    list_filter = ('region',)
    search_fields = ('name_tm', 'name_ru', 'name_en', 'region__name_tm')
    ordering = ('region__name_tm', 'name_tm')
