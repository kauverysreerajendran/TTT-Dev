from django.contrib import admin
from .models import *
#test
class ModelMasterAdmin(admin.ModelAdmin):
    list_display = ['model_no', 'brand', 'ep_bath_type', 'plating_stk_no']
    search_fields = ['model_no', 'brand', 'plating_stk_no']
    list_filter = ['brand', 'ep_bath_type']

admin.site.register(ModelMaster, ModelMasterAdmin)
admin.site.register(PolishFinishType)
admin.site.register(TrayType)
admin.site.register(Vendor) 
admin.site.register(ModelMasterCreation)
admin.site.register(Version)
admin.site.register(Location)
admin.site.register(Category)
admin.site.register(TrayId)
admin.site.register(DraftTrayId)

admin.site.register(ModelImage)
admin.site.register(Plating_Color)
admin.site.register(TotalStockModel)
admin.site.register(DP_TrayIdRescan)

admin.site.register(TrayAutoSaveData)
admin.site.register(LookLikeModel)
