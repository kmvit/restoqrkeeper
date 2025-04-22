from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.menu_list, name='menu_list'),
    path('item/<int:item_id>/', views.menu_detail, name='menu_detail'),
] 