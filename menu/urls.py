from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.menu_list, name='menu_list'),
    path('category/<int:category_id>/', views.menu_list, name='menu_list_by_category'),
    path('<int:item_id>/', views.menu_detail, name='menu_detail'),
] 