from django.contrib import admin
from django.contrib.gis import admin as admin_gis
from . import models


class SearchRequestAdmin(admin_gis.GISModelAdmin):
    """Defines the look of the model in admin dashboard panel."""
    list_display = ('full_name', 'date_of_birth', 'status', 'location')


admin.site.register(models.SearchRequest, admin_gis.GISModelAdmin)
# SearchRequestAdmin)

admin.site.register(models.Reporter,
                    )

admin.site.register(models.ReporterSearchRequest,
                    )
