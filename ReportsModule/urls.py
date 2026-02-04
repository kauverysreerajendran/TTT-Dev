from django.urls import path
from .views import *

app_name = 'reports_module'

urlpatterns = [
  
    path('reports/', ReportsView.as_view(), name='reports'),
    path('download_report/', download_report, name='download_report'),

]



