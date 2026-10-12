import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.utils.http import urlsafe_base64_decode


from hr.models import Leave, Employee

User = get_user_model()

def set_password(request, uidb64, token):

   try:
       uid = urlsafe_base64_decode(uidb64).decode()
       user = User.objects.get(pk=uid)
   except (TypeError, ValueError, OverflowError, User.DoesNotExist):
       user = None

   if user is None or not default_token_generator.check_token(user, token):
       return render(request, "invalid_link.html")




   if request.method == "POST":




       password = request.POST.get("password")
       confirm_password = request.POST.get("confirm_password")




       if password != confirm_password:
           messages.error(request, "Passwords do not match.")
           return redirect(
               "set_password",
               uidb64=uidb64,
               token=token
           )




       user.set_password(password)
       user.save()




       messages.success(
           request,
           "Password created successfully. You can now login."
       )




       return redirect("login")




   return render(request, "set_password.html")




@login_required
def employee_dashboard(request):




  employee = request.user.employee




  return render(request,"employee_dashboard.html",{
          "employee": employee,"is_employee": True,})




def employee_profile(request):
   employee = request.user.employee


   return render(request, "profile.html", {
       "employee": employee, "is_employee": True, })




def apply_leave(request):


   employee = request.user.employee


   if request.method == "POST":


       leave_type = request.POST.get("leave_type")
       start_date = request.POST.get("start_date")
       end_date = request.POST.get("end_date")
       reason = request.POST.get("reason")


       Leave.objects.create(
           employee=employee,
           leave_type=leave_type,
           start_date=start_date,
           end_date=end_date,
           reason=reason
       )


       messages.success(
           request,
           "Leave application submitted successfully."
       )


       return redirect("my_leaves")


   return render(
       request,
       "apply_leave.html",
       {
           "leave_types": Leave.LEAVE_TYPES,
           "is_employee": True,
       }
   )




@login_required
def my_leaves(request):


   employee = request.user.employee


   leaves = Leave.objects.filter(
       employee=employee
   ).order_by("-applied_date")


   return render(
       request,
       "my_leaves.html",
       {
           "leaves": leaves,
           "is_employee": True,
       }
   )




@login_required
def leave_calendar(request):
   """
   Renders a month-view calendar (FullCalendar) showing the
   logged-in employee's leave applications, color-coded by status.
   """


   # Colors used for each leave status on the calendar
   status_colors = {
       "Approved": "#28a745",   # green
       "Pending": "#ffc107",    # yellow
       "Rejected": "#dc3545",   # red
   }


   employee = request.user.employee


   leaves = Leave.objects.filter(employee=employee)


   events = []


   for leave in leaves:


       # FullCalendar treats the `end` date as exclusive for all-day
       # events, so we add one day to make the leave's last day show up.
       end_exclusive = leave.end_date + timedelta(days=1)


       events.append({
           "title": f"{leave.get_leave_type_display()} ({leave.status})",
           "start": leave.start_date.isoformat(),
           "end": end_exclusive.isoformat(),
           "color": status_colors.get(leave.status, "#6c757d"),
           "extendedProps": {
               "leave_type": leave.get_leave_type_display(),
               "status": leave.status,
               "reason": leave.reason,
               "start_date": leave.start_date.strftime("%d %b %Y"),
               "end_date": leave.end_date.strftime("%d %b %Y"),
           },
       })


   return render(
       request,
       "leave_calendar.html",
       {
           "is_employee": True,
           "leave_events": events,
       }
   )


