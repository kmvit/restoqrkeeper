from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, View
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json
import logging
from django.urls import reverse

from .models import Order, OrderItem, Waiter, Table
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
    table_number = request.session.get('table_number')
    
    # Получаем объект стола
    table = None
    if table_number:
        try:
            table = Table.objects.get(number=table_number, is_active=True)
        except Table.DoesNotExist:
            logger.warning(f"Не найден активный стол с номером {table_number}")
    
    # Создаем заказ в базе данных
    order = Order.objects.create(
        table=table,
        station_id=request.session.get('station_code'),
        waiter=table.waiter if table else None,
        total_amount=total_amount,
        status='new',
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
    
    # Создаем платеж в ForteBank
    try:
        payment_service = ForteBankPaymentService()
        payment_data = payment_service.create_payment(order)
        
        # Сохраняем payment_id в заказе
        order.payment_id = payment_data.get('order_id')
        order.save()
        
        # Очищаем корзину
        request.session['cart'] = {}
        
        # Перенаправляем на платежный виджет ForteBank
        return redirect(payment_data.get('payment_url'))
        
    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        messages.error(request, 'Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже.')
        return redirect('orders:cart')

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
        return self._handle_callback(request)
        
    def get(self, request, *args, **kwargs):
        return self._handle_callback(request)
        
    def _handle_callback(self, request):
        """
        Обработчик callback'а от платежной системы ForteBank.
        Обрабатывает как POST, так и GET запросы.
        """
        logger.info(f"Received payment callback. Method: {request.method}")
        
        try:
            if request.method == "POST":
                data = json.loads(request.body)
            else:  # GET request
                data = request.GET.dict()
                
            logger.info(f"Payment callback data: {data}")
            
            # Получаем ID и статус из данных ForteBank
            payment_id = data.get('ID') or data.get('id')
            status = data.get('STATUS') or data.get('status')
            
            if not payment_id or not status:
                logger.error("Missing ID or STATUS in callback data")
                return JsonResponse({'error': 'Missing ID or STATUS'}, status=400)
                
            try:
                order = Order.objects.get(payment_id=payment_id)
            except Order.DoesNotExist:
                logger.error(f"Order with payment_id {payment_id} not found")
                return JsonResponse({'error': 'Order not found'}, status=404)
                
            # Обновляем статус заказа в зависимости от статуса платежа
            if status in ['FullyPaid', 'Completed', 'Success']:
                # Сначала обновляем статус на 'paid'
                order.status = 'paid'
                order.save()
                logger.info(f"Order {order.id} marked as paid")
                
                # Затем отправляем заказ в R-Keeper
                try:
                    rkeeper_service = RKeeperService()
                    success = rkeeper_service.send_order(order)
                    
                    if success:
                        # Только после успешной отправки в R-Keeper меняем статус на 'processing'
                        order.status = 'processing'
                        order.save()
                        logger.info(f"Order {order.id} successfully sent to R-Keeper and marked as processing")
                    else:
                        logger.error(f"Failed to send order {order.id} to R-Keeper")
                except Exception as e:
                    logger.error(f"Error sending order to R-Keeper: {str(e)}", exc_info=True)
                    
            elif status in ['Cancelled', 'Canceled']:
                order.status = 'cancelled'
                order.save()
                logger.info(f"Order {order.id} cancelled")
                
            elif status in ['Failed', 'Error', 'Rejected']:
                order.status = 'failed'
                order.save()
                logger.info(f"Order {order.id} payment failed")
            
            # Если это GET запрос, делаем редирект на главную страницу
            if request.method == "GET":
                return redirect('home')  # Предполагается, что у вас есть URL с именем 'home'
            
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON in callback data")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error processing payment callback: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)

class OrderSuccessView(DetailView):
    model = Order
    template_name = 'orders/order_success.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
