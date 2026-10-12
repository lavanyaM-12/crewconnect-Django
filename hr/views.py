from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from hr.models import Employee, Department, Designation, Leave

from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail

# Create your views here.
def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request,username=username,password=password)
        if user is not None:
            login(request, user)
            if Employee.objects.filter(user=user).exists():
                return redirect("employee_dashboard")
            return redirect("dashboard")
        return render(request,"login.html",{"error": "Invalid username or password"})
    return render(request, "login.html")

@login_required
@never_cache
def dashboard(request):
    return render(request, "dashboard.html")


def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
@never_cache
def employee_list(request):
    employees = (Employee.objects.select_related("department","designation")
                 .filter(status=True))

    return render(request,"employee_list.html",
                               {"employees": employees})


@login_required
@never_cache
def employee_create(request):

    departments = Department.objects.all()
    designations = Designation.objects.all()

    if request.method == "POST":

        employee_id = request.POST.get("employee_id")
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")

        department_id = request.POST.get("department")
        designation_id = request.POST.get("designation")

        joining_date = request.POST.get("joining_date")
        employment_type = request.POST.get("employment_type")
        salary = request.POST.get("salary")
        address = request.POST.get("address")

        status = request.POST.get("status") == "on"

        if Employee.objects.filter(email=email).exists():
            messages.error(
                request,
                "Employee with this email already exists."
            )
            return redirect("employee_create")

        # Create Django User
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name
        )

        # Disable password until employee creates one
        user.set_unusable_password()
        user.save()

        # Create Employee
        employee = Employee.objects.create(
            user=user,
            employee_id=employee_id,
            name=name,
            email=email,
            phone=phone,
            department_id=department_id,
            designation_id=designation_id,
            joining_date=joining_date,
            employment_type=employment_type,
            salary=salary,
            address=address,
            status=status
        )

        # Generate password setup token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Password setup URL
        setup_link = request.build_absolute_uri(
            reverse(
                "set_password",
                kwargs={
                    "uidb64": uid,
                    "token": token
                }
            )
        )

        # Send email
        send_mail(
            subject="CrewConnect - Set Your Password",
            message=f"""
Hello {name},

Your CrewConnect employee account has been created.

Please click the link below to create your password:

{setup_link}

After setting your password, you can log in to CrewConnect.

Regards,
CrewConnect HR
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return redirect("employee_list")

    return render(
        request,
        "employee_add_update.html",
        {
            "departments": departments,
            "designations": designations,
            "employment_types": Employee.EMPLOYMENT_TYPES,
            "is_update": False,
        }
    )

@login_required
@never_cache
def employee_update(request, id):

    employee = get_object_or_404(Employee,id=id)

    departments = Department.objects.all()
    designations = Designation.objects.all()

    if request.method == "POST":

        employee.employee_id = request.POST.get("employee_id")
        employee.name = request.POST.get("name")
        employee.email = request.POST.get("email")
        employee.phone = request.POST.get("phone")

        employee.department_id = request.POST.get("department")
        employee.designation_id = request.POST.get("designation")

        employee.joining_date = request.POST.get("joining_date")
        employee.employment_type = request.POST.get("employment_type")
        employee.salary = request.POST.get("salary")
        employee.address = request.POST.get("address")

        employee.status = request.POST.get("status") == "on"

        employee.save()

        return redirect(
            "employee_list"
        )

    return render(request,"employee_add_update.html",
        {
            "employee": employee,
            "departments": departments,
            "designations": designations,
            "employment_types": Employee.EMPLOYMENT_TYPES,
            "is_update": True,
        }
    )

@login_required
@never_cache
def employee_delete(request, id):
    employee = get_object_or_404(Employee,id=id)
    employee.status = not employee.status
    employee.save()
    return redirect("employee_list")


@login_required
def leave_approve(request):

    # Check whether logged-in user is an employee
    if Employee.objects.filter(user=request.user).exists():
        return redirect("employee_dashboard")

    leaves = Leave.objects.select_related(
        "employee",
        "employee__department",
        "employee__designation"
    ).order_by("-applied_date")

    return render(
        request,
        "leave_approval.html",
        {
            "leaves": leaves,
            "is_employee": False,
        }
    )


@login_required
def leave_action(request, id):

    # Employee cannot approve/reject
    if Employee.objects.filter(user=request.user).exists():
        return redirect("employee_dashboard")

    if request.method == "POST":

        leave = Leave.objects.get(id=id)

        action = request.POST.get("action")

        if action == "approve":

            leave.status = "Approved"
            leave.save()

        elif action == "reject":

            leave.status = "Rejected"
            leave.save()

    return redirect("leave_approve")

@login_required
def department_list(request):


   # Employee should not access department management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   departments = Department.objects.all().order_by("name")


   return render(
       request,
       "departments.html",
       {
           "departments": departments,
           "is_employee": False,
       }
   )




@login_required
def department_create(request):


   # Employee should not access department management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   if request.method == "POST":


       name = request.POST.get("name")


       if not name:
           messages.error(
               request,
               "Department name is required."
           )


           return redirect("department_list")


       if Department.objects.filter(
           name__iexact=name
       ).exists():


           messages.error(
               request,
               "Department already exists."
           )


           return redirect("department_list")


       Department.objects.create(
           name=name
       )


       messages.success(
           request,
           "Department added successfully."
       )


       return redirect("department_list")


   return redirect("department_list")




@login_required
def department_update(request, id):


   # Employee should not access department management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   department = get_object_or_404(
       Department,
       id=id
   )


   if request.method == "POST":


       name = request.POST.get("name")


       if not name:


           messages.error(
               request,
               "Department name is required."
           )


           return redirect("department_list")


       if Department.objects.filter(
           name__iexact=name
       ).exclude(id=id).exists():


           messages.error(
               request,
               "Department already exists."
           )


           return redirect("department_list")


       department.name = name
       department.save()


       messages.success(
           request,
           "Department updated successfully."
       )


       return redirect("department_list")


   return redirect("department_list")




@login_required
def department_delete(request, id):


   # Employee should not access department management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   department = get_object_or_404(
       Department,
       id=id
   )


   if request.method == "POST":


       try:
           department.delete()


           messages.success(
               request,
               "Department deleted successfully."
           )


       except ProtectedError:


           messages.error(
               request,
               "This department cannot be deleted because employees are assigned to it."
           )


   return redirect("department_list")




@login_required
def department_detail(request, id):


   # Employee should not access department management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   department = get_object_or_404(
       Department,
       id=id
   )


   # Get employees belonging to this department
   employees = Employee.objects.select_related(
       "department",
       "designation"
   ).filter(
       department=department,
       status=True
   )


   return render(
       request,
       "Employee_list.html",
       {
           "employees": employees,
           "department": department,
           "is_employee": False,
       }
   )
@login_required
def designation_list(request):


   # Employee should not access designation management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   designations = Designation.objects.all().order_by("name")


   return render(
       request,
       "designations.html",
       {
           "designations": designations,
           "is_employee": False,
       }
   )




@login_required
def designation_create(request):


   # Employee should not access designation management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   if request.method == "POST":


       name = request.POST.get("name")


       if not name:
           messages.error(
               request,
               "Designation name is required."
           )
           return redirect("designation_list")


       if Designation.objects.filter(
           name__iexact=name
       ).exists():


           messages.error(
               request,
               "Designation already exists."
           )
           return redirect("designation_list")


       Designation.objects.create(
           name=name
       )


       messages.success(
           request,
           "Designation added successfully."
       )


       return redirect("designation_list")


   return redirect("designation_list")




@login_required
def designation_update(request, id):


   # Employee should not access designation management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   designation = get_object_or_404(
       Designation,
       id=id
   )


   if request.method == "POST":


       name = request.POST.get("name")


       if not name:
           messages.error(
               request,
               "Designation name is required."
           )
           return redirect("designation_list")


       if Designation.objects.filter(
           name__iexact=name
       ).exclude(id=id).exists():


           messages.error(
               request,
               "Designation already exists."
           )
           return redirect("designation_list")


       designation.name = name
       designation.save()


       messages.success(
           request,
           "Designation updated successfully."
       )


       return redirect("designation_list")


   return redirect("designation_list")




@login_required
def designation_delete(request, id):


   # Employee should not access designation management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   designation = get_object_or_404(
       Designation,
       id=id
   )


   if request.method == "POST":


       try:


           designation.delete()


           messages.success(
               request,
               "Designation deleted successfully."
           )


       except ProtectedError:


           messages.error(
               request,
               "This designation cannot be deleted because employees are assigned to it."
           )


   return redirect("designation_list")




@login_required
def designation_detail(request, id):


   # Employee should not access designation management
   if Employee.objects.filter(user=request.user).exists():
       return redirect("employee_dashboard")


   designation = get_object_or_404(
       Designation,
       id=id
   )


   employees = Employee.objects.select_related(
       "department",
       "designation"
   ).filter(
       designation=designation,
       status=True
   )


   return render(
       request,
       "Employee_list.html",
       {
           "employees": employees,
           "designation": designation,
           "is_employee": False,
       }
   )
