from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class DataItem(models.Model):
    DATA_TYPES = [
        ('unsigned short', 'Unsigned Short'),
        ('float', 'Float'),
    ]

    READ_WRITE_CHOICES = [
        ('R', 'Read Only'),
        ('R/W', 'Read/Write'),
    ]

    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    address = models.IntegerField()
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    read_write = models.CharField(max_length=3, choices=READ_WRITE_CHOICES)
    command = models.CharField(max_length=10)

    # 用于存储最新读取的值
    last_value = models.FloatField(null=True, blank=True)
    last_read_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        unique_together = ('category', 'name')


class ModuleStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    concentration = models.FloatField(null=True, blank=True)
    raw_concentration = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    pressure = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
