from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django import forms # Import django forms

from .models import SalaryStructure, Payslip, PayPeriod, Employee
from .forms import SalaryStructureForm, PayslipGenerationForm, PayslipFilterForm, EmployeeSalaryAssignmentForm
from .services import generate_payslips_for_period, generate_payslip_for_employee
import datetime

# --- Salary Structure Views ---
class SalaryStructureListView(ListView):
    model = SalaryStructure
    template_name = 'payroll/salarystructure_list.html'
    context_object_name = 'structures'

    def get_queryset(self):
        return SalaryStructure.objects.select_related('employee').all()

class SalaryStructureCreateView(CreateView):
    model = SalaryStructure
    form_class = SalaryStructureForm
    template_name = 'payroll/salarystructure_form.html'
    success_url = reverse_lazy('payroll:salarystructure_list')

    def get_initial(self):
        initial = super().get_initial()
        employee_id_from_url = self.kwargs.get('employee_id')
        if employee_id_from_url:
            try:
                employee = Employee.objects.get(pk=employee_id_from_url)
                if not hasattr(employee, 'salary_structure'):
                    initial['employee'] = employee
                else:
                    # This case should ideally redirect to update view from a dispatch or get method
                    messages.warning(self.request, f"Salary structure already exists for {employee}. Redirecting to update page.")
            except Employee.DoesNotExist:
                messages.error(self.request, "Selected employee for salary structure not found.")
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        employee_id_from_url = self.kwargs.get('employee_id')
        if employee_id_from_url:
            try:
                employee = Employee.objects.get(pk=employee_id_from_url)
                if not hasattr(employee, 'salary_structure'):
                    form.fields['employee'].initial = employee
                    form.fields['employee'].disabled = True # Disable if creating for specific employee
                    form.fields['employee'].widget = forms.HiddenInput() # Or hide completely
                    form.instance.employee = employee # Set it on the instance early
            except Employee.DoesNotExist:
                pass # Error will be handled by initial or form validation
        return form

    def form_valid(self, form):
        employee_id_from_url = self.kwargs.get('employee_id')
        if employee_id_from_url and not form.instance.pk: # Creating for a specific employee
            try:
                employee = Employee.objects.get(pk=employee_id_from_url)
                if hasattr(employee, 'salary_structure'):
                    # This should ideally be caught earlier, e.g. in dispatch or get
                    messages.error(self.request, f"Salary structure already exists for {employee}.")
                    return self.form_invalid(form)
                form.instance.employee = employee
            except Employee.DoesNotExist:
                messages.error(self.request, "Selected employee not found. Cannot create salary structure.")
                return self.form_invalid(form)

        messages.success(self.request, "Salary structure saved successfully.")
        return super().form_valid(form)

class SelectEmployeeForSalaryView(FormView):
    form_class = EmployeeSalaryAssignmentForm
    template_name = 'payroll/select_employee_for_salary.html'

    def form_valid(self, form):
        employee = form.cleaned_data['employee']
        # Check if salary structure already exists for this employee
        if hasattr(employee, 'salary_structure'):
            return redirect('payroll:salarystructure_update', pk=employee.salary_structure.pk)
        else:
            # Use reverse with kwargs for clarity
            return redirect(reverse('payroll:salarystructure_create_for_employee', kwargs={'employee_id': employee.pk}))


class SalaryStructureUpdateView(UpdateView):
    model = SalaryStructure
    form_class = SalaryStructureForm
    template_name = 'payroll/salarystructure_form.html'
    success_url = reverse_lazy('payroll:salarystructure_list')

    def form_valid(self, form):
        messages.success(self.request, "Salary structure updated successfully.")
        return super().form_valid(form)

# --- Payslip Views ---
class PayslipListView(ListView):
    model = Payslip
    template_name = 'payroll/payslip_list.html'
    context_object_name = 'payslips'
    paginate_by = 20

    def get_queryset(self):
        queryset = Payslip.objects.select_related('employee', 'pay_period').all()
        self.filter_form = PayslipFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            pay_period = self.filter_form.cleaned_data.get('pay_period')
            employee = self.filter_form.cleaned_data.get('employee')
            if pay_period:
                queryset = queryset.filter(pay_period=pay_period)
            if employee:
                queryset = queryset.filter(employee=employee)
        return queryset.order_by('-pay_period__year', '-pay_period__month', 'employee__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        return context

class PayslipDetailView(DetailView):
    model = Payslip
    template_name = 'payroll/payslip_detail.html'
    context_object_name = 'payslip'

    def get_queryset(self):
        return Payslip.objects.select_related('employee', 'pay_period').all()


class GeneratePayslipsView(FormView):
    form_class = PayslipGenerationForm
    template_name = 'payroll/generate_payslips_form.html'
    success_url = reverse_lazy('payroll:payslip_list') # Redirect to payslip list after generation

    def form_valid(self, form):
        year = int(form.cleaned_data['year'])
        month = int(form.cleaned_data['month'])
        force_regenerate = form.cleaned_data.get('force_regenerate', False)

        generated, errors = generate_payslips_for_period(year=year, month=month, force_regenerate=force_regenerate)

        if generated:
            messages.success(self.request, f"{len(generated)} payslip(s) generated/retrieved for {calendar.month_name[month]} {year}.")
        if errors:
            for error_msg in errors:
                messages.error(self.request, error_msg)
        if not generated and not errors: # Neither generated nor errors means no eligible employees or already exist
            existing_count = Payslip.objects.filter(pay_period__year=year, pay_period__month=month).count()
            if existing_count > 0 and not force_regenerate:
                 messages.info(self.request, f"Payslips for {calendar.month_name[month]} {year} already exist. Use 'Force Re-generation' to overwrite.")
            else:
                messages.info(self.request, f"No payslips generated for {calendar.month_name[month]} {year}. Ensure employees have salary structures assigned.")


        return HttpResponseRedirect(self.get_success_url())

# --- PayPeriod Views (Optional - could be managed via Admin or simple scripts) ---
class PayPeriodListView(ListView):
    model = PayPeriod
    template_name = 'payroll/payperiod_list.html'
    context_object_name = 'pay_periods'
    ordering = ['-year', '-month']

# Helper for calendar month name if needed in templates directly and not using model's __str__
import calendar
from django.template.defaultfilters import register

@register.filter(name='month_name_filter') # Renamed to avoid conflict if django.utils.dateformat.MONTHS is used
def month_name_custom(month_number): # Renamed function
    try:
        return calendar.month_name[int(month_number)]
    except (ValueError, TypeError, IndexError):
        return ''
