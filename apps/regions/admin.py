from django.contrib import admin
from .models import Region, City


class CityInline(admin.TabularInline):
    model = City
    extra = 1
    fields = ('name_tm', 'name_ru', 'is_region_level')
    show_change_link = True


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru')
    search_fields = ('name_tm', 'name_ru')
    ordering = ('name_tm',)
    inlines = [CityInline]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'region', 'name_ru', 'is_region_level')
    list_filter = ('region', 'is_region_level')
    search_fields = ('name_tm', 'name_ru', 'region__name_tm')
    ordering = ('region__name_tm', 'name_tm')
