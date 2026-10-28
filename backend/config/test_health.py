import pytest
from rest_framework.test import APIClient


# The first test calls the API without logging in, 
# which proves the public opt-out works.
def test_health_is_public():
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
# @pytest.mark.django_db gives a test access to a temporary database that’s thrown away afterwards,
# so tests never touch your real data.
def test_new_user_defaults_to_editor(django_user_model):
    user = django_user_model.objects.create_user(username="ada", password="x12345678")
    assert user.role == "editor"
# django_user_model is a fixture that returns your custom User, 
# so the test follows AUTH_USER_MODEL automatically.
