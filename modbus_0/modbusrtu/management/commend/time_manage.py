import asyncio
import datetime
import logging
from channels.generic.websocket import WebsocketConsumer
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

async def set_main_time(datetime_str,ModbusHandler):
    try:
        # 将收到的datetime字符串转换为datetime对象
        set_time = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # 检查Modbus客户端是否连接
        if not ModbusHandler.get_client() or not ModbusHandler.get_serial_connected():
            return {"status": "error", "message": {"reason": "Modbus客户端未连接"}}
        # 写入时间到设备寄存器
        client=ModbusHandler.get_client()
        client.write_register(0x0005, set_time.year, unit=1)
        client.write_register(0x0006, set_time.month, unit=1)
        client.write_register(0x0007, set_time.day, unit=1)
        client.write_register(0x0008, set_time.hour, unit=1)
        client.write_register(0x0009, set_time.minute, unit=1)
        client.write_register(0x000A, set_time.second, unit=1)
        # 更新当前时间
        ModbusHandler.current_time = set_time
        ModbusHandler.last_update = datetime.datetime.now().timestamp()
        return {"status": "success", "message": "主控时间设置成功"}
    except ValueError as e:
        return {"status": "error", "message": f"时间格式错误: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"设置主控时间失败: {str(e)}"}

async def set_test_time(time,ModbusHandler):
    try:
        time_parts = time.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2])

        client = ModbusHandler.get_client()

        if not client:
            return {"status": "error", "message": "Modbus客户端未连接"}

        client.write_register(0x000C, hour, unit=1)
        client.write_register(0x000D, minute, unit=1)
        client.write_register(0x000E, second, unit=1)

        return {"status": "success", "message": "测试时间设置成功"}
    except Exception as e:
        return {"status": "error", "message": f"设置测试时间失败: {str(e)}"}

async def set_interval_time(time,ModbusHandler):
    try:
        time_parts = time.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2])

        client = ModbusHandler.get_client()

        if not client:
            return {"status": "error", "message": "Modbus客户端未连接"}

        client.write_register(0x000F, hour, unit=1)
        client.write_register(0x0010, minute, unit=1)
        client.write_register(0x0011, second, unit=1)

        return {"status": "success", "message": "间隔时间设置成功"}
    except Exception as e:
        return {"status": "error", "message": f"设置间隔时间失败: {str(e)}"}

def start_periodic_sync_task(ModbusHandler):
    # 获取当前线程的事件循环，如果没有则创建一个新的
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # 直接运行异步任务
    loop.run_until_complete(run_periodic_sync_task(ModbusHandler))
    # 保持事件循环持续运行
    loop.run_forever()


async def run_periodic_sync_task(ModbusHandler):
    # 直接运行并等待异步任务的完成
    await periodic_time_sync(ModbusHandler)

async def periodic_time_sync(ModbusHandler):
    while ModbusHandler.get_client() and ModbusHandler.get_serial_connected():
        try:
            print("开始时间同步...")
            await sync_time_with_device(ModbusHandler)  # 同步设备时间
            print("时间同步完成，等待下一次同步...")
        except Exception as e:
            print(f"时间同步出错: {e}")
        print("等待30秒后继续同步...")  # 这里的日志应该被输出
        await asyncio.sleep(30)


async def sync_time_with_device(ModbusHandler):
    if not ModbusHandler.get_serial_connected():
        await ModbusHandler.channel_layer.group_send(
            "modbus_status",
            {
                "type": "sync_time_failed",
                "message": {
                    "reason": "没法设置时间：串口未连接",
                }
            }
        )
        return False
    try:
        current_time = datetime.datetime.now()
        builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Little)
        builder.add_16bit_uint(current_time.year)
        builder.add_16bit_uint(current_time.month)
        builder.add_16bit_uint(current_time.day)
        builder.add_16bit_uint(current_time.hour)
        builder.add_16bit_uint(current_time.minute)
        builder.add_16bit_uint(current_time.second)
        payload = builder.to_registers()
        ModbusHandler.get_client().write_registers(0x0005, payload, unit=1)
        registers = ModbusHandler.get_client().read_holding_registers(0x0005, 6, unit=1).registers
        year = registers[0]
        month = registers[1]
        day = registers[2]
        hour = registers[3]
        minute = registers[4]
        second = registers[5]
        board_time = datetime.datetime(year, month, day, hour, minute, second)
        board_time_str = board_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{board_time_str}")
        return True
    except ModbusIOException as e:
        print(f"同步时间失败: {str(e)}")
        # 发送 WebSocket 消息到前端，通知同步失败
        await ModbusHandler.channel_layer.group_send(
            "modbus_status",
            {
                "type": "sync_time_failed",
                "message": {
                    "reason": str(e),
                }
            }
        )
        return False