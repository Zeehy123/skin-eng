from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

# Register your models here.

@admin.register(User)
# python decorator that tells django to register the user model in the admin panel
class CustomUserAdmin(UserAdmin):
  # this inherits the existing behavior of UserAdmin allowimg you to customize it
  fieldsets=UserAdmin.fieldsets + (("Role",{"fields":("role",)}),)
# organizes fields on the user editing page into sections. 
# These sections are called fieldsets.then we use the addition to add a new section
# role is the section title, then the field dispplayed inside that section
  add_fieldsets=UserAdmin.add_fieldsets+(("Role",{"fields":("role",)}),)
  # the initail on is to add the role section to exisitng user;s while editing
  # but for add is to add this when creating a new user
  list_display=("username","email","role","is_staff")