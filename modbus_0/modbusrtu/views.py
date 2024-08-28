# views.py
import threading
import json
import datetime
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from modbusrtu.management.commend.serial_handler import ModbusHandler
from modbusrtu.management.commend.time_manage import sync_time_with_device,start_periodic_sync_task
import modbusrtu.management.commend.time_manage
import serial.tools.list_ports

_global_modbus_handler = None

def get_modbus_handler():
    global _global_modbus_handler
    if _global_modbus_handler is None:
        print("Initializing global ModbusHandler")
        _global_modbus_handler = ModbusHandler()
    return _global_modbus_handler

def index(request):
    return render(request, 'index.html')

def sync_time_thread(modbus_handler):
    # 在单独的线程中执行同步操作
    if not async_to_sync(sync_time_with_device)(modbus_handler):
        print("时间同步失败")
    else:
        print("时间同步成功")

@csrf_exempt
def toggle_connection(request):
    modbus_handler = get_modbus_handler()
    if request.method == 'POST':
        data = json.loads(request.body)
        selected_port = data.get('port')
        if not modbus_handler.serial_connected:
            # 连接 Modbus 设备
            success = async_to_sync(modbus_handler.connect_modbus)(selected_port)
            if success:
                # 连接成功后，同步一次时间，但不阻塞主线程
                threading.Thread(target=sync_time_thread, args=(modbus_handler,)).start()

                # 启动定时检查和时间同步任务
                start_periodic_sync_task(modbus_handler)
                return JsonResponse({
                    'status': 'success',
                    'connected': True,
                    'message': f"Connected to {selected_port}"
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'connected': False,
                    'message': "Failed to connect"
                })
        else:
            # 断开 Modbus 设备
            success = async_to_sync(modbus_handler.disconnect_modbus)()
            if success:
                return JsonResponse({
                    'status': 'success',
                    'connected': False,
                    'message': "Disconnected"
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'connected': True,
                    'message': "Failed to disconnect"
                })
    return JsonResponse({'status': 'error', 'message': {'reason': 'Invalid request method'}})


def get_serial_ports(request):
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return JsonResponse({'ports': ports})

@csrf_exempt
def command_page(request):
    """ Render the command page with input and output boxes. """
    return render(request, 'command_page.html')

@csrf_exempt
def send_command(request):
    """ Handle command input from the user and return the response from the device. """
    if request.method == 'POST':
        data = json.loads(request.body)
        command = data.get('command')
        modbus_handler = get_modbus_handler()
        # 确保 ModbusHandler 已连接
        if not modbus_handler.serial_connected:
            return JsonResponse({'result': 'ModbusHandler is not connected. Please connect first.'})
        # 发送命令给设备并获取结果
        result = async_to_sync(modbus_handler.send_command)(command)
        # 返回设备的结果
        return JsonResponse({'result': result})
    return JsonResponse({'result': 'Invalid request method.'})