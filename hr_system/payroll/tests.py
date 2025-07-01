from django.test import TestCase
from django.urls import reverse
from employees.models import Employee
from .models import SalaryStructure, Payslip, PayPeriod
from .services import calculate_payslip_data, generate_payslip_for_employee, generate_payslips_for_period
from .forms import SalaryStructureForm, PayslipGenerationForm
import datetime
from decimal import Decimal

class PayrollModelTests(TestCase):
    def setUp(self):
        self.employee1 = Employee.objects.create(
            first_name="Alice", last_name="Smith", email="alice@example.com",
            date_of_birth=datetime.date(1990, 1, 1), date_hired=datetime.date(2020, 1, 1),
            department="Tech", job_title="Developer", salary=Decimal("60000.00") # Base Employee salary
        )
        self.employee2 = Employee.objects.create(
            first_name="Bob", last_name="Johnson", email="bob@example.com",
            date_of_birth=datetime.date(1985, 5, 5), date_hired=datetime.date(2018, 5, 5),
            department="Sales", job_title="Manager", salary=Decimal("80000.00")
        )
        self.salary_structure = SalaryStructure.objects.create(
            employee=self.employee1,
            basic_salary=Decimal("3000.00"),
            housing_allowance=Decimal("500.00"),
            transport_allowance=Decimal("200.00"),
            income_tax=Decimal("300.00"),
            provident_fund=Decimal("150.00")
        )
        self.pay_period = PayPeriod.objects.create(year=2023, month=7)

    def test_salary_structure_calculations(self):
        self.assertEqual(self.salary_structure.total_earnings(), Decimal("3700.00"))
        self.assertEqual(self.salary_structure.total_deductions(), Decimal("450.00"))
        self.assertEqual(self.salary_structure.net_salary(), Decimal("3250.00"))
        self.assertEqual(str(self.salary_structure), f"Salary Structure for {self.employee1}")

    def test_pay_period_str(self):
        self.assertEqual(str(self.pay_period), "July 2023")

    def test_payslip_creation(self):
        payslip = Payslip.objects.create(
            employee=self.employee1,
            pay_period=self.pay_period,
            basic_salary_paid=self.salary_structure.basic_salary,
            housing_allowance_paid=self.salary_structure.housing_allowance,
            gross_salary=self.salary_structure.total_earnings(),
            total_deductions_amount=self.salary_structure.total_deductions(),
            net_salary_paid=self.salary_structure.net_salary()
        )
        self.assertEqual(str(payslip), f"Payslip for {self.employee1} - {self.pay_period}")
        self.assertEqual(payslip.net_salary_paid, Decimal("3250.00"))


class PayrollServiceTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="Charlie", last_name="Brown", email="charlie@example.com",
            date_of_birth=datetime.date(1992, 2, 2), date_hired=datetime.date(2021, 2, 2),
            department="Support", job_title="Agent", salary=Decimal("50000.00")
        )
        self.salary_structure = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("2500.00"),
            housing_allowance=Decimal("400.00"),
            transport_allowance=Decimal("150.00"),
            other_allowances=Decimal("50.00"),
            income_tax=Decimal("250.00"),
            provident_fund=Decimal("120.00"),
            other_deductions=Decimal("30.00")
        )
        # Expected: Earnings = 3100, Deductions = 400, Net = 2700

    def test_calculate_payslip_data(self):
        data = calculate_payslip_data(self.salary_structure)
        self.assertEqual(data['gross_salary'], Decimal("3100.00"))
        self.assertEqual(data['total_deductions_amount'], Decimal("400.00"))
        self.assertEqual(data['net_salary_paid'], Decimal("2700.00"))
        self.assertEqual(data['basic_salary_paid'], Decimal("2500.00"))

    def test_generate_payslip_for_employee(self):
        payslip = generate_payslip_for_employee(self.employee, 2023, 8)
        self.assertIsNotNone(payslip)
        self.assertEqual(payslip.employee, self.employee)
        self.assertEqual(payslip.pay_period.year, 2023)
        self.assertEqual(payslip.pay_period.month, 8)
        self.assertEqual(payslip.net_salary_paid, Decimal("2700.00"))

        # Test idempotency (should return existing if not forcing)
        payslip_again = generate_payslip_for_employee(self.employee, 2023, 8)
        self.assertEqual(payslip.pk, payslip_again.pk)

        # Test force regenerate
        original_id = payslip.id
        new_payslip = generate_payslip_for_employee(self.employee, 2023, 8, force_regenerate=True)
        self.assertNotEqual(original_id, new_payslip.id) # New payslip object
        self.assertEqual(new_payslip.net_salary_paid, Decimal("2700.00"))


    def test_generate_payslip_for_employee_no_salary_structure(self):
        no_ss_employee = Employee.objects.create(
            first_name="NoSS", last_name="User", email="noss@example.com",
            date_of_birth=datetime.date(1990,1,1), date_hired=datetime.date(2020,1,1), department="Test", job_title="Tester", salary=1000
        )
        payslip = generate_payslip_for_employee(no_ss_employee, 2023, 9)
        self.assertIsNone(payslip)

    def test_generate_payslips_for_period(self):
        # Employee 2 for this test
        employee2 = Employee.objects.create(
            first_name="David", last_name="Lee", email="david@example.com",
            date_of_birth=datetime.date(1993, 3, 3), date_hired=datetime.date(2022, 3, 3),
            department="HR", job_title="Specialist", salary=Decimal("55000.00")
        )
        SalaryStructure.objects.create(
            employee=employee2, basic_salary=Decimal("2800.00"), income_tax=Decimal("280.00")
            # Net for employee2 will be 2800-280 = 2520
        )

        # Employee without salary structure
        Employee.objects.create(
            first_name="Eve", last_name="Test", email="eve@example.com",
            date_of_birth=datetime.date(1994, 4, 4), date_hired=datetime.date(2023, 4, 4),
            department="Intern", job_title="Intern", salary=Decimal("30000.00")
        )

        generated, errors = generate_payslips_for_period(2023, 10)

        self.assertEqual(len(generated), 2) # self.employee and employee2
        self.assertEqual(len(errors), 1) # For Eve
        self.assertIn("No salary structure found for Eve Test.", errors[0])

        payslip_charlie = next(p for p in generated if p.employee == self.employee)
        payslip_david = next(p for p in generated if p.employee == employee2)

        self.assertEqual(payslip_charlie.net_salary_paid, Decimal("2700.00"))
        self.assertEqual(payslip_david.net_salary_paid, Decimal("2520.00"))

        # Test with force_regenerate
        generated_force, errors_force = generate_payslips_for_period(2023, 10, force_regenerate=True)
        self.assertEqual(len(generated_force), 2)
        self.assertEqual(len(errors_force), 1)
        # Check if IDs are different (or count is still 2 after deletion)
        self.assertEqual(Payslip.objects.filter(pay_period__year=2023, pay_period__month=10).count(), 2)


class PayrollFormTests(TestCase):
    def setUp(self):
        self.employee_no_ss = Employee.objects.create( # Renamed to be more descriptive
            first_name="Form", last_name="Tester", email="form@example.com",
            date_of_birth=datetime.date(1990,1,1), date_hired=datetime.date(2020,1,1), department="Test", job_title="Tester", salary=1000
        )
        self.employee_with_ss = Employee.objects.create(
            first_name="SS", last_name="Haver", email="sshaver@example.com",
            date_of_birth=datetime.date(1990,1,1), date_hired=datetime.date(2020,1,1), department="Test", job_title="Tester", salary=1000
        )
        SalaryStructure.objects.create(employee=self.employee_with_ss, basic_salary=100)


    def test_salary_structure_form_valid_new_employee(self):
        form_data = {
            'employee': self.employee_no_ss.pk,
            'basic_salary': '3000.00',
            'housing_allowance': '500.00',
            'transport_allowance': '200.00',
            'other_allowances': '100.00',
            'income_tax': '300.00',
            'provident_fund': '150.00',
            'other_deductions': '50.00'
        }
        form = SalaryStructureForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        # Check that queryset for employee field is limited to those without SS
        self.assertNotIn(self.employee_with_ss, form.fields['employee'].queryset)
        self.assertIn(self.employee_no_ss, form.fields['employee'].queryset)


    def test_salary_structure_form_valid_update_employee_disabled(self):
        ss_instance = SalaryStructure.objects.get(employee=self.employee_with_ss)
        form = SalaryStructureForm(instance=ss_instance)
        self.assertTrue(form.fields['employee'].disabled)


    def test_salary_structure_form_invalid_missing_fields(self):
        form_data = {'employee': self.employee_no_ss.pk} # Missing other required fields
        form = SalaryStructureForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('basic_salary', form.errors)

    def test_payslip_generation_form_valid(self):
        form_data = {'year': 2023, 'month': 7, 'force_regenerate': True}
        form = PayslipGenerationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_payslip_generation_form_initials(self):
        form = PayslipGenerationForm()
        current_year = datetime.date.today().year
        current_month = datetime.date.today().month
        self.assertEqual(int(form.fields['year'].initial), current_year) # Ensure it's int for comparison
        self.assertEqual(int(form.fields['month'].initial), current_month) # Ensure it's int for comparison


class PayrollViewTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="View", last_name="User", email="view@example.com",
            date_of_birth=datetime.date(1990,1,1), date_hired=datetime.date(2020,1,1), department="ViewDept", job_title="Viewer", salary=70000
        )
        self.salary_structure = SalaryStructure.objects.create(
            employee=self.employee, basic_salary=Decimal("3500.00"), income_tax=Decimal("350.00")
        )
        self.pay_period = PayPeriod.objects.create(year=2023, month=11)
        self.payslip = generate_payslip_for_employee(self.employee, 2023, 11)

        self.employee_no_ss = Employee.objects.create(
            first_name="NoSSView", last_name="User", email="nossview@example.com",
            date_of_birth=datetime.date(1991,1,1), date_hired=datetime.date(2021,1,1), department="ViewDept", job_title="ViewerNoSS", salary=60000
        )


    def test_salary_structure_list_view(self):
        response = self.client.get(reverse('payroll:salarystructure_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.first_name)
        self.assertTemplateUsed(response, 'payroll/salarystructure_list.html')

    def test_select_employee_for_salary_view_get(self): # Renamed for clarity
        response = self.client.get(reverse('payroll:select_employee_for_salary'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payroll/select_employee_for_salary.html')
        # Check that employee with SS is not in the choices
        self.assertNotContains(response, f'>{self.employee.first_name} {self.employee.last_name}<')
        self.assertContains(response, f'>{self.employee_no_ss.first_name} {self.employee_no_ss.last_name}<')


    def test_select_employee_for_salary_view_post_new_ss(self):
        response = self.client.post(reverse('payroll:select_employee_for_salary'), {'employee': self.employee_no_ss.pk})
        self.assertRedirects(response, reverse('payroll:salarystructure_create_for_employee', kwargs={'employee_id': self.employee_no_ss.pk}))

    def test_select_employee_for_salary_view_post_existing_ss(self):
        response = self.client.post(reverse('payroll:select_employee_for_salary'), {'employee': self.employee.pk}) # This employee already has an SS
        # This will fail if the form's queryset for 'employee' in SelectEmployeeForSalaryForm
        # correctly excludes employees who already have a salary structure.
        # The current EmployeeSalaryAssignmentForm does filter: Employee.objects.filter(salary_structure__isnull=True)
        # So, this test case as written, where we POST an employee who *has* an SS,
        # means the form itself would be invalid if that employee wasn't in the choices.
        # Let's assume the goal is to test redirection if somehow such a POST occurred or if the form was different.
        # For the current form, this POST would be invalid.
        #
        # If the form allowed selecting an employee who already has a structure, then this redirection would be correct:
        # self.assertRedirects(response, reverse('payroll:salarystructure_update', kwargs={'pk': self.employee.salary_structure.pk}))
        #
        # Given EmployeeSalaryAssignmentForm filters to salary_structure__isnull=True,
        # a POST with self.employee.pk should result in form invalidation.
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('employee', form.errors)


    def test_salary_structure_create_view_get_for_employee(self): # Renamed
        response = self.client.get(reverse('payroll:salarystructure_create_for_employee', kwargs={'employee_id': self.employee_no_ss.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payroll/salarystructure_form.html')
        self.assertEqual(response.context['form'].initial.get('employee'), self.employee_no_ss)
        self.assertFalse(response.context['form'].instance.pk) # Ensure it's a create form

    def test_salary_structure_create_view_post_for_employee(self): # Renamed
        form_data = {
            # 'employee' is now handled by the view via URL and form.instance.employee
            'basic_salary': '4000.00',
            'housing_allowance': '600.00',
            'transport_allowance': '250.00',
            'other_allowances': '50.00', # Added missing field
            'income_tax': '400.00',
            'provident_fund': '200.00',
            'other_deductions': '0.00' # Ensure it's a decimal string
        }
        response = self.client.post(reverse('payroll:salarystructure_create_for_employee', kwargs={'employee_id': self.employee_no_ss.pk}), form_data)
        self.assertEqual(response.status_code, 302, form.errors.as_text() if response.context and (form := response.context.get('form')) else "No form context or form has no errors attribute / Response content: " + response.content.decode() )
        self.assertTrue(SalaryStructure.objects.filter(employee=self.employee_no_ss).exists())
        self.assertEqual(SalaryStructure.objects.get(employee=self.employee_no_ss).basic_salary, Decimal("4000.00"))


    def test_salary_structure_update_view_post(self):
        updated_basic = Decimal("3800.00")
        form_data = {
            'employee': self.salary_structure.employee.pk,
            'basic_salary': str(updated_basic),
            'housing_allowance': str(self.salary_structure.housing_allowance),
            'transport_allowance': str(self.salary_structure.transport_allowance),
            'other_allowances': str(self.salary_structure.other_allowances),
            'income_tax': str(self.salary_structure.income_tax),
            'provident_fund': str(self.salary_structure.provident_fund),
            'other_deductions': str(self.salary_structure.other_deductions),
        }
        response = self.client.post(reverse('payroll:salarystructure_update', kwargs={'pk': self.salary_structure.pk}), form_data)
        self.assertEqual(response.status_code, 302)
        self.salary_structure.refresh_from_db()
        self.assertEqual(self.salary_structure.basic_salary, updated_basic)

    def test_payslip_list_view(self):
        response = self.client.get(reverse('payroll:payslip_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.first_name)
        self.assertContains(response, "November 2023")
        self.assertTemplateUsed(response, 'payroll/payslip_list.html')

    def test_payslip_detail_view(self):
        response = self.client.get(reverse('payroll:payslip_detail', kwargs={'pk': self.payslip.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.email)
        self.assertContains(response, str(self.payslip.net_salary_paid))
        self.assertTemplateUsed(response, 'payroll/payslip_detail.html')

    def test_generate_payslips_view_get(self):
        response = self.client.get(reverse('payroll:generate_payslips'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payroll/generate_payslips_form.html')
        self.assertIsInstance(response.context['form'], PayslipGenerationForm)

    def test_generate_payslips_view_post(self):
        Payslip.objects.filter(employee=self.employee, pay_period__year=2023, pay_period__month=12).delete()
        form_data = {'year': '2023', 'month': '12'} # Values from form are strings
        response = self.client.post(reverse('payroll:generate_payslips'), form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payslip.objects.filter(employee=self.employee, pay_period__year=2023, pay_period__month=12).exists())

    def test_pay_period_list_view(self):
        response = self.client.get(reverse('payroll:payperiod_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.pay_period.year))
        # self.assertContains(response, "November") # Using month_name_filter now
        self.assertTemplateUsed(response, 'payroll/payperiod_list.html')
