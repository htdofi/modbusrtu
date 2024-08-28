from django.core.management.base import BaseCommand
from django.utils import timezone
from modbusrtu.models import DataItem, ModuleStatus
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian


class Command(BaseCommand):
    help = 'Read all Modbus data and update the database'

    def handle(self, *args, **options):
        client = ModbusTcpClient('your_modbus_server_ip', port=502)
        try:
            client.connect()
            start_address = 0
            num_registers = 195
            registers = []

            while start_address < num_registers:
                batch_size = min(125, num_registers - start_address)
                response = client.read_holding_registers(start_address, batch_size, unit=1)
                registers.extend(response.registers)
                start_address += batch_size

            for data_item in DataItem.objects.all():
                address = data_item.address
                if address < len(registers):
                    if data_item.data_type == "float":
                        if address + 1 < len(registers):
                            decoder = BinaryPayloadDecoder.fromRegisters(
                                registers[address:address + 2],
                                byteorder=Endian.Big,
                                wordorder=Endian.Little
                            )
                            value = decoder.decode_32bit_float()
                        else:
                            value = None
                    elif data_item.data_type == "unsigned short":
                        value = registers[address]
                    else:
                        value = None

                    data_item.last_value = value
                    data_item.last_read_time = timezone.now()
                    data_item.save()

                    # Update ModuleStatus
                    if "板" in data_item.name:
                        module_name = data_item.name.split("板")[0]
                        module_status, created = ModuleStatus.objects.get_or_create(name=module_name)

                        if data_item.name.endswith("浓度") and not data_item.name.endswith("标气浓度"):
                            module_status.concentration = value
                        elif data_item.name.endswith("浓度(单位:ppm 传感器原始值)"):
                            module_status.raw_concentration = value
                        elif data_item.name.endswith("浓度:温度"):
                            module_status.temperature = value
                        elif data_item.name.endswith("浓度:压力"):
                            module_status.pressure = value / 1000 if value is not None else None
                        elif data_item.name.endswith("板运行状态"):
                            module_status.status = "正常" if value == 1 else "异常" if value is not None else None

                        module_status.save()

            self.stdout.write(self.style.SUCCESS('Successfully read and updated all data'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading Modbus data: {e}'))
        finally:
            client.close()
