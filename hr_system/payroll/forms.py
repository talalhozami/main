from django import forms
from .models import SalaryStructure, PayPeriod, Employee
import datetime

class SalaryStructureForm(forms.ModelForm):
    class Meta:
        model = SalaryStructure
        fields = [
            'employee',
            'basic_salary',
            'housing_allowance',
            'transport_allowance',
            'other_allowances',
            'income_tax',
            'provident_fund',
            'other_deductions'
        ]
        # To make employee selection easier if there are many employees
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If updating, make employee field read-only or hide it.
        # For creation, you might want to limit choices to employees without a salary structure yet.
        if self.instance and self.instance.pk:
            self.fields['employee'].disabled = True
            # Or: self.fields['employee'].widget = forms.HiddenInput()
        else:
            # Limit choices to employees who don't yet have a salary structure
            self.fields['employee'].queryset = Employee.objects.filter(salary_structure__isnull=True)


class PayslipGenerationForm(forms.Form):
    # Define current_year at class level before it's used by MONTH_CHOICES
    current_year = datetime.date.today().year
    YEAR_CHOICES = [(year, year) for year in range(current_year - 5, current_year + 2)]
    # MONTH_CHOICES needs access to current_year, so ensure it's defined above or use datetime.date.today().year directly
    MONTH_CHOICES = [(i, datetime.date(datetime.date.today().year, i, 1).strftime('%B')) for i in range(1, 13)]

    year = forms.ChoiceField(choices=YEAR_CHOICES, initial=current_year)
    month = forms.ChoiceField(choices=MONTH_CHOICES, initial=datetime.date.today().month)

    # Optional: Allow selecting specific employees
    # employees = forms.ModelMultipleChoiceField(
    #     queryset=Employee.objects.all(),
    #     widget=forms.SelectMultiple(attrs={'class': 'select2'}),
    #     required=False,
    #     help_text="Leave blank to generate for all employees with salary structures."
    # )
    force_regenerate = forms.BooleanField(required=False, label="Force Re-generation", help_text="If checked, will delete and recreate payslips if they already exist for the selected period.")


class PayPeriodForm(forms.ModelForm):
    class Meta:
        model = PayPeriod
        fields = ['month', 'year']
        widgets = {
            'month': forms.Select(choices=[(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = datetime.date.today().year
        self.fields['year'].widget = forms.Select(choices=[(y,y) for y in range(current_year -10, current_year + 5)])
        self.fields['year'].initial = current_year
        self.fields['month'].initial = datetime.date.today().month

class PayslipFilterForm(forms.Form):
    pay_period = forms.ModelChoiceField(queryset=PayPeriod.objects.all().order_by('-year', '-month'), required=False, label="Pay Period")
    employee = forms.ModelChoiceField(queryset=Employee.objects.all().order_by('first_name', 'last_name'), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pay_period'].label_from_instance = lambda obj: f"{obj.get_month_display()} {obj.year}" if hasattr(obj, 'get_month_display') else str(obj)
        self.fields['employee'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"

# Add a more specific form for selecting employee if not using the one in SalaryStructureForm directly
class EmployeeSalaryAssignmentForm(forms.Form):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(salary_structure__isnull=True),
        label="Select Employee",
        help_text="Choose an employee to assign or update a salary structure."
    )
