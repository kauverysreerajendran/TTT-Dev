from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from modelmasterapp.models import *
from Recovery_DP.models import *
from DayPlanning.models import DPTrayId_History
from InputScreening.models import IPTrayId, IP_Accepted_TrayScan, IP_Rejected_TrayScan, IP_Accepted_TrayID_Store
from Brass_QC.models import BrassTrayId, Brass_Qc_Accepted_TrayScan, Brass_QC_Rejected_TrayScan, Brass_Qc_Accepted_TrayID_Store
from IQF.models import IQFTrayId, IQF_Accepted_TrayScan, IQF_Rejected_TrayScan, IQF_Accepted_TrayID_Store
from BrassAudit.models import BrassAuditTrayId, Brass_Audit_Accepted_TrayScan, Brass_Audit_Rejected_TrayScan, Brass_Audit_Accepted_TrayID_Store
from django.core.paginator import Paginator
import pandas as pd
from io import BytesIO
from datetime import datetime

def convert_datetimes(data):
    for item in data:
        for key, value in item.items():
            if isinstance(value, datetime) and value.tzinfo is not None:
                item[key] = value.replace(tzinfo=None)
    return data

class ReportsView(TemplateView):
    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # List of available modules for reports
        context['modules'] = [
            {'value': 'day-planning', 'label': 'Day Planning'},
            {'value': 'input-screening', 'label': 'Input Screening'},
            {'value': 'brass-qc', 'label': 'Brass QC'},
            {'value': 'iqf', 'label': 'IQF'},
            {'value': 'brass-audit', 'label': 'Brass Audit'},
            {'value': 'recovery-day-planning', 'label': 'Recovery Day Planning'},
            {'value': 'recovery-input-screening', 'label': 'Recovery Input Screening'},
            {'value': 'recovery-brass-qc', 'label': 'Recovery Brass QC'},
            {'value': 'recovery-iqf', 'label': 'Recovery IQF'},
            {'value': 'recovery-brass-audit', 'label': 'Recovery Brass Audit'},
            {'value': 'jig-loading', 'label': 'Jig Loading'},
            {'value': 'inprocess-inspection', 'label': 'Inprocess Inspection'},
            {'value': 'jig-unloading', 'label': 'Jig Unloading'},
            {'value': 'nickel-inspection', 'label': 'Nickel Inspection'},
            {'value': 'nickel-audit', 'label': 'Nickel Audit'},
            {'value': 'spider-spindle', 'label': 'Spider Spindle'}
        ]
        return context
# Function for "Reports Module" to download Excel report based on selected module
def download_report(request):
    module = request.GET.get('module')
    if not module:
        return HttpResponse("Module not specified", status=400)

    # Create Excel file with multiple sheets
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if module == 'day-planning':
            # Pick Table
            dp_trays = list(DPTrayId_History.objects.all().values())
            for tray in dp_trays:
                if 'date' in tray and tray['date'] and tray['date'].tzinfo is not None:
                    tray['date'] = tray['date'].replace(tzinfo=None)
            pd.DataFrame(dp_trays).to_excel(writer, sheet_name='Pick Table', index=False)

            # Completed Table - assuming accepted tray IDs
            completed_trays = list(DPTrayId_History.objects.filter(scanned=True).values())
            for tray in completed_trays:
                if 'date' in tray and tray['date'] and tray['date'].tzinfo is not None:
                    tray['date'] = tray['date'].replace(tzinfo=None)
            pd.DataFrame(completed_trays).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'input-screening':
            # Pick Table
            ip_trays = convert_datetimes(list(IPTrayId.objects.all().values()))
            pd.DataFrame(ip_trays).to_excel(writer, sheet_name='Pick Table', index=False)

            # Accept Table
            accepted = convert_datetimes(list(IP_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)

            # Reject Table
            rejected = convert_datetimes(list(IP_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)

            # Completed Table
            completed = convert_datetimes(list(IP_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'brass-qc':
            # Pick Table
            brass_trays = convert_datetimes(list(BrassTrayId.objects.all().values()))
            pd.DataFrame(brass_trays).to_excel(writer, sheet_name='Pick Table', index=False)

            # Accept Table
            accepted = convert_datetimes(list(Brass_Qc_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)

            # Reject Table
            rejected = convert_datetimes(list(Brass_QC_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)

            # Completed Table
            completed = convert_datetimes(list(Brass_Qc_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'iqf':
            # Pick Table
            iqf_trays = convert_datetimes(list(IQFTrayId.objects.all().values()))
            pd.DataFrame(iqf_trays).to_excel(writer, sheet_name='Pick Table', index=False)

            # Accept Table
            accepted = convert_datetimes(list(IQF_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)

            # Reject Table
            rejected = convert_datetimes(list(IQF_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)

            # Completed Table
            completed = convert_datetimes(list(IQF_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'brass-audit':
            # Pick Table
            audit_trays = convert_datetimes(list(BrassAuditTrayId.objects.all().values()))
            pd.DataFrame(audit_trays).to_excel(writer, sheet_name='Pick Table', index=False)

            # Accept Table
            accepted = convert_datetimes(list(Brass_Audit_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)

            # Reject Table
            rejected = convert_datetimes(list(Brass_Audit_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)

            # Completed Table
            completed = convert_datetimes(list(Brass_Audit_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'recovery-day-planning':
            # Pick Table
            from Recovery_DP.models import RecoveryTrayId_History
            dp_trays = convert_datetimes(list(RecoveryTrayId_History.objects.all().values()))
            pd.DataFrame(dp_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Completed Table
            completed_trays = convert_datetimes(list(RecoveryTrayId_History.objects.filter(scanned=True).values()))
            pd.DataFrame(completed_trays).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'recovery-input-screening':
            # Pick Table
            from Recovery_IS.models import RecoveryIPTrayId
            ip_trays = convert_datetimes(list(RecoveryIPTrayId.objects.all().values()))
            pd.DataFrame(ip_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Accept Table
            from Recovery_IS.models import RecoveryIP_Accepted_TrayScan
            accepted = convert_datetimes(list(RecoveryIP_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)
            
            # Reject Table
            from Recovery_IS.models import RecoveryIP_Rejected_TrayScan
            rejected = convert_datetimes(list(RecoveryIP_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)
            
            # Completed Table
            from Recovery_IS.models import RecoveryIP_Accepted_TrayID_Store
            completed = convert_datetimes(list(RecoveryIP_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'recovery-brass-qc':
            # Pick Table
            from Recovery_Brass_QC.models import BrassTrayId as RecoveryBrassTrayId
            brass_trays = convert_datetimes(list(RecoveryBrassTrayId.objects.all().values()))
            pd.DataFrame(brass_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Accept Table
            from Recovery_Brass_QC.models import Brass_Qc_Accepted_TrayScan as RecoveryBrass_Qc_Accepted_TrayScan
            accepted = convert_datetimes(list(RecoveryBrass_Qc_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)
            
            # Reject Table
            from Recovery_Brass_QC.models import Brass_QC_Rejected_TrayScan as RecoveryBrass_QC_Rejected_TrayScan
            rejected = convert_datetimes(list(RecoveryBrass_QC_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)
            
            # Completed Table
            from Recovery_Brass_QC.models import Brass_Qc_Accepted_TrayID_Store as RecoveryBrass_Qc_Accepted_TrayID_Store
            completed = convert_datetimes(list(RecoveryBrass_Qc_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'recovery-iqf':
            # Pick Table
            from Recovery_IQF.models import IQFTrayId as RecoveryIQFTrayId
            iqf_trays = convert_datetimes(list(RecoveryIQFTrayId.objects.all().values()))
            pd.DataFrame(iqf_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Accept Table
            from Recovery_IQF.models import IQF_Accepted_TrayScan as RecoveryIQF_Accepted_TrayScan
            accepted = convert_datetimes(list(RecoveryIQF_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)
            
            # Reject Table
            from Recovery_IQF.models import IQF_Rejected_TrayScan as RecoveryIQF_Rejected_TrayScan
            rejected = convert_datetimes(list(RecoveryIQF_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)
            
            # Completed Table
            from Recovery_IQF.models import IQF_Accepted_TrayID_Store as RecoveryIQF_Accepted_TrayID_Store
            completed = convert_datetimes(list(RecoveryIQF_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'recovery-brass-audit':
            # Pick Table
            from Recovery_BrassAudit.models import BrassAuditTrayId as RecoveryBrassAuditTrayId
            audit_trays = convert_datetimes(list(RecoveryBrassAuditTrayId.objects.all().values()))
            pd.DataFrame(audit_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Accept Table
            from Recovery_BrassAudit.models import Brass_Audit_Accepted_TrayScan as RecoveryBrass_Audit_Accepted_TrayScan
            accepted = convert_datetimes(list(RecoveryBrass_Audit_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)
            
            # Reject Table
            from Recovery_BrassAudit.models import Brass_Audit_Rejected_TrayScan as RecoveryBrass_Audit_Rejected_TrayScan
            rejected = convert_datetimes(list(RecoveryBrass_Audit_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)
            
            # Completed Table
            from Recovery_BrassAudit.models import Brass_Audit_Accepted_TrayID_Store as RecoveryBrass_Audit_Accepted_TrayID_Store
            completed = convert_datetimes(list(RecoveryBrass_Audit_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'jig-loading':
            # Pick Table
            from Jig_Loading.models import JigLoadTrayId
            jig_trays = convert_datetimes(list(JigLoadTrayId.objects.all().values()))
            pd.DataFrame(jig_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # For jig loading, completed might be the same as pick table
            completed_trays = convert_datetimes(list(JigLoadTrayId.objects.all().values()))
            pd.DataFrame(completed_trays).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'inprocess-inspection':
            # Inprocess inspection might not have separate tables, just use a placeholder
            pd.DataFrame([{'message': 'Inprocess Inspection data not implemented yet'}]).to_excel(writer, sheet_name='Data', index=False)

        elif module == 'jig-unloading':
            # Similar to jig loading
            pd.DataFrame([{'message': 'Jig Unloading data not implemented yet'}]).to_excel(writer, sheet_name='Data', index=False)

        elif module == 'nickel-inspection':
            # Pick Table
            from Nickel_Inspection.models import NickelQcTrayId
            nickel_trays = convert_datetimes(list(NickelQcTrayId.objects.all().values()))
            pd.DataFrame(nickel_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Accept Table
            from modelmasterapp.models import Nickle_IP_Accepted_TrayScan
            accepted = convert_datetimes(list(Nickle_IP_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)
            
            # Reject Table
            from modelmasterapp.models import Nickle_IP_Rejected_TrayScan
            rejected = convert_datetimes(list(Nickle_IP_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)
            
            # Completed Table
            from modelmasterapp.models import Nickle_IP_Accepted_TrayID_Store
            completed = convert_datetimes(list(Nickle_IP_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'nickel-audit':
            # Pick Table
            from Nickel_Audit.models import Nickel_AuditTrayId
            nickel_audit_trays = convert_datetimes(list(Nickel_AuditTrayId.objects.all().values()))
            pd.DataFrame(nickel_audit_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Accept Table
            from modelmasterapp.models import Nickle_Audit_Accepted_TrayScan
            accepted = convert_datetimes(list(Nickle_Audit_Accepted_TrayScan.objects.all().values()))
            pd.DataFrame(accepted).to_excel(writer, sheet_name='Accept Table', index=False)
            
            # Reject Table
            from modelmasterapp.models import Nickle_Audit_Rejected_TrayScan
            rejected = convert_datetimes(list(Nickle_Audit_Rejected_TrayScan.objects.all().values()))
            pd.DataFrame(rejected).to_excel(writer, sheet_name='Reject Table', index=False)
            
            # Completed Table
            from modelmasterapp.models import Nickle_Audit_Accepted_TrayID_Store
            completed = convert_datetimes(list(Nickle_Audit_Accepted_TrayID_Store.objects.all().values()))
            pd.DataFrame(completed).to_excel(writer, sheet_name='Completed Table', index=False)

        elif module == 'spider-spindle':
            # Pick Table
            from Spider_Spindle.models import Spider_TrayId
            spider_trays = convert_datetimes(list(Spider_TrayId.objects.all().values()))
            pd.DataFrame(spider_trays).to_excel(writer, sheet_name='Pick Table', index=False)
            
            # Completed Table
            completed_trays = convert_datetimes(list(Spider_TrayId.objects.all().values()))
            pd.DataFrame(completed_trays).to_excel(writer, sheet_name='Completed Table', index=False)

    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={module}_report.xlsx'
    response['Content-Length'] = len(output.getvalue())
    # Clear buffer to prevent buffering
    output.close()
    return response