from django.urls import path
from .views import PageDetailView

app_name = 'core'

urlpatterns = [
    path('page/<slug:slug>/', PageDetailView.as_view(), name='page_detail'),
] 