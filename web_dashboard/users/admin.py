from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
# from .forms import CustomUserChangeForm
from django.utils.translation import gettext_lazy as _


class CustomUserAdmin(UserAdmin):
    """
    CustomUserAdmin determines which fields and how they
    displayed in Django Admin dashboard.
    """
    model = CustomUser
#    form = CustomUserChangeForm
#    add_form = CustomUserCreationForm

    list_display = (
         'username',
         'full_name',
         'email',
         'phone_number',
         'has_car',
         'is_active',
    )

    list_filter = (
        'has_car',
        'groups'
    )

    fieldsets = (
        (_('Details'), {
            "fields": (
                'username',
                "password1",
                "password2",
                'nickname',
                "first_name",
                "last_name",
                "patronymic_name",
                'dateofbirth',
                "email",
                "phone_number",
                'telegram_id',
                "address",
                'has_car',
                'comment'
             )
        }),
        (_("Permissions"), {
            "fields": (
                "groups",
                "user_permissions",
                "is_staff",
                "is_active",
            )
        }),
    )

    add_fieldsets = fieldsets
    search_fields = (
        'username',
        'first_name',
        'last_name',
        'patronymic_name',
        'dateofbirth',
        'nickname',
        'email',
        'phone_number',
        'address',
        'comment',
    )

    ordering = (
        'email',
    )


admin.site.register(CustomUser, CustomUserAdmin)
