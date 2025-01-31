from django.contrib import admin
from .models import Transaction
from bank.models import Bank
from django.shortcuts import get_object_or_404, redirect

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'amount', 'balance_after_transaction', 'transaction_type', 'loan_approve']
    
    def save_model(self, request, obj, form, change):
        obj.account.balance += obj.amount
        obj.balance_after_transaction = obj.account.balance
        obj.account.save()
        bank = get_object_or_404(Bank, id=1)
        bank.balance -= amount
        bank.save()
        super().save_model(request, obj, form, change)

