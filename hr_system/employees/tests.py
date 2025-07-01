from django.test import TestCase
from django.urls import reverse
from .models import Employee
from .forms import EmployeeForm
import datetime

class EmployeeModelTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            date_of_birth=datetime.date(1990, 1, 1),
            date_hired=datetime.date(2020, 1, 1),
            department="Engineering",
            job_title="Software Engineer",
            salary=75000.00
        )

    def test_employee_creation(self):
        self.assertEqual(self.employee.first_name, "John")
        self.assertEqual(self.employee.last_name, "Doe")
        self.assertEqual(str(self.employee), "John Doe")

    def test_employee_email_unique(self):
        with self.assertRaises(Exception): # Django raises IntegrityError, a subclass of Exception
            Employee.objects.create(
                first_name="Jane",
                last_name="Doe",
                email="john.doe@example.com", # Duplicate email
                date_of_birth=datetime.date(1992, 2, 2),
                date_hired=datetime.date(2021, 2, 2),
                department="HR",
                job_title="HR Manager",
                salary=65000.00
            )

class EmployeeFormTests(TestCase):
    def test_employee_form_valid(self):
        form_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'phone_number': '1234567890',
            'date_of_birth': '1995-05-15',
            'date_hired': '2022-03-10',
            'department': 'Marketing',
            'job_title': 'Marketing Specialist',
            'salary': 60000.00
        }
        form = EmployeeForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_employee_form_invalid_missing_required(self):
        form_data = { # Missing first_name, last_name, email etc.
            'salary': 60000.00
        }
        form = EmployeeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
        self.assertIn('last_name', form.errors)
        self.assertIn('email', form.errors)

    def test_employee_form_date_widgets(self):
        form = EmployeeForm()
        self.assertEqual(form.fields['date_of_birth'].widget.input_type, 'date')
        self.assertEqual(form.fields['date_hired'].widget.input_type, 'date')


class EmployeeViewTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="Test",
            last_name="User",
            email="test.user@example.com",
            date_of_birth=datetime.date(1985, 6, 15),
            date_hired=datetime.date(2019, 7, 1),
            department="IT",
            job_title="System Admin",
            salary=80000.00
        )

    def test_employee_list_view(self):
        response = self.client.get(reverse('employee_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.first_name)
        self.assertTemplateUsed(response, 'employees/employee_list.html')

    def test_employee_detail_view(self):
        response = self.client.get(reverse('employee_detail', args=[self.employee.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.email)
        self.assertTemplateUsed(response, 'employees/employee_detail.html')

    def test_employee_create_view_get(self):
        response = self.client.get(reverse('employee_create'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], EmployeeForm)
        self.assertTemplateUsed(response, 'employees/employee_form.html')

    def test_employee_create_view_post(self):
        data = {
            'first_name': 'New',
            'last_name': 'Employee',
            'email': 'new.employee@example.com',
            'date_of_birth': '1998-10-20',
            'date_hired': '2023-01-15',
            'department': 'Sales',
            'job_title': 'Sales Rep',
            'salary': 55000.00
        }
        response = self.client.post(reverse('employee_create'), data)
        self.assertEqual(response.status_code, 302) # Redirects on success
        self.assertTrue(Employee.objects.filter(email='new.employee@example.com').exists())

    def test_employee_update_view_post(self):
        updated_department = "Senior Engineering"
        data = {
            'first_name': self.employee.first_name,
            'last_name': self.employee.last_name,
            'email': self.employee.email,
            'date_of_birth': self.employee.date_of_birth.strftime('%Y-%m-%d'),
            'date_hired': self.employee.date_hired.strftime('%Y-%m-%d'),
            'department': updated_department, # Changed field
            'job_title': self.employee.job_title,
            'salary': self.employee.salary
        }
        response = self.client.post(reverse('employee_update', args=[self.employee.pk]), data)
        self.assertEqual(response.status_code, 302) # Redirects
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.department, updated_department)

    def test_employee_delete_view_post(self):
        response = self.client.post(reverse('employee_delete', args=[self.employee.pk]))
        self.assertEqual(response.status_code, 302) # Redirects
        self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())

    def test_employee_delete_view_get_confirm_page(self):
        response = self.client.get(reverse('employee_delete', args=[self.employee.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.employee.first_name)
        self.assertTemplateUsed(response, 'employees/employee_confirm_delete.html')
