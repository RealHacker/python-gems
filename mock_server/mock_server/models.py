from django.db import models

class URL(models.Model):
    name = models.CharField(max_length=64)
    pattern = models.CharField(max_length=256)


class Condition(models.Model):
    METHOD_CHOICES = (
        ("GET", "GET"),
        ("POST", "POST"),
        ("HEAD", "HEAD"),
        ("DELETE", "DELETE"),
        ("PUT", "PUT")
    )
    url = models.ForeignKey(URL)
    method = models.CharField(max_length=32, choices=METHOD_CHOICES)
    state_filter = models.CharField(max_length=32, null=True)
    query_filter = models.CharField(max_length=128, null=True)

class Response(models.Model):
    RESPONSE_TYPES = (
        (1, "TEMPLATE"),
        (2, "JSON"),
    )
    condition = models.ForeignKey(Condition)
    is_inactive = models.BooleanField()
    response_type = models.IntegerField(choices=RESPONSE_TYPES)
    data = models.TextField()
    status_code = models.IntegerField(default=200)
    tpl_name = models.CharField(null=True, max_length=128)
    tpl_type = models.CharField(null=True, max_length=32)
    redirect_url = models.CharField(null=True, max_length=128)

class GlobalState(models.Model):
    name = models.CharField(max_length=32, unique=True)
    value = models.CharField(max_length=32)
    statetype = models.CharField(max_length=32)
    choices = models.CharField(max_length=256)

class Proxy(models.Model):
    isOn = models.BooleanField()
    proxy_server = models.CharField(max_length=128)

class AccessRecord(models.Model):
    condition = models.ForeignKey(Condition)
    fullurl = models.CharField(max_length=256)
    timestamp = models.DateTimeField(auto_now_add=True)

    
