from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('table/<table_id>/', views.table_detail, name='table_detail'),
    path('api/table/<table_id>/order/new/', views.create_order, name='create_order'),
    path('api/table/<table_id>/orders/', views.table_orders, name='table_orders'),
    path('staff/', views.staff_panel, name='staff_panel'),
    path('staff/api/order/<order_id>/<action>/', views.update_order_status, name='update_order_status'),
    path('staff/api/orders/', views.staff_orders_api, name='staff_orders_api'),
    path('login/', views.login_page, name='login_page'),
    path('logout/', views.logout_view, name='logout'),
    path('api/login/', views.login_api, name='login_api'),
    path('api/register/', views.register_api, name='register_api'),
]
