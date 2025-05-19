from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, View
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json
import logging
from django.urls import reverse

from .models import Order, OrderItem
from menu.models import MenuItem
from .services.forte_payment import ForteBankPaymentService
from .services.rkeeper_service import RKeeperService
from core.utils import format_price, calculate_order_total, validate_table_number

logger = logging.getLogger(__name__)

class CartView(View):
    template_name = 'orders/cart.html'
    context_object_name = 'cart_items'
    
    def get(self, request):
        cart = request.session.get('cart', {})
        items = []
        total_amount = Decimal('0')

        for item_id, quantity in cart.items():
            try:
                menu_item = MenuItem.objects.get(id=item_id)
                item_total = menu_item.price * Decimal(quantity)
                total_amount += item_total
                items.append({
                    'id': menu_item.id,
                    'name': menu_item.name,
                    'price': menu_item.price,
                    'photo_url': menu_item.photo.url if menu_item.photo else '',
                    'quantity': quantity,
                    'total': item_total
                })
            except MenuItem.DoesNotExist:
                continue
                
        context = {
            'cart_items': items,
            'total_amount': total_amount
        }
        return render(request, self.template_name, context)

@require_POST
def add_to_cart(request):
    try:
        print("Headers:", dict(request.headers))
        print("Request method:", request.method)
        print("Raw body:", request.body)
        print("POST data:", request.POST)
        
        data = json.loads(request.body) if request.body else request.POST
        print("Parsed data:", data)
        
        item_id = str(data.get('item_id'))  # Преобразуем в строку
        quantity = int(data.get('quantity', 1))
        
        print(f"Adding item {item_id} to cart with quantity {quantity}")
        
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            print(f"Found menu item: {menu_item.name}, quantity in DB: {menu_item.quantity}")
            
            cart = request.session.get('cart', {})
            current_quantity = int(cart.get(item_id, 0))
            print(f"Current quantity in cart: {current_quantity}")
            
            # Проверяем, не превышает ли количество товара в корзине максимальное количество
            if current_quantity + quantity > menu_item.quantity:
                print(f"Error: Maximum quantity reached. Current: {current_quantity}, Adding: {quantity}, Max: {menu_item.quantity}")
                return JsonResponse({
                    'success': False,
                    'message': 'Достигнуто максимальное количество товара'
                }, status=400)
            
            # Добавляем к существующему количеству в корзине
            cart[item_id] = current_quantity + quantity
            print(f"New quantity in cart: {cart[item_id]}")
                
            request.session['cart'] = cart
            total_count = sum(int(value) for value in cart.values())
            
            return JsonResponse({
                'success': True,
                'message': f'Товар добавлен в корзину',
                'count': total_count
            })
        except MenuItem.DoesNotExist:
            print(f"Error: Menu item {item_id} not found")
            return JsonResponse({
                'success': False,
                'message': 'Товар не найден'
            }, status=404)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'Неверный формат данных'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Внутренняя ошибка сервера: {str(e)}'
        }, status=500)

@require_POST
def update_cart_item(request):
    try:
        data = json.loads(request.body) if request.body else request.POST
        item_id = str(data.get('item_id'))
        quantity = int(data.get('quantity', 1))
        
        print(f"Updating item {item_id} in cart to quantity {quantity}")
        
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            print(f"Found menu item: {menu_item.name}, quantity in DB: {menu_item.quantity}")
            
            # Проверяем, не превышает ли запрошенное количество максимальное
            if quantity > menu_item.quantity:
                print(f"Error: Maximum quantity exceeded. Requested: {quantity}, Max: {menu_item.quantity}")
                return JsonResponse({
                    'success': False,
                    'message': 'Превышено максимальное количество товара'
                }, status=400)
            
            cart = request.session.get('cart', {})
            
            # Если товар есть в корзине, обновляем его количество
            if item_id in cart:
                cart[item_id] = quantity
                request.session['cart'] = cart
                total_count = sum(int(value) for value in cart.values())
                
                return JsonResponse({
                    'success': True,
                    'message': 'Количество товара обновлено',
                    'count': total_count
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Товар не найден в корзине'
                }, status=404)
                
        except MenuItem.DoesNotExist:
            print(f"Error: Menu item {item_id} not found")
            return JsonResponse({
                'success': False,
                'message': 'Товар не найден'
            }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'message': 'Неверный формат данных'
        }, status=400)

@require_POST
def remove_from_cart(request):
    try:
        data = json.loads(request.body) if request.body else request.POST
        item_id = str(data.get('item_id'))
        
        cart = request.session.get('cart', {})
        
        if item_id in cart:
            del cart[item_id]
            request.session['cart'] = cart
            total_count = sum(int(value) for value in cart.values())
            
            return JsonResponse({
                'success': True,
                'message': 'Товар удален из корзины',
                'count': total_count
            })
        
        return JsonResponse({
            'success': False,
            'message': 'Товар не найден в корзине'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'message': 'Неверный формат данных'
        }, status=400)

def cart_count(request):
    cart = request.session.get('cart', {})
    total_count = sum(int(value) for value in cart.values())
    return JsonResponse({'count': total_count})

class CartDataView(View):
    def get(self, request):
        cart = request.session.get('cart', {})
        items = []
        total_amount = Decimal('0')

        for item_id, quantity in cart.items():
            try:
                menu_item = MenuItem.objects.get(id=item_id)
                item_total = menu_item.price * Decimal(quantity)
                total_amount += item_total
                items.append({
                    'id': menu_item.id,
                    'name': menu_item.name,
                    'price': str(menu_item.price),
                    'photo_url': menu_item.photo.url if menu_item.photo else '',
                    'quantity': quantity,
                    'total': str(item_total)
                })
            except MenuItem.DoesNotExist:
                continue
                
        return JsonResponse({
            'items': items,
            'total_amount': str(total_amount),
            'count': sum(int(value) for value in cart.values())
        })

class CheckoutView(ListView):
    template_name = 'orders/checkout.html'
    context_object_name = 'items'

    def get_queryset(self):
        cart = self.request.session.get('cart', {})
        items = []
        
        for item_id, quantity in cart.items():
            try:
                menu_item = MenuItem.objects.get(id=item_id)
                item_total = menu_item.price * Decimal(quantity)
                items.append({
                    'id': menu_item.id,
                    'name': menu_item.name,
                    'price': menu_item.price,
                    'quantity': quantity,
                    'total': item_total,
                    'photo_url': menu_item.photo.url if menu_item.photo else ''
                })
            except MenuItem.DoesNotExist:
                continue
                
        return items

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = context['items']
        total_amount = sum(item['total'] for item in items)
        context['total_amount'] = total_amount
        return context

@require_POST
def create_order(request):
    # Получаем данные корзины из сессии
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.error(request, 'Корзина пуста')
        return redirect('orders:cart')
    
    # Создаем заказ
    items = []
    total_amount = Decimal('0')
    
    for item_id, quantity in cart.items():
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            item_total = menu_item.price * Decimal(quantity)
            total_amount += item_total
            items.append({
                'menu_item': menu_item,
                'quantity': quantity,
                'price': menu_item.price,
                'total': item_total
            })
        except MenuItem.DoesNotExist:
            continue
            
    if not items:
        messages.error(request, 'Нет доступных товаров')
        return redirect('orders:cart')
    
    comment = request.POST.get('comment', '')
    
    # Создаем заказ в базе данных
    order = Order.objects.create(
        table_number=request.session.get('table_number'),
        station_id=request.session.get('station_code'),  # Сохраняем ID станции
        total_amount=total_amount,
        status='new',  # Устанавливаем статус 'new' вместо ожидания оплаты
        comment=comment
    )
    
    # Создаем позиции заказа
    for item in items:
        comment = request.POST.get(f'comment_{item["menu_item"].id}', '')
        
        OrderItem.objects.create(
            order=order,
            menu_item=item['menu_item'],
            quantity=item['quantity'],
            price=item['price'],
            total=item['total'],
            comment=comment
        )
    
    # Отправляем заказ в R-Keeper
    try:
        rkeeper_service = RKeeperService()
        rkeeper_order_id = rkeeper_service.send_order(order)
        if rkeeper_order_id:
            order.rkeeper_order_id = rkeeper_order_id
            order.status = 'processing'
            order.save()
            logger.info(f"Заказ #{order.id} успешно отправлен в R-Keeper")
        else:
            logger.error(f"Не удалось отправить заказ #{order.id} в R-Keeper")
    except Exception as e:
        logger.error(f"Ошибка при отправке заказа в R-Keeper: {e}")
    
    # Очищаем корзину
    request.session['cart'] = {}
    
    # Перенаправляем на страницу успешного оформления заказа с параметрами станции и стола
    station = order.station_id or request.session.get('station_code')
    table = order.table_number or request.session.get('table_number')
    success_url = reverse('orders:order_success', kwargs={'pk': order.pk}) + f'?station_id={station}&table={table}'
    return redirect(success_url)

class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = context['order']
        context['formatted_total'] = format_price(order.total_amount)
        return context

@method_decorator(csrf_exempt, name='dispatch')
class PaymentCallbackView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            payment_id = data.get('payment_id')
            status = data.get('status')
            
            if not payment_id or not status:
                return JsonResponse({'error': 'Missing payment_id or status'}, status=400)
            
            order = Order.objects.get(payment_id=payment_id)
            
            if status == 'success':
                order.status = 'paid'
                order.save()
                
                # Отправка заказа в R-Keeper
                rkeeper_service = RKeeperService()
                try:
                    rkeeper_order_id = rkeeper_service.send_order(order)
                    if rkeeper_order_id:
                        order.rkeeper_order_id = rkeeper_order_id
                        order.status = 'processing'
                        order.save()
                        logger.info(f"Заказ #{order.id} успешно отправлен в R-Keeper")
                    else:
                        logger.error(f"Не удалось отправить заказ #{order.id} в R-Keeper")
                except Exception as e:
                    logger.error(f"Ошибка при отправке заказа в R-Keeper: {e}")
                
                return JsonResponse({'status': 'success'})
            else:
                order.status = 'failed'
                order.save()
                return JsonResponse({'status': 'failed'})
                
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class OrderSuccessView(DetailView):
    model = Order
    template_name = 'orders/order_success.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
