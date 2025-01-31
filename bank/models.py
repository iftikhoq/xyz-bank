from django.db import models

class Bank(models.Model):
    name = models.CharField(max_length=30)
    balance = models.DecimalField(default=0, max_digits=20, decimal_places=2) 
    def __str__(self):
        return str(self.name)