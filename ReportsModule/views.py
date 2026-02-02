from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from modelmasterapp.models import *
from Recovery_DP.models import *
from django.core.paginator import Paginator

class ReportsView(TemplateView):
    template_name = "ModelMaster/Report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch all model_no values from ModelMaster
        context['model_list'] = ModelMaster.objects.values_list('model_no', flat=True)

        # Get filter parameters
        lot_id = self.request.GET.get('lot_id')
        batch_id = self.request.GET.get('batch_id')
        model_no = self.request.GET.get('model_no')
        department = self.request.GET.get('department')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        # Pagination parameters
        page_number = self.request.GET.get('page', 1)
        try:
            page_number = int(page_number)
        except ValueError:
            page_number = 1
        
        page_size = 10

        # Get batch details data (Paginated)
        data_response = self.get_batch_details_data(
            lot_id, batch_id, model_no, department, date_from, date_to, page_number, page_size
        )

        batch_details = data_response['data']
        total_count = data_response['total_count']

        # Manual Paginator Creation for Template Compatibility
        # We create a paginator over a range of numbers equal to the total count
        # This allows us to generate the correct page links without fetching all data
        paginator = Paginator(range(total_count), page_size)
        try:
            page_obj = paginator.page(page_number)
        except:
            page_obj = paginator.page(1)
        
        context['page_obj'] = page_obj
        context['batch_details'] = batch_details # The actual data for the current page
        
        # Preserve filter parameters for pagination links
        context['lot_id'] = lot_id
        context['batch_id'] = batch_id
        context['model_no'] = model_no
        context['department'] = department
        context['date_from'] = date_from
        context['date_to'] = date_to

        return context

    def get_batch_details_data(self, lot_id, batch_id, model_no, department, date_from, date_to, page, page_size):
        """
        Get batch details data with segmented pagination.
        Avoids loading all records into memory.
        """
        # Department mapping
        department_mapping = {
            'day-planning': 'Day Planning',
            'input-screening': 'Input Screening',
            'brass-qc': 'Brass QC',
            'brass-audit': 'Brass Audit',
            'iqf': 'IQF',
            'recovery-day-planning': 'Recovery Day Planning',
            'recovery-input-screening': 'Recovery Input Screening',
            'recovery-brass-qc': 'Recovery Brass QC',
            'recovery-brass-audit': 'RecoveryBrass Audit',
            'recovery-iqf': 'Recovery IQF',
            'jig-loading': 'JIG Loading',
            'inprocess-inspection': 'Inprocess Inspection',
            'jig-unloading': 'Jig Unloading',
            'nickel-inspection': 'Nickel Inspection',
            'nickel-audit': 'Nickel Audit',
            'spider-spindle': 'Spider Loading'
        }

        department_name = department_mapping.get(department)

        # 1. Prepare QuerySets for each data source
        
        # Source A: ModelMasterCreation (Day Planning)
        qs_dp = ModelMasterCreation.objects.filter(Moved_to_D_Picker=False).select_related('model_stock_no', 'version')
        
        # Source B: RecoveryMasterCreation (Recovery Day Planning)
        qs_rec_dp = RecoveryMasterCreation.objects.filter(Moved_to_D_Picker=False).select_related('model_stock_no', 'version')
        
        # Source C: TotalStockModel (Other Stages)
        qs_stock = TotalStockModel.objects.all().select_related('model_stock_no', 'version', 'batch_id')
        
        # Source D: RecoveryStockModel (Recovery Other Stages)
        qs_rec_stock = RecoveryStockModel.objects.all().select_related('model_stock_no', 'version', 'batch_id')

        # 2. Apply Filters to QuerySets
        
        # Filter: Batch ID / Lot ID
        if lot_id:
            qs_dp = qs_dp.filter(lot_id=lot_id)
            qs_rec_dp = qs_rec_dp.filter(lot_id=lot_id)
            qs_stock = qs_stock.filter(lot_id=lot_id)
            qs_rec_stock = qs_rec_stock.filter(lot_id=lot_id)
        elif batch_id:
            qs_dp = qs_dp.filter(batch_id=batch_id)
            qs_rec_dp = qs_rec_dp.filter(batch_id=batch_id)
            
            # For stock tables, we need to filter by the related batch objects or by finding the batch_id manually
            # Since batch_id in Stock models is FK to MasterCreation, we can filter directly if we have the ID,
            # but user passes the string ID.
            
            # Efficient: Filter stock based on batch_id string via the FK relation
            qs_stock = qs_stock.filter(batch_id__batch_id=batch_id)
            qs_rec_stock = qs_rec_stock.filter(batch_id__batch_id=batch_id)

        # Filter: Model No
        if model_no:
            qs_dp = qs_dp.filter(model_stock_no__model_no=model_no)
            qs_rec_dp = qs_rec_dp.filter(model_stock_no__model_no=model_no)
            qs_stock = qs_stock.filter(model_stock_no__model_no=model_no)
            qs_rec_stock = qs_rec_stock.filter(model_stock_no__model_no=model_no)

        # Filter: Date Range
        if date_from:
            qs_dp = qs_dp.filter(date_time__date__gte=date_from)
            qs_rec_dp = qs_rec_dp.filter(date_time__date__gte=date_from)
            # For stock, strict requirement typically uses the batch creation date
            qs_stock = qs_stock.filter(batch_id__date_time__date__gte=date_from)
            qs_rec_stock = qs_rec_stock.filter(batch_id__date_time__date__gte=date_from)
            
        if date_to:
            qs_dp = qs_dp.filter(date_time__date__lte=date_to)
            qs_rec_dp = qs_rec_dp.filter(date_time__date__lte=date_to)
            qs_stock = qs_stock.filter(batch_id__date_time__date__lte=date_to)
            qs_rec_stock = qs_rec_stock.filter(batch_id__date_time__date__lte=date_to)

        # 3. Determine Active Sources based on Department Filter
        active_sources = []
        
        # Helper to add source
        def add_source(qs, source_type):
            active_sources.append({'qs': qs.order_by('-date_time') if 'date_time' in [f.name for f in qs.model._meta.fields] else qs.order_by('-id'), 'type': source_type})

        is_all = (not department or department == 'all') and not lot_id and not batch_id

        # Logic for "Day Planning"
        if is_all or department_name == 'Day Planning':
            add_source(qs_dp, 'DP')
            
        # Logic for "Recovery Day Planning"
        if is_all or department_name == 'Recovery Day Planning':
            add_source(qs_rec_dp, 'R_DP')

        # Logic for Other Stages
        # If searching specifically by ID, we might check all tables or fallback to logic. 
        # The original code's logic was: check everything if 'all', else check specific.
        # But if lot_id/batch_id is present, it checked everything.
        
        force_check_all = bool(lot_id or batch_id)

        if force_check_all:
             # When filtering by ID, include all relevant sources
            add_source(qs_dp, 'DP')
            add_source(qs_rec_dp, 'R_DP')
            add_source(qs_stock, 'STOCK')
            add_source(qs_rec_stock, 'R_STOCK')
            # Remove duplicates if any logic added them twice (re-building list is safer)
            # Simplified: Just rebuild list for this case
            active_sources = []
            add_source(qs_dp, 'DP')
            add_source(qs_rec_dp, 'R_DP')
            add_source(qs_stock, 'STOCK')
            add_source(qs_rec_stock, 'R_STOCK')

        elif not is_all and department_name:
             if department_name not in ['Day Planning', 'Recovery Day Planning']:
                 # Specific stage filter for Stock tables
                 qs_stock_filtered = qs_stock.filter(last_process_module=department_name)
                 qs_rec_stock_filtered = qs_rec_stock.filter(last_process_module=department_name)
                 add_source(qs_stock_filtered, 'STOCK')
                 add_source(qs_rec_stock_filtered, 'R_STOCK')
        
        elif is_all:
             add_source(qs_stock, 'STOCK')
             add_source(qs_rec_stock, 'R_STOCK')


        # 4. Pagination / Slicing Logic
        # Calculate start and end indices for the requested page
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        current_offset = 0
        result_data = []
        
        # Calculate total count first (needed for paginator)
        # To optimize, we could cache counts, but for now we just count()
        # We also need to identify which sources overlap with our page slice
        
        total_count = 0
        source_counts = []
        
        for source in active_sources:
            count = source['qs'].count()
            source_counts.append(count)
            total_count += count
            
        # Fetch Data Phase
        current_idx = 0
        processed_count = 0
        
        for i, source in enumerate(active_sources):
            count = source_counts[i]
            
            # Check if this source overlaps with [start_index, end_index)
            source_start = current_idx
            source_end = current_idx + count
            
            if source_end > start_index and source_start < end_index:
                # Calculate slice relative to this queryset
                slice_start = max(0, start_index - source_start)
                slice_end = max(0, end_index - source_start)
                
                # Fetch objects
                objs = list(source['qs'][slice_start:slice_end])
                
                # Process objects
                for obj in objs:
                    formatted_row = self.format_row(obj, source['type'])
                    # Add Serial Number (Global Index)
                    # Global Index = start_index_global + iteration_index
                    # start_index is the 0-based offset of the first item on this page
                    # processed_count tracks how many items we've already added to result_data
                    global_s_no = start_index + processed_count + 1
                    formatted_row['s_no'] = global_s_no
                    
                    result_data.append(formatted_row)
                    processed_count += 1
            
            current_idx += count
            
            # Optimization: If we've filled the page, break (though loop logic naturally handles it)
            if current_idx >= end_index:
                break

        return {
            'data': result_data,
            'total_count': total_count
        }

    def format_row(self, obj, source_type):
        """Helper to format a single row based on its source type"""
        row = {}
        if source_type == 'DP':
            row = {
                'batch_id': obj.batch_id,
                'onboard_date': obj.date_time.strftime('%Y-%m-%d'),
                'model_no': obj.model_stock_no.model_no,
                'version': obj.version.version_name,
                'quantity': obj.total_batch_quantity,
                'current_stage': "Day Planning",
                'status': "Yet To Start",
            }
        elif source_type == 'R_DP':
             row = {
                'batch_id': obj.batch_id,
                'onboard_date': obj.date_time.strftime('%Y-%m-%d'),
                'model_no': obj.model_stock_no.model_no,
                'version': obj.version.version_name,
                'quantity': obj.total_batch_quantity,
                'current_stage': "Recovery Day Planning",
                'status': "Yet To Start",
            }
        elif source_type in ['STOCK', 'R_STOCK']:
             # Logic for Stock Models
             # Determine Status
            status = "Yet To Start"
            
            # Access related batch object efficiently
            # Note: select_related('batch_id') was used, so obj.batch_id doesn't hit DB
            batch_obj = obj.batch_id 
            
            current_stage = obj.last_process_module or ''
            last_process_module = obj.last_process_module or ''
             
            if source_type == 'STOCK':
                if current_stage == "Day Planning" and batch_obj and batch_obj.Moved_to_D_Picker:
                    status = "Released"
                elif last_process_module == "Input Screening" and obj.ip_person_qty_verified:
                    status = "Released"
                elif current_stage == "Brass QC" and obj.brass_qc_accepted_qty_verified:
                    status = "Released"
                elif current_stage == "Brass Audit" and obj.brass_audit_accepted_qty_verified:
                    status = "Released"
                elif current_stage == "IQF" and obj.iqf_accepted_qty_verified:
                    status = "Released"
            else: # R_STOCK
                if current_stage == "Recovery Day Planning" and batch_obj and batch_obj.Moved_to_D_Picker:
                    status = "Released"
                elif last_process_module == "Recovery Input Screening" and obj.ip_person_qty_verified:
                    status = "Released"
                elif current_stage == "Recovery Brass QC" and obj.brass_qc_accepted_qty_verified:
                    status = "Released"
                elif current_stage == "RecoveryBrass Audit" and obj.brass_audit_accepted_qty_verified:
                    status = "Released"
                elif current_stage == "Recovery IQF" and obj.iqf_accepted_qty_verified:
                    status = "Released"
            
            row = {
                'batch_id': batch_obj.batch_id if batch_obj else '',
                'onboard_date': batch_obj.date_time.strftime('%Y-%m-%d') if batch_obj else '',
                'model_no': obj.model_stock_no.model_no,
                'version': obj.version.version_name,
                'quantity': obj.total_stock,
                'current_stage': current_stage,
                'status': status,
            }
            
        return row


def get_batch_details(request):
    """AJAX endpoint for JavaScript filters"""
    lot_id = request.GET.get('lot_id')
    batch_id = request.GET.get('batch_id')
    model_no = request.GET.get('model_no')
    department = request.GET.get('department')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Pagination parameters
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    
    reports_view = ReportsView()
    # ReportsView instance specific call might need request attached or manual method call
    # Ideally should make get_batch_details_data static or standalone, but it is instance method
    # Attached request is not strictly needed for the calculation method
    reports_view.request = request 
    
    data_response = reports_view.get_batch_details_data(
        lot_id, batch_id, model_no, department, date_from, date_to, page, page_size
    )
    
    # For AJAX, we return the list directly as before, or the full object?
    # Existing JS expects a list of rows. 
    # If the JS handles pagination, it might expect just the data.
    # However, if we want to update total counts in JS, we might need a richer response.
    # Analyzing current JS: "renderProcessFlow(data)" "fetch(url).then(res => res.json())"
    # Wait, the JS in Report.html calls `get_stage_counts`, NOT `get_batch_details`.
    # The `get_batch_details` view seems to be for the TABLE update?
    # Checking existing templates... `Report.html` uses a FORM submit for filters (`method="GET" action="{% url 'reports' %}"`).
    # It reloads the page.
    # Is there any JS calling `get_batch_details`?
    # Searching provided files... I don't see `get_batch_details` being called in the provided snippet of Report.html.
    # It seems the page works primarily by reload (Django Template View).
    # IF there is a legacy JS file using it, we should maintain compatibility or update it.
    # Assuming standard behavior, returning the LIST `data_response['data']` is safest for backward compat if JS expects list.
    
    return JsonResponse(data_response['data'], safe=False)


from django.http import JsonResponse
from collections import Counter

def get_stage_counts(request):
    model_no = request.GET.get('model_no')
    department = request.GET.get('department')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    stage_counts = Counter()
    
    # Department mapping from filter values to actual process module names
    department_mapping = {
        'day-planning': 'Day Planning',
        'input-screening': 'Input Screening',
        'brass-qc': 'Brass QC',
        'brass-audit': 'Brass Audit',
        'iqf': 'IQF',
        'recovery-day-planning': 'Recovery Day Planning',
        'recovery-input-screening': 'Recovery Input Screening',
        'recovery-brass-qc': 'Recovery Brass QC',
        'recovery-brass-audit': 'RecoveryBrass Audit',
        'recovery-iqf': 'Recovery IQF',
        'jig-loading': 'JIG Loading',
        'inprocess-inspection': 'Inprocess Inspection',
        'jig-unloading': 'Jig Unloading',
        'nickel-inspection': 'Nickel Inspection',
        'nickel-audit': 'Nickel Audit',
        'spider-spindle': 'Spider Loading'
    }
    
    # Special handling for Day Planning department
    if department == 'day-planning':
        # Get data from ModelMasterCreation and RecoveryMasterCreation tables where Moved_to_D_Picker is FALSE
        master_objs = ModelMasterCreation.objects.filter(Moved_to_D_Picker=False)
        recovery_master_objs = RecoveryMasterCreation.objects.filter(Moved_to_D_Picker=False)
        
        if model_no:
            master_objs = master_objs.filter(model_stock_no__model_no=model_no)
            recovery_master_objs = recovery_master_objs.filter(model_stock_no__model_no=model_no)
        
        # Apply date filters
        if date_from:
            master_objs = master_objs.filter(date_time__date__gte=date_from)
            recovery_master_objs = recovery_master_objs.filter(date_time__date__gte=date_from)
        if date_to:
            master_objs = master_objs.filter(date_time__date__lte=date_to)
            recovery_master_objs = recovery_master_objs.filter(date_time__date__lte=date_to)
        
        # For Day Planning stage, next stage would typically be Input Screening
        for obj in master_objs:
            stage_counts["Input Screening"] += 1
            
        # For Recovery Day Planning stage, next stage would typically be Recovery Input Screening  
        for obj in recovery_master_objs:
            stage_counts["Recovery Input Screening"] += 1
            
        return JsonResponse(stage_counts, safe=False)
    
    # Handle "All Departments" case - show all stages
    if not department or department == 'all':
        # Always show data even if no model is selected
        if not model_no:
            # No model filter, show all data from all tables
            
            # Day Planning data from ModelMasterCreation
            master_objs = ModelMasterCreation.objects.filter(Moved_to_D_Picker=False)
            recovery_master_objs = RecoveryMasterCreation.objects.filter(Moved_to_D_Picker=False)
            
            # All other data from stock tables
            total_stock_objs = TotalStockModel.objects.all()
            recovery_stock_objs = RecoveryStockModel.objects.all()
        else:
            # Model filter applied, show all data for that model
            master_objs = ModelMasterCreation.objects.filter(Moved_to_D_Picker=False, model_stock_no__model_no=model_no)
            recovery_master_objs = RecoveryMasterCreation.objects.filter(Moved_to_D_Picker=False, model_stock_no__model_no=model_no)
            total_stock_objs = TotalStockModel.objects.filter(model_stock_no__model_no=model_no)
            recovery_stock_objs = RecoveryStockModel.objects.filter(model_stock_no__model_no=model_no)
        
        # Apply date filters
        if date_from or date_to:
            if date_from:
                master_objs = master_objs.filter(date_time__date__gte=date_from)
                recovery_master_objs = recovery_master_objs.filter(date_time__date__gte=date_from)
                total_stock_objs = total_stock_objs.filter(batch_id__in=ModelMasterCreation.objects.filter(date_time__date__gte=date_from).values_list('id', flat=True))
                recovery_stock_objs = recovery_stock_objs.filter(batch_id__in=RecoveryMasterCreation.objects.filter(date_time__date__gte=date_from).values_list('id', flat=True))
            if date_to:
                master_objs = master_objs.filter(date_time__date__lte=date_to)
                recovery_master_objs = recovery_master_objs.filter(date_time__date__lte=date_to)
                total_stock_objs = total_stock_objs.filter(batch_id__in=ModelMasterCreation.objects.filter(date_time__date__lte=date_to).values_list('id', flat=True))
                recovery_stock_objs = recovery_stock_objs.filter(batch_id__in=RecoveryMasterCreation.objects.filter(date_time__date__lte=date_to).values_list('id', flat=True))
        
        # Count Day Planning stages
        for obj in master_objs:
            stage_counts["Input Screening"] += 1
        for obj in recovery_master_objs:
            stage_counts["Recovery Input Screening"] += 1
            
        # Count other stages
        for obj in total_stock_objs:
            stage = obj.next_process_module or "Unknown"
            stage_counts[stage] += 1
        for obj in recovery_stock_objs:
            stage = obj.next_process_module or "Unknown"
            stage_counts[stage] += 1
            
        return JsonResponse(stage_counts, safe=False)
    
    # If model is provided but specific department is selected
    if model_no:
        # Get querysets
        total_stock_objs = TotalStockModel.objects.filter(model_stock_no__model_no=model_no)
        recovery_stock_objs = RecoveryStockModel.objects.filter(model_stock_no__model_no=model_no)
        
        # Apply date filters by joining with ModelMasterCreation
        if date_from or date_to:
            if date_from:
                total_stock_objs = total_stock_objs.filter(batch_id__in=ModelMasterCreation.objects.filter(date_time__date__gte=date_from).values_list('id', flat=True))
                recovery_stock_objs = recovery_stock_objs.filter(batch_id__in=RecoveryMasterCreation.objects.filter(date_time__date__gte=date_from).values_list('id', flat=True))
            if date_to:
                total_stock_objs = total_stock_objs.filter(batch_id__in=ModelMasterCreation.objects.filter(date_time__date__lte=date_to).values_list('id', flat=True))
                recovery_stock_objs = recovery_stock_objs.filter(batch_id__in=RecoveryMasterCreation.objects.filter(date_time__date__lte=date_to).values_list('id', flat=True))
        
        # Apply department filter if specified
        if department and department in department_mapping:
            department_name = department_mapping[department]
            total_stock_objs = total_stock_objs.filter(last_process_module=department_name)
            recovery_stock_objs = recovery_stock_objs.filter(last_process_module=department_name)
        
        # Count stages in TotalStockModel
        for obj in total_stock_objs:
            stage = obj.next_process_module or "Unknown"
            stage_counts[stage] += 1
        # Count stages in RecoveryStockModel
        for obj in recovery_stock_objs:
            stage = obj.next_process_module or "Unknown"
            stage_counts[stage] += 1
            
    # Fallback: if no specific filters and no data found, show all available stages
    if not stage_counts and not model_no and (not department or department == 'all'):
        # Show all available data as fallback
        all_total_stock = TotalStockModel.objects.all()
        all_recovery_stock = RecoveryStockModel.objects.all()
        all_master = ModelMasterCreation.objects.filter(Moved_to_D_Picker=False)
        all_recovery_master = RecoveryMasterCreation.objects.filter(Moved_to_D_Picker=False)
        
        for obj in all_master:
            stage_counts["Input Screening"] += 1
        for obj in all_recovery_master:
            stage_counts["Recovery Input Screening"] += 1
        for obj in all_total_stock:
            stage = obj.next_process_module or "Unknown"
            stage_counts[stage] += 1
        for obj in all_recovery_stock:
            stage = obj.next_process_module or "Unknown"
            stage_counts[stage] += 1
            
    return JsonResponse(stage_counts, safe=False)