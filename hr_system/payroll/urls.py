from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    # Salary Structure URLs
    path('salary-structures/', views.SalaryStructureListView.as_view(), name='salarystructure_list'),
    path('salary-structures/select-employee/', views.SelectEmployeeForSalaryView.as_view(), name='select_employee_for_salary'),
    path('salary-structures/new/', views.SalaryStructureCreateView.as_view(), name='salarystructure_create'), # Generic create
    path('salary-structures/new/for-employee/<int:employee_id>/', views.SalaryStructureCreateView.as_view(), name='salarystructure_create_for_employee'), # Create for specific employee
    path('salary-structures/<int:pk>/update/', views.SalaryStructureUpdateView.as_view(), name='salarystructure_update'),
    # path('salary-structures/<int:pk>/delete/', views.SalaryStructureDeleteView.as_view(), name='salarystructure_delete'), # If you add delete functionality

    # Payslip URLs
    path('payslips/', views.PayslipListView.as_view(), name='payslip_list'),
    path('payslips/generate/', views.GeneratePayslipsView.as_view(), name='generate_payslips'),
    path('payslips/<int:pk>/', views.PayslipDetailView.as_view(), name='payslip_detail'),
    # path('payslips/<int:pk>/update-status/', views.UpdatePayslipStatusView.as_view(), name='payslip_update_status'), # For changing payment status

    # PayPeriod URLs (Optional)
    path('pay-periods/', views.PayPeriodListView.as_view(), name='payperiod_list'),
]
