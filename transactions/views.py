from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from bank.models import Bank
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID, TRANSFER
from datetime import datetime
from django.db.models import Sum
from accounts.models import UserBankAccount
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail

from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferForm,
)
from transactions.models import Transaction

class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account

        bank = get_object_or_404(Bank, id=1)
        bank.balance += amount
        bank.save()

        account.balance += amount 
        account.save(
            update_fields=[
                'balance'
            ]
        )

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        bank = get_object_or_404(Bank, id=1)

        if self.request.user.account.balance < amount:
            messages.error(
                self.request,
                f'You dont have sufficient balance in your account'
            )

        elif bank.balance < amount:
            messages.error(
            self.request,
            f'Bank is bankrupt.'
            )

        else:
            self.request.user.account.balance -= form.cleaned_data.get('amount')

            self.request.user.account.save(update_fields=['balance'])
            
            bank.balance -= amount
            bank.save()

            messages.success(
                self.request,
                f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
            )

            send_mail(
                subject="Withdrawal",
                message=f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account',
                from_email="ifti.hoq087@gmail.com",
                recipient_list=[self.request.user.email],
                fail_silently=False,
            )

        return super().form_valid(form)

class TransferMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Transfer Money'

    def get_initial(self):
        initial = {'transaction_type': TRANSFER}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        rec_account_no = form.cleaned_data.get('rec_account_no')
        try:
            rec = UserBankAccount.objects.get(account_no=rec_account_no)
            self.request.user.account.balance -= form.cleaned_data.get('amount')
            rec.balance += form.cleaned_data.get('amount')
            self.request.user.account.save(update_fields=['balance'])
            rec.save(update_fields=['balance'])

            send_mail(
                subject="Transfer",
                message=f'Successfully Transferred {"{:,.2f}".format(float(amount))}$ from your account',
                from_email="ifti.hoq087@gmail.com",
                recipient_list=[self.request.user.email],
                fail_silently=False,
            )
            send_mail(
                subject="Transfer",
                message=f'You got {"{:,.2f}".format(float(amount))}$ from {self.request.user.first_name}',
                from_email="ifti.hoq087@gmail.com",
                recipient_list=[rec.user.email],
                fail_silently=False,
            )

            messages.success(
                self.request,
                f'Successfully transferred {"{:,.2f}".format(float(amount))}$'
            )
        except ObjectDoesNotExist:
            messages.error(
                self.request,
                f'No account is associated with this number.'
            )

        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        
        bank = get_object_or_404(Bank, id=1)
        
        if bank.balance < amount:
            messages.error(
            self.request,
            f'Bank doesnt have sufficient balance'
            )
        else:
            bank.balance -= amount
            bank.save()
            messages.success(
                self.request,
                f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
            )

        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans'
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset