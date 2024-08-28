import json
import datetime
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from modbusrtu.management.commend.time_manage import set_main_time,set_interval_time,set_test_time
from modbusrtu.views import get_modbus_handler


class ModbusStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("modbus_status", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("modbus_status", self.channel_name)

    async def connection_status(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'message': message
        }))

    async def connection_lost(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'connection_lost',
            'message': message
        }))

    async def connection_lost(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'sync_time_failed',
            'message': message
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        modbus_handler = get_modbus_handler()
        if not modbus_handler.get_client():
            print("horrible!!!!!!!")

        if message_type == 'set_main_time':
            datetime_data = data.get('datetime')
            response = await set_main_time(datetime_data,modbus_handler)
            await self.send(text_data=json.dumps(response))

        elif message_type == 'set_test_time':
            time = data.get('time')
            response = await set_test_time(time,modbus_handler)
            await self.send(text_data=json.dumps(response))

        elif message_type == 'set_interval_time':
            time = data.get('time')
            response = await set_interval_time(time,modbus_handler)
            await self.send(text_data=json.dumps(response))

