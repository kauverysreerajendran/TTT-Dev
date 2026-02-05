import os
import django

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')  # Replace 'your_project_name' with 'watchcase_tracker'
django.setup()

from modelmasterapp.models import *
from Jig_Loading.models import *
from Brass_QC.models import *
from BrassAudit.models import *
from InputScreening.models import *

def clear_database():
    """
    Deletes all records from the specified models.
    """
    # Delete all records
    TotalStockModel.objects.all().delete()
    ModelMasterCreation.objects.all().delete()
    TrayAutoSaveData.objects.all().delete()
    Jig.objects.all().delete()
    JigLoadingManualDraft.objects.all().delete()
    JigCompleted.objects.all().delete()
    JigAutoSave.objects.all().delete()
    Brass_QC_Draft_Store.objects.all().delete()
    TrayId.objects.all().delete()

    # Brass_QC additional tables
    Brass_TopTray_Draft_Store.objects.all().delete()
    Brass_QC_Rejected_TrayScan.objects.all().delete()
    Brass_QC_Rejection_ReasonStore.objects.all().delete()

    # BrassAudit tables
    BrassAuditTrayId.objects.all().delete()
    Brass_Audit_Accepted_TrayID_Store.objects.all().delete()
    Brass_Audit_Rejection_ReasonStore.objects.all().delete()

    # InputScreening tables
    IP_Accepted_TrayID_Store.objects.all().delete()
    IP_Rejected_TrayScan.objects.all().delete()
    IP_Rejection_ReasonStore.objects.all().delete()
    IP_Rejection_Draft.objects.all().delete()

    print("✅ All specified model data deleted successfully.")

if __name__ == "__main__":
    clear_database()