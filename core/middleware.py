from django.conf import settings

class TableNumberMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Получаем номер стола из параметра URL или сессии
        table_number = request.GET.get('table') or request.session.get('table_number')
        
        if table_number:
            try:
                table_number = int(table_number)
                request.table_number = table_number
                request.session['table_number'] = table_number
            except (ValueError, TypeError):
                request.table_number = None
        else:
            request.table_number = None

        response = self.get_response(request)
        return response 