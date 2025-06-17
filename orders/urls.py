from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    path('cart/data/', views.CartDataView.as_view(), name='cart_data'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('create/', views.create_order, name='create_order'),
    path('order/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('order/<int:pk>/success/', views.OrderSuccessView.as_view(), name='order_success'),
    path('payment/callback/', views.PaymentCallbackView.as_view(), name='payment_callback'),
] 