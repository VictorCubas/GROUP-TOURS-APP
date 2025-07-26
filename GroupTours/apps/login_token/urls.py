from django.urls import path

from .views import LoginTokenView

urlpatterns = [
    path('/login', LoginTokenView.as_view(), name='login_token'),
]
