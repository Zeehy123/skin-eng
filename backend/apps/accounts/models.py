from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class User(AbstractUser):
  # AbstractUser gives you everything Django users already have 
  # (username, password hashing, email, permissions) so you only add what’s new.
  class Role(models.TextChoices):
# TextChoices creates a fixed list of allowed values. 
# The first string is stored in the database, the second is the label shown in forms.
    ADMIN="admin","Admin",
    EDITOR="editor","Editor"

  role=models.CharField(max_length=50,choices=Role.choices, default=Role.EDITOR)