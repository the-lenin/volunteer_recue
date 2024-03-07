from django.contrib import admin
from . import models


class SearchRequestAdmin(admin.ModelAdmin):
    """Defines the look of the model in admin dashboard panel."""
    list_display = ('full_name', 'date_of_birth', 'status', 'location')


admin.site.register(models.SearchRequest,)
# SearchRequestAdmin)

admin.site.register(models.Reporter,
                    )

admin.site.register(models.ReporterSearchRequest,
                    )
