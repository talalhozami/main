from .models import SalaryStructure, Payslip, PayPeriod, Employee
from django.utils import timezone
from django.db import transaction
import calendar # For month name in PayPeriod __str__

def calculate_payslip_data(salary_structure: SalaryStructure):
    """
    Calculates payslip components based on a given salary structure.
    Returns a dictionary with the calculated data.
    """
    earnings = {
        'basic_salary': salary_structure.basic_salary,
        'housing_allowance': salary_structure.housing_allowance,
        'transport_allowance': salary_structure.transport_allowance,
        'other_allowances': salary_structure.other_allowances,
    }

    deductions = {
        'income_tax': salary_structure.income_tax,
        'provident_fund': salary_structure.provident_fund,
        'other_deductions': salary_structure.other_deductions,
    }

    total_earnings = sum(earnings.values())
    total_deductions = sum(deductions.values())
    net_salary = total_earnings - total_deductions

    return {
        'basic_salary_paid': earnings['basic_salary'],
        'housing_allowance_paid': earnings['housing_allowance'],
        'transport_allowance_paid': earnings['transport_allowance'],
        'other_allowances_paid': earnings['other_allowances'],
        'income_tax_deducted': deductions['income_tax'],
        'provident_fund_deducted': deductions['provident_fund'],
        'other_deductions_made': deductions['other_deductions'],
        'gross_salary': total_earnings,
        'total_deductions_amount': total_deductions,
        'net_salary_paid': net_salary,
    }

@transaction.atomic
def generate_payslip_for_employee(employee: Employee, year: int, month: int, force_regenerate: bool = False):
    """
    Generates a payslip for a specific employee and pay period.
    If a payslip already exists and force_regenerate is False, it returns the existing one.
    Returns the Payslip object (created or existing) or None if no salary structure.
    """
    try:
        salary_structure = employee.salary_structure
    except SalaryStructure.DoesNotExist:
        # Log this: print(f"No salary structure for employee {employee.id} - {employee}")
        return None # Or raise an error

    pay_period, created = PayPeriod.objects.get_or_create(year=year, month=month)

    if not force_regenerate:
        existing_payslip = Payslip.objects.filter(employee=employee, pay_period=pay_period).first()
        if existing_payslip:
            return existing_payslip

    # If forcing regeneration, delete existing payslip for this employee and period
    if force_regenerate:
         Payslip.objects.filter(employee=employee, pay_period=pay_period).delete()

    payslip_data = calculate_payslip_data(salary_structure)

    payslip = Payslip.objects.create(
        employee=employee,
        pay_period=pay_period,
        **payslip_data # Unpack the dictionary
    )
    return payslip

@transaction.atomic
def generate_payslips_for_period(year: int, month: int, employee_ids: list = None, force_regenerate: bool = False):
    """
    Generates payslips for all active employees (or a subset if employee_ids is provided)
    for a given year and month.
    Skips employees without a salary structure.
    Returns a tuple: (list_of_generated_payslips, list_of_errors)
    """
    pay_period, created = PayPeriod.objects.get_or_create(year=year, month=month)

    employees_to_process = Employee.objects.all()
    if employee_ids:
        employees_to_process = employees_to_process.filter(id__in=employee_ids)

    generated_payslips = []
    errors = []

    for employee in employees_to_process:
        try:
            salary_structure = employee.salary_structure
            # If forcing regeneration, delete existing payslip for this employee and period
            if force_regenerate:
                Payslip.objects.filter(employee=employee, pay_period=pay_period).delete()

            # Check if payslip already exists (if not forcing regeneration)
            if not force_regenerate and Payslip.objects.filter(employee=employee, pay_period=pay_period).exists():
                # errors.append(f"Payslip already exists for {employee} for {pay_period} and regeneration not forced.")
                # Or retrieve and add to generated_payslips if that's the desired behavior
                existing_payslip = Payslip.objects.get(employee=employee, pay_period=pay_period)
                generated_payslips.append(existing_payslip)
                continue

            payslip_data = calculate_payslip_data(salary_structure)

            payslip = Payslip.objects.create(
                employee=employee,
                pay_period=pay_period,
                **payslip_data
            )
            generated_payslips.append(payslip)
        except SalaryStructure.DoesNotExist:
            errors.append(f"No salary structure found for {employee}. Skipping payslip generation.")
        except Exception as e:
            errors.append(f"Error generating payslip for {employee}: {str(e)}")
            # Potentially log the full traceback here

    return generated_payslips, errors
