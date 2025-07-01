from django.db import models
from employees.models import Employee
from decimal import Decimal # Import Decimal

class SalaryStructure(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='salary_structure')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly basic salary")
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Common Deductions
    income_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Calculated monthly income tax")
    provident_fund = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Employee's contribution")
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def total_earnings(self):
        return self.basic_salary + self.housing_allowance + self.transport_allowance + self.other_allowances

    def total_deductions(self):
        return self.income_tax + self.provident_fund + self.other_deductions

    def net_salary(self):
        return self.total_earnings() - self.total_deductions()

    def __str__(self):
        return f"Salary Structure for {self.employee}"

class PayPeriod(models.Model):
    month = models.PositiveIntegerField() # e.g., 1 for January, 12 for December
    year = models.PositiveIntegerField() # e.g., 2023

    class Meta:
        unique_together = ('month', 'year') # Ensure each month/year combination is unique
        ordering = ['-year', '-month']

    def __str__(self):
        import calendar
        return f"{calendar.month_name[self.month]} {self.year}"

class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    pay_period = models.ForeignKey(PayPeriod, on_delete=models.PROTECT, related_name='payslips') # Protect so you don't delete historical data easily

    # Snapshot of values at the time of payslip generation
    basic_salary_paid = models.DecimalField(max_digits=10, decimal_places=2)
    housing_allowance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transport_allowance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    other_allowances_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    income_tax_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    provident_fund_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    other_deductions_made = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions_amount = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary_paid = models.DecimalField(max_digits=10, decimal_places=2)

    generated_on = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed')], default='PENDING')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'pay_period') # One payslip per employee per pay period
        ordering = ['-pay_period__year', '-pay_period__month', 'employee__last_name']

    def __str__(self):
        return f"Payslip for {self.employee} - {self.pay_period}"

    # It might be useful to also store a JSON snapshot of the SalaryStructure used, for auditing
    # salary_structure_snapshot = models.JSONField(null=True, blank=True)
    # However, for simplicity now, we'll directly copy fields.
