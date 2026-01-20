import os
import django

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchcase_tracker.settings')  # Replace 'your_project_name' with 'watchcase_tracker'
django.setup()

from modelmasterapp.models import *
from Jig_Loading.models import *
from Brass_QC.models import *

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

    print("✅ All specified model data deleted successfully.")

if __name__ == "__main__":
    clear_database()