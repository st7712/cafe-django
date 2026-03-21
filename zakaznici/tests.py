from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from .models import Table, Drink, DrinkType, Order, StaffUser
from django.test import Client
from django.utils import timezone
from datetime import timedelta

class TestModels(TestCase):
    def setUp(self):
        self.table = Table.objects.create(number=1, seats=4)
        self.drink = Drink.objects.create(name="Káva", price=50.00)
        self.drink_type = DrinkType.objects.create(name="Espresso", drink=self.drink)
        self.order = Order.objects.create(table=self.table, drink=self.drink, drink_type=self.drink_type)

    def test_table_str(self):
        self.assertTrue(isinstance(self.table, Table))
        self.assertEqual(str(self.table), "Stůl 1 (4 míst)")

    def test_drink_str(self):
        self.assertTrue(isinstance(self.drink, Drink))
        self.assertEqual(str(self.drink), "Káva (50.0 Kč)")

    def test_drink_type_str(self):
        self.assertTrue(isinstance(self.drink_type, DrinkType))
        self.assertEqual(str(self.drink_type), "Káva - Espresso")

    def test_order_str(self):
        self.assertTrue(isinstance(self.order, Order))
        self.assertEqual(str(self.order), "Stůl 1: Káva (Espresso) - NEW")

class TestViews(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.table = Table.objects.create(number=3, seats=4)
        self.drink = Drink.objects.create(name="Limonáda", price=40.00)
        self.order = Order.objects.create(table=self.table, drink=self.drink)     
        
        self.staff_user = StaffUser.objects.create(
            username='admin',
            password=make_password('secret')
        )
        
    def test_index_GET(self):
        response = self.client.get(reverse('index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/staff pro personál")
        
    def test_table_detail_GET(self):
        response = self.client.get(reverse('table_detail', args=[self.table.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"<span class=\"text-primary\">{self.table.number}</span>") # Očekáváme, že číslo stolu bude zobrazeno v HTML s touto strukturou
        self.assertTemplateUsed(response, 'table_detail.html')
    
    def test_create_order_POST(self):        
        response = self.client.post(reverse('create_order', args=[self.table.id]), {
            'drink_id': self.drink.id,
            'drink_type_id': ''
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.filter(table=self.table, drink=self.drink).exists())
        self.assertEqual(Order.objects.filter(table=self.table, drink=self.drink).count(), 2)  # Zde bychom nyní měli mít 2 objednávky stejného nápoje pro tento stůl
    
    def test_create_order_invalid_drink_POST(self):
        response = self.client.post(reverse('create_order', args=[self.table.id]), {
            'drink_id': 9999,  # Neexistující ID nápoje
            'drink_type_id': ''
        })
        
        self.assertEqual(response.status_code, 404)  # Očekáváme 404 Not Found pro neexistující nápoj (kvůli get_object_or_404 dostaneme 404 a webovou stránku s chybou)
    
    def test_create_order_no_drink_POST(self):
        response = self.client.post(reverse('create_order', args=[self.table.id]), {
            'drink_id': '',  # Žádný nápoj není vybrán
            'drink_type_id': ''
        })
        
        self.assertEqual(response.status_code, 400)  # Očekáváme 400 Bad Request, protože drink_id je povinné
        self.assertEqual(response.json().get('error'), "Nápoj není vybrán")
        
    def test_create_order_wrong_method_GET(self):
        response = self.client.get(reverse('create_order', args=[self.table.id]))  # GET místo POST
        
        self.assertEqual(response.status_code, 405)  # Očekáváme 405 Method Not Allowed
    
    def test_table_orders_GET(self):
        response = self.client.get(reverse('table_orders', args=[self.table.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('orders', response.json())
        self.assertEqual(len(response.json()['orders']), 1)
        self.assertEqual(response.json()['orders'][0]['drink_name'], "Limonáda")
        self.assertEqual(response.json()['orders'][0]['drink_name'], self.drink.name)
    
    def test_staff_unauthorized_GET(self):
        response = self.client.get(reverse('staff_panel'))
        
        self.assertEqual(response.status_code, 302)  # Očekáváme přesměrování na login
        self.assertIn(reverse('login_page'), response.url)
    
    def test_staff_orders_api_unauthorized_GET(self):
        response = self.client.get(reverse('staff_orders_api'))
        
        self.assertEqual(response.status_code, 401)  # Očekáváme 401 Unauthorized
        
    def test_update_order_status_unauthorized_POST(self):        
        response = self.client.post(reverse('update_order_status', args=[self.order.id, 'accept']))
        
        self.assertEqual(response.status_code, 401)  # Očekáváme 401 Unauthorized

    def test_staff_authorized_GET(self):
        # Nastavíme cookie
        self.client.cookies['auth_token'] = self.staff_user.token
        
        response = self.client.get(reverse('staff_panel'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff_panel.html')
    
    def test_staff_orders_api_authorized_GET(self):
        response = self.client.get(reverse('staff_orders_api'), headers={'X-Auth-Token': self.staff_user.token}, data={})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('new', response.json())
        self.assertEqual(len(response.json()['new']), 1)
        
    def test_staff_update_order_status_authorized_POST(self):
        response = self.client.post(reverse('update_order_status', args=[self.order.id, 'finish']), headers={'X-Auth-Token': self.staff_user.token})
        
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.FINISHED)
        
    def test_staff_delete_order_status_authorized_POST(self):
        order_to_delete = Order.objects.create(table=self.table, drink=self.drink, status=Order.Status.FINISHED)

        response = self.client.post(reverse('update_order_status', args=[order_to_delete.id, 'delete']), headers={'X-Auth-Token': self.staff_user.token})
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(id=order_to_delete.id).exists())
        
    def test_login_api_POST(self):
        response = self.client.post(reverse('login_api'), data={
            'username': 'admin',
            'password': 'secret'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())
        self.assertTrue(StaffUser.objects.filter(username='admin', token=response.json()['token']).exists())
    
    def test_login_api_invalid_credentials_POST(self):
        response = self.client.post(reverse('login_api'), data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.json())
        self.assertEqual(response.json()['error'], "Neplatné údaje")

class TestOrderTimeLimits(TestCase):
    def setUp(self):        
        self.client = Client()
        
        self.table = Table.objects.create(number=3, seats=4)
        self.drink = Drink.objects.create(name="Limonáda", price=40.00)
        self.order = Order.objects.create(table=self.table, drink=self.drink)     
        
        self.staff_user = StaffUser.objects.create(
            username='admin',
            password=make_password('secret')
        )
        
    def test_order_time_limits(self):
        # Simulujeme, že objednávka byla vytvořena před 11 minutami
        self.order.created_at -= timedelta(minutes=11)
        self.order.save()
        
        self.order.check_time_limits()
        self.order.refresh_from_db()
        
        self.assertEqual(self.order.status, Order.Status.MISSED)
    
    def test_order_time_limits_accepted(self):
        # Nejprve přijmeme objednávku
        self.order.status = Order.Status.ACCEPTED
        self.order.accepted_at = timezone.now() - timedelta(minutes=16)  # Simulujeme, že byla přijata před 16 minutami
        self.order.save()
        
        self.order.check_time_limits()
        self.order.refresh_from_db()
        
        self.assertEqual(self.order.status, Order.Status.MISSED_DEADLINE)
    
    def test_order_time_limits_no_change(self):
        # Simulujeme, že objednávka byla vytvořena před 5 minutami
        self.order.created_at -= timedelta(minutes=5)
        self.order.save()
        
        self.order.check_time_limits()
        self.order.refresh_from_db()
        
        self.assertEqual(self.order.status, Order.Status.NEW)
    
    def test_order_time_limits_accepted_no_change(self):
        # Nejprve přijmeme objednávku
        self.order.status = Order.Status.ACCEPTED
        self.order.accepted_at = timezone.now() - timedelta(minutes=10)  # Simulujeme, že byla přijata před 10 minutami
        self.order.save()
        
        self.order.check_time_limits()
        self.order.refresh_from_db()
        
        self.assertEqual(self.order.status, Order.Status.ACCEPTED)
    
    def test_order_time_limits_using_api_GET(self):
        Order.objects.filter(id=self.order.id).update(created_at=timezone.now() - timedelta(minutes=11)) # Simulujeme, že objednávka byla vytvořena před 11 minutami
        
        response = self.client.get(reverse('staff_orders_api'), headers={'X-Auth-Token': self.staff_user.token}) # Získáme seznam objednávek přes API, což by mělo spustit kontrolu časových limitů a aktualizovat stav objednávky
        self.assertEqual(response.status_code, 200)
        
        order = Order.objects.get(id=self.order.id) # Znovu načteme objednávku z databáze, abychom získali aktualizovaný stav
        self.assertEqual(order.status, Order.Status.MISSED)
        
        # Ověříme, že v JSONu je ve správné sekci (history)
        data = response.json()
        
        self.assertTrue(len(data["history"]) > 0) # Očekáváme, že v historii bude alespoň jedna objednávka
        self.assertEqual(data["history"][0]['id'], str(self.order.id))
    
    def test_order_time_limits_accepted_using_api_GET(self):
        Order.objects.filter(id=self.order.id).update(status=Order.Status.ACCEPTED, accepted_at=timezone.now() - timedelta(minutes=16))  # Simulujeme, že objednávka byla přijata před 16 minutami
        
        response = self.client.get(reverse('staff_orders_api'), headers={'X-Auth-Token': self.staff_user.token}) # Získáme seznam objednávek přes API, což by mělo spustit kontrolu časových limitů a aktualizovat stav objednávky
        self.assertEqual(response.status_code, 200)
        
        order = Order.objects.get(id=self.order.id) # Znovu načteme objednávku z databáze, abychom získali aktualizovaný stav
        self.assertEqual(order.status, Order.Status.MISSED_DEADLINE)
        
        # Ověříme, že v JSONu je ve správné sekci (history)
        data = response.json()
        
        self.assertTrue(len(data["history"]) > 0) # Očekáváme, že v historii bude alespoň jedna objednávka
        self.assertEqual(data["history"][0]['id'], str(self.order.id))