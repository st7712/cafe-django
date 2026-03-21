from django.shortcuts import render, get_object_or_404, HttpResponse, redirect
from .models import Table, Drink, Order, DrinkType, StaffUser
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_POST
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
import json

def get_auth_staff(request):
    """Hledá uživatelský token v různých místech a vrací odpovídající StaffUser objekt, nebo None pokud není nalezen"""
    token = None
    
    if request.COOKIES.get('auth_token'):
        token = request.COOKIES.get('auth_token')
        
    if not token and request.headers.get('X-Auth-Token'):
        token = request.headers.get('X-Auth-Token')
    
    if not token:
        return None
    
    try:
        return StaffUser.objects.get(token=token)
    except StaffUser.DoesNotExist:
        return None
# --- Webové stránky ---

def index(request):
    return HttpResponse("/staff pro personál, /table/id pro zákazníky")

def table_detail(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    orders = table.orders.all().order_by('-created_at')
    
    drinks = Drink.objects.all()
    
    drinks_data = {}
    for drink in drinks:
        # Získáme všechny typy pro tento drink
        types = list(drink.types.values('id', 'name'))
        drinks_data[drink.id] = types

    # Převedeme na JSON string
    drinks_data_json = json.dumps(drinks_data)

    context = {
        'table': table,
        'orders': orders,
        'drinks': drinks,
        'drinks_data_json': drinks_data_json, # Posíláme do šablony
    }
    return render(request, 'table_detail.html', context)

def login_page(request):
    if request.COOKIES.get('auth_token'):
         if StaffUser.objects.filter(token=request.COOKIES.get('auth_token')).exists():
             return redirect('staff_panel')
    return render(request, 'login.html')

def staff_panel(request):
    user = get_auth_staff(request)
    
    if not user:
        return redirect('login_page')
    
    tables = Table.objects.all()
    return render(request, 'staff_panel.html', {'tables': tables, 'user': user})

# --- Zákazník API endpointy ---

def table_orders(request, table_id):
    """
    Pomocný endpoint, který vrací seznam objednávek v JSONu.
    """
    table = get_object_or_404(Table, id=table_id)
    orders = table.orders.all().order_by('-created_at')
    
    data = []
    for order in orders:
        order.check_time_limits()

        # Sestavíme objekt pro JSON
        data.append({
            'id': order.id,
            'drink_name': order.drink.name,
            'type_name': order.drink_type.name if order.drink_type else None,
            'status': order.status,                 # Např. 'ACCEPTED' (pro CSS třídu)
            'status_display': order.get_status_display(), # Např. 'Přijatá' (pro text)
            'created_time': order.created_at.strftime('%H:%M'),
            'ago': timesince(order.created_at),     # Django funkce 'před X minutami'
        })
    
    return JsonResponse({'orders': data})

@require_POST
def create_order(request, table_id):
    if request.method == 'POST':
        drink_id = request.POST.get('drink_id')
        drink_type_id = request.POST.get('drink_type_id')

        table = get_object_or_404(Table, id=table_id)
        
        if drink_id:
            drink = get_object_or_404(Drink, id=drink_id)
            drink_type = get_object_or_404(DrinkType, id=drink_type_id) if drink_type_id else None
    
            Order.objects.create(table=table, drink=drink, drink_type=drink_type, status=Order.Status.NEW)
            return JsonResponse({"message": "Objednávka vytvořena", "status": "success"}, status=201)
        return JsonResponse({"error": "Nápoj není vybrán"}, status=400)
    return JsonResponse({"error": "Neplatná metoda"}, status=405)

# -- staff API endpointy ---

def staff_orders_api(request):
    user = get_auth_staff(request)
    token = user.token if user else None
    
    if not user or not token or not StaffUser.objects.filter(token=token).exists():
        return JsonResponse({'error': 'Neautorizováno'}, status=401)
    
    orders = Order.objects.all().order_by('created_at')
    
    for order in orders:
        order.check_time_limits()

    data = {
        'new': [],
        'accepted': [],
        'history': []
    }

    now = timezone.now()

    for order in orders:
        # Vypočteme deadline pro odpočet
        remaining_seconds = 0
        
        if order.status == Order.Status.NEW:
            deadline_dt = order.created_at + timedelta(minutes=10)
            remaining_seconds = (deadline_dt - now).total_seconds()
            bucket = 'new'
            
        elif order.status == Order.Status.ACCEPTED:
            deadline_dt = order.accepted_at + timedelta(minutes=15) if order.accepted_at else now
            remaining_seconds = (deadline_dt - now).total_seconds()
            bucket = 'accepted'
            
        else:
            # Vše ostatní jde do historie
            bucket = 'history'
        
        # Sestavení objektu
        item = {
            'id': order.id,
            'table_number': order.table.number,
            'table_id': order.table.id,
            'drink_name': order.drink.name,
            'type_name': order.drink_type.name if order.drink_type else '',
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': order.created_at.strftime('%H:%M'),
            'remaining_seconds': remaining_seconds,
        }

        # Přidání do správného seznamu
        if bucket == 'history':
            data['history'].append(item)
        elif bucket == 'new':
            data['new'].append(item)
        elif bucket == 'accepted':
            data['accepted'].append(item)

    # SEŘAZENÍ HISTORIE (Propáslé/nestihnuté nahoře, Dokončené dole)
    # Priorita: MISSED/DEADLINE (0), REJECTED (1), FINISHED (2)
    def history_sort_key(item):
        s = item['status']
        if 'MISSED' in s: 
            return 0
        if s == 'REJECTED': 
            return 1
        return 2 # FINISHED
    
    data['history'].sort(key=history_sort_key)

    return JsonResponse(data)

@require_POST
def update_order_status(request, order_id, action):
    user = get_auth_staff(request)
    token = user.token if user else None
    
    if not user or not token or not StaffUser.objects.filter(token=token).exists():
        return JsonResponse({'error': 'Neautorizováno'}, status=401)
    
    order = get_object_or_404(Order, id=order_id)
    
    if action == 'accept':
        order.status = Order.Status.ACCEPTED
        order.accepted_at = timezone.now()
        order.save()
        
    elif action == 'finish':
        order.status = Order.Status.FINISHED
        order.save()
        
    elif action == 'reject':
        order.status = Order.Status.REJECTED
        order.save()
        
    elif action == 'delete':
        order.delete()
        return JsonResponse({'status': 'deleted'})

    else:
        return JsonResponse({'error': 'Neznámá akce'}, status=400)
        
    return JsonResponse({'status': 'ok'})

@csrf_exempt
def register_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if StaffUser.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Uživatel již existuje'}, status=409)
            
            # Vytvoření uživatele
            user = StaffUser(username=username, password=make_password(password))
            user.save()
            
            return JsonResponse({'token': user.token, 'message': 'Registrace úspěšná'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            try:
                user = StaffUser.objects.get(username=username)
            except StaffUser.DoesNotExist:
                return JsonResponse({'error': 'Neplatné údaje'}, status=401)
            
            # Kontrola hashe
            if check_password(password, user.password):
                return JsonResponse({'token': user.token, 'message': 'Login OK'}, status=200)
            else:
                return JsonResponse({'error': 'Neplatné údaje'}, status=401)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def logout_view(request):
    response = redirect('login_page')
    response.delete_cookie('auth_token')
    return response