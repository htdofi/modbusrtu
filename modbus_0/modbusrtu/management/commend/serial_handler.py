from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
import serial
import datetime
from background_task import background
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import asyncio
import logging
from channels.generic.websocket import WebsocketConsumer

logger = logging.getLogger(__name__)


class ModbusHandler:
    def __init__(self):
        self.sync_task = None
        self.channel_layer = None
        self.client = None
        self.serial_connected = False

    def set_client(self, client):
        self.client = client

    def get_client(self):
        return self.client

    def get_serial_connected(self):
        return self.serial_connected

    async def notify_frontend_connection_status(self, connected):
        channel_layer = get_channel_layer()
        message = {
            "type": "connection_status",
            "message": {
                "connected": connected
            }
        }
        logger.info(f"Preparing to send message to frontend: {message}")
        try:
            await channel_layer.group_send("modbus_status", message)
            logger.info("Message successfully sent to frontend.")
        except Exception as e:
            logger.error(f"Failed to send message to frontend: {e}")

    async def connect_modbus(self, port, baudrate=9600, timeout=1):
        try:
            self.client = ModbusClient(method='rtu', port=port, baudrate=baudrate, timeout=timeout)
            self.serial_connected = self.client.connect()
            if self.serial_connected:
                self.start_connection_check()  # 连接后启动连接检查
                await self.notify_frontend_connection_status(True)  # 连接成功后通知前端
            else:
                await self.notify_frontend_connection_status(False)  # 连接失败时通知前端
            return self.serial_connected
        except Exception as e:
            print(f"连接失败: {str(e)}")
            self.serial_connected = False
            await self.notify_frontend_connection_status(False)  # 连接失败时通知前端
            return False

    async def disconnect_modbus(self):
        if self.client:
            self.client.close()
            self.client = None
            self.serial_connected = False
            await self.notify_frontend_connection_status(False)
            return True
        return False



    def start_connection_check(self):
        connection_check_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        cache.set(f'connection_check_{connection_check_id}', True, 5)
        asyncio.create_task(self.check1_connection(connection_check_id))  # 启动第一个任务

    async def check1_connection(self, connection_check_id):
        while self.serial_connected and cache.get(f'connection_check_{connection_check_id}'):
            try:
                print("开始检查")
                client = self.get_client()  # 获取线程本地的client
                if client:
                    client.read_holding_registers(address=0, count=1, unit=1)
                    cache.set(f'connection_check_{connection_check_id}', True, 5)
                else:
                    raise Exception("客户端未连接")
            except Exception as e:
                print(f"连接检查失败: {e}")
                await self.handle_connection_loss()
                break
            await asyncio.sleep(2)  # 等待2秒

    async def handle_connection_loss(self):
        print("检测到连接丢失")
        await self.disconnect_modbus()
        await self.notify_frontend_connection_status(False)  # 连接丢失后通知前端
        # 发送自定义的连接丢失消息给前端
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "modbus_status",
            {
                "type": "connection_lost",
                "message": {
                    "connected": False,
                    "reason": "已拔出"
                }
            }
        )

    def send_command(self, command):
        # 实现发送命令到设备的逻辑，并返回结果
        return "Mock response from device"  # 替换为实际实现


