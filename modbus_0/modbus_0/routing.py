from django.urls import path
from modbusrtu import consumers

websocket_urlpatterns = [
    path('ws/modbus', consumers.ModbusStatusConsumer.as_asgi()),
]
