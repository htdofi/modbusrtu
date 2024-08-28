from django.urls import path

from . import views
from django.views.generic import TemplateView

app_name="modbusrtu"

urlpatterns = [
    path('', views.index, name='index'),
    path('get_serial_ports/', views.get_serial_ports, name='get_serial_ports'),
    path('toggle_connection/', views.toggle_connection, name='toggle_connection'),
    path('command_page/', views.command_page, name='send_command'),  # 发送命令的端点
]