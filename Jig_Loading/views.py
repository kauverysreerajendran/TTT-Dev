from django.views.generic import *
from modelmasterapp.models import *
from .models import Jig, JigLoadingMaster, JigLoadTrayId, JigDetails, JigLoadingManualDraft
from rest_framework.decorators import *
from django.http import JsonResponse
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from math import ceil
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import logging
import json
import json




# Jig Loading Pick Table - Main View (display completed batch from Brass Audit Complete table)
@method_decorator(login_required, name='dispatch') 
class JigView(TemplateView):
    template_name = "JigLoading/Jig_Picktable.html"
    
    # No of Trays Calculation
    def get_tray_capacity(stock):
        # Try batch first
        if stock.batch_id and getattr(stock.batch_id, 'tray_capacity', None):
            return stock.batch_id.tray_capacity
        # Try model_master
        if stock.model_stock_no and getattr(stock.model_stock_no, 'tray_capacity', None):
            return stock.model_stock_no.tray_capacity
        # Try tray_type
        if stock.batch_id and hasattr(stock.batch_id, 'tray_type') and stock.batch_id.tray_type:
            try:
                tray_type_obj = TrayType.objects.get(tray_type=stock.batch_id.tray_type)
                return tray_type_obj.tray_capacity
            except TrayType.DoesNotExist:
                pass
        # Try JigLoadingMaster
        jig_master = JigLoadingMaster.objects.filter(model_stock_no=stock.model_stock_no).first()
        if jig_master and getattr(jig_master, 'tray_capacity', None):
            return jig_master.tray_capacity
        return None
    
    
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only show lots NOT completed (do not change row order)
        total_stock_qs = (
            TotalStockModel.objects.filter(brass_audit_accptance=True, Jig_Load_completed=False)
            | TotalStockModel.objects.filter(brass_audit_few_cases_accptance=True, Jig_Load_completed=False)
            | TotalStockModel.objects.filter(brass_audit_rejection=True, Jig_Load_completed=False)
            | TotalStockModel.objects.filter(jig_draft=True, Jig_Load_completed=False)  # Include partial draft lots
        )

        master_data = []
        for stock in total_stock_qs:
            plating_stk_no = (
                getattr(stock.batch_id, 'plating_stk_no', None)
                or getattr(stock.model_stock_no, 'plating_stk_no', None)
            )
            polishing_stk_no = (
                getattr(stock.batch_id, 'polishing_stk_no', None)
                or getattr(stock.model_stock_no, 'polishing_stk_no', None)
            )

            tray_capacity = JigView.get_tray_capacity(stock)
            jig_type = ''
            jig_capacity = ''
            if plating_stk_no:
                jig_master = JigLoadingMaster.objects.filter(model_stock_no__plating_stk_no=plating_stk_no).first()
                if jig_master:
                    jig_type = f"{jig_master.jig_capacity}-Jig"
                    jig_capacity = jig_master.jig_capacity

            lot_qty = stock.total_stock or 0
            no_of_trays = 0
            if tray_capacity and tray_capacity > 0:
                no_of_trays = (lot_qty // tray_capacity) + (1 if lot_qty % tray_capacity else 0)

            # --- Fix: Use jig_draft for correct lot status ---
            if getattr(stock, 'released_flag', False):
                lot_status = 'Yet to Released'
                lot_status_class = 'lot-status-yet-released'
            elif getattr(stock, 'jig_draft', False):
                lot_status = 'Draft'
                lot_status_class = 'lot-status-draft'
            else:
                lot_status = 'Yet to Start'
                lot_status_class = 'lot-status-yet'

            master_data.append({
                'batch_id': stock.batch_id.batch_id if stock.batch_id else '',
                'stock_lot_id': stock.lot_id,
                'plating_stk_no': plating_stk_no,
                'polishing_stk_no': polishing_stk_no,
                'plating_color': stock.plating_color.plating_color if stock.plating_color else '',
                'polish_finish': stock.polish_finish.polish_finish if stock.polish_finish else '',
                'version__version_internal': stock.version.version_internal if stock.version else '',
                'no_of_trays': no_of_trays,
                'display_qty': lot_qty,
                'jig_capacity': jig_capacity if jig_capacity else '',
                'jig_type': jig_type,
                'model_images': [img.master_image.url for img in stock.model_stock_no.images.all()] if stock.model_stock_no else [],
                'brass_audit_last_process_date_time': stock.brass_audit_last_process_date_time,
                'last_process_module': stock.last_process_module,
                'lot_status': lot_status,
                'lot_status_class': lot_status_class,
            })
        context['master_data'] = master_data
        return context 

# Tray Info API View
class TrayInfoView(APIView):
    def get(self, request, *args, **kwargs):
        lot_id = request.GET.get('lot_id')
        batch_id = request.GET.get('batch_id')
        trays = JigLoadTrayId.objects.filter(lot_id=lot_id, batch_id__batch_id=batch_id).values('tray_id', 'tray_quantity')
        tray_list = [{'tray_id': t['tray_id'], 'tray_quantity': t['tray_quantity']} for t in trays]
        return Response({'trays': tray_list})
       
# Tray Validation API View   
class TrayValidateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        batch_id = request.data.get('batch_id')
        lot_id = request.data.get('lot_id')
        tray_ids = request.data.get('tray_ids', [])
        if not batch_id or not lot_id:
            return Response({'validated': False, 'message': 'batch_id and lot_id required'}, status=status.HTTP_400_BAD_REQUEST)

        allocated_trays = JigLoadTrayId.objects.filter(
            lot_id=lot_id,
            batch_id__batch_id=batch_id
        ).values_list('tray_id', flat=True)
        allocated_tray_set = set(str(t) for t in allocated_trays)
        scanned_tray_set = set(str(t) for t in tray_ids)

        if not allocated_tray_set:
            return Response({'validated': False, 'message': 'No allocated trays found for this batch.'}, status=status.HTTP_400_BAD_REQUEST)

        if not scanned_tray_set.issubset(allocated_tray_set):
            invalid = scanned_tray_set - allocated_tray_set
            return Response({
                'validated': False,
                'message': f'Tray IDs not allocated: {", ".join(invalid)}',
                'allocated_trays': list(allocated_tray_set),
                'scanned_trays': list(scanned_tray_set)
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'validated': True, 'message': 'Tray validation successful'}, status=status.HTTP_200_OK)


# Class for "Add Model" button data
class JigAddModalDataView(TemplateView):
    """
    Comprehensive modal data preparation for "Add Jig" functionality.
    Handles all data selection, calculation, and validation logic.
    """
    def get(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        batch_id = request.GET.get('batch_id')
        lot_id = request.GET.get('lot_id')
        jig_qr_id = request.GET.get('jig_qr_id')
        # --- FIX: Only restore from draft if not supplied by user ---
        broken_hooks_param = request.GET.get('broken_hooks', None)
        broken_hooks = int(broken_hooks_param) if broken_hooks_param not in [None, ''] else 0

        try:
            draft = JigLoadingManualDraft.objects.get(
                batch_id=batch_id,
                lot_id=lot_id,
                user=request.user
            )
            # Only restore from draft if user did not supply a new value
            if (broken_hooks_param in [None, '']) and draft.draft_data.get('broken_buildup_hooks') is not None:
                broken_hooks = int(draft.draft_data.get('broken_buildup_hooks', 0))
                logger.info(f"🔄 Restored broken_hooks from draft: {broken_hooks}")
        except JigLoadingManualDraft.DoesNotExist:
            pass
        
        logger.info(f"🔍 JigAddModal: Processing batch_id={batch_id}, lot_id={lot_id}, jig_qr_id={jig_qr_id}, broken_hooks={broken_hooks}")
        
        # Fetch TotalStockModel for batch/lot
        stock = get_object_or_404(TotalStockModel, lot_id=lot_id)
        batch = stock.batch_id
        model_master = batch.model_stock_no if (batch and batch.model_stock_no) else stock.model_stock_no
        
        # Comprehensive plating_stk_no resolution logic
        plating_stk_no = self._resolve_plating_stock_number(batch, model_master)
        
        # Comprehensive data preparation
        modal_data = self._prepare_modal_data(request, batch, model_master, stock, jig_qr_id, lot_id, broken_hooks)

        # Calculate excess message if lot qty exceeds jig capacity
        lot_qty = stock.total_stock
        jig_capacity = modal_data.get('jig_capacity', 0)
        excess = max(0, lot_qty - jig_capacity)
        if excess > 0:
            # Automatically revise lot qty to jig_capacity and create new lot for excess
            remaining_cases = excess
            new_lot_id = f"LID{timezone.now().strftime('%d%m%Y%H%M%S')}{remaining_cases:04d}"
            TotalStockModel.objects.create(
                batch_id=stock.batch_id,
                model_stock_no=stock.model_stock_no,
                version=stock.version,
                total_stock=remaining_cases,
                polish_finish=stock.polish_finish,
                plating_color=stock.plating_color,
                lot_id=new_lot_id,
                created_at=timezone.now(),
                Jig_Load_completed=False,
                jig_draft=True,
                last_process_date_time=timezone.now(),
                last_process_module="Jig Loading",
            )
            # Update original stock to jig_capacity
            stock.total_stock = jig_capacity
            stock.save()
            excess = 0
        excess_message = f"{excess} cases are in excess" if excess > 0 else ""

        # Enhanced logging for debugging
        logger.info(f"📊 Modal data prepared: plating_stk_no={plating_stk_no}, jig_type={modal_data.get('jig_type')}, jig_capacity={modal_data.get('jig_capacity')}, broken_hooks={broken_hooks}")
        
        return JsonResponse({
            'form_title': f"Jig Loading / Plating Stock No: {plating_stk_no or 'N/A'}",
            'jig_id': jig_qr_id,
            'nickel_bath_type': modal_data.get('nickel_bath_type'),
            'tray_type': modal_data.get('tray_type'),
            'broken_buildup_hooks': modal_data.get('broken_buildup_hooks'),
            'empty_hooks': modal_data.get('empty_hooks'),
            'loaded_cases_qty': modal_data.get('loaded_cases_qty'),
            'effective_loaded_cases': modal_data.get('effective_loaded_cases', modal_data.get('loaded_cases_qty')),
            'lot_qty': lot_qty,
            'jig_capacity': modal_data.get('jig_capacity'),
            'jig_type': modal_data.get('jig_type'),
            'loaded_hooks': modal_data.get('loaded_hooks'),
            'add_model_enabled': modal_data.get('add_model_enabled'),
            'can_save': modal_data.get('can_save'),
            'model_images': modal_data.get('model_images'),
            'delink_table': modal_data.get('delink_table'),
            'logs': modal_data.get('logs'),
            'no_of_cycle': modal_data.get('no_of_cycle'),
            'plating_stk_no': plating_stk_no,
            'modal_validation': modal_data.get('modal_validation'),
            'ui_config': modal_data.get('ui_config'),
            'tray_distribution': modal_data.get('tray_distribution'),
            'half_filled_tray_cases': modal_data.get('half_filled_tray_cases', 0),
            'remaining_cases': modal_data.get('remaining_cases', 0),
            'excess_message': excess_message,
        })
    
    def _resolve_plating_stock_number(self, batch, model_master):
        """
        Centralized plating stock number resolution logic.
        Priority: ModelMasterCreation.plating_stk_no -> ModelMaster.plating_stk_no
        """
        plating_stk_no = ''
        if batch and batch.plating_stk_no:
            plating_stk_no = batch.plating_stk_no
        elif batch and batch.model_stock_no and batch.model_stock_no.plating_stk_no:
            plating_stk_no = batch.model_stock_no.plating_stk_no
        return plating_stk_no
    
    def _prepare_modal_data(self, request, batch, model_master, stock, jig_qr_id, lot_id, broken_hooks=0):
        """
        Comprehensive modal data preparation including all calculations and validations.
        """
        import logging
        import re
        logger = logging.getLogger(__name__)
        
        # Calculate max broken hooks based on jig ID prefix
        max_broken_hooks = 5  # default
        if jig_qr_id:
            match = re.match(r'J(\d+)-', jig_qr_id)
            if match:
                jig_capacity_from_id = int(match.group(1))
                max_broken_hooks = 10 if jig_capacity_from_id >= 144 else 5
                # Restrict broken_hooks to max allowed
                if broken_hooks > max_broken_hooks:
                    broken_hooks = max_broken_hooks
        
        # Initialize all modal data variables
        modal_data = {
            'nickel_bath_type': None,
            'tray_type': 'Normal',
            'broken_buildup_hooks': broken_hooks,
            'empty_hooks': 0,
            'loaded_cases_qty': 0,
            'jig_capacity': 0,
            'jig_type': None,
            'loaded_hooks': 0,
            'add_model_enabled': False,
            'model_images': [],
            'delink_table': [],
            'no_of_cycle': 1,
            'modal_validation': {},
            'ui_config': {},
            'can_save': False,
        }
        
        # Set max broken hooks in validation
        modal_data['modal_validation']['max_broken_hooks'] = max_broken_hooks
        
        # Get jig details if exists
        jig_details = None
        if jig_qr_id:
            jig_details = JigDetails.objects.filter(jig_qr_id=jig_qr_id, lot_id=lot_id).first()
        
        # Set initial loaded_cases_qty to 0 (no trays scanned yet)
        modal_data['loaded_cases_qty'] = 0
        
        # Calculate effective_loaded_cases based on broken hooks
        original_lot_qty = stock.total_stock or 0
        if broken_hooks > 0:
            # With broken hooks, effective quantity is original minus broken hooks
            modal_data['effective_loaded_cases'] = max(0, original_lot_qty - broken_hooks)
            logger.info(f"🔧 Broken hooks adjustment: original={original_lot_qty}, broken_hooks={broken_hooks}, effective={modal_data['effective_loaded_cases']}")
        else:
            # No broken hooks - use full lot quantity
            modal_data['effective_loaded_cases'] = original_lot_qty
        
        # Resolve plating stock number
        plating_stk_no = self._resolve_plating_stock_number(batch, model_master)
        
        # Fetch Jig Type and Capacity from JigLoadingMaster
        jig_master = JigLoadingMaster.objects.filter(model_stock_no=model_master).first()
        if jig_master:
            modal_data['jig_type'] = f"{jig_master.jig_capacity:03d}" if jig_master.jig_capacity else None
            modal_data['jig_capacity'] = jig_master.jig_capacity
        else:
            # No jig master found - use stock total as fallback  
            modal_data['jig_capacity'] = stock.total_stock or 0

        # Set tray type from batch
        modal_data['tray_type'] = batch.tray_type if batch else 'Normal'

        # Calculate tray capacity
        tray_capacity = batch.tray_capacity if batch and batch.tray_capacity else 12

        # Set tray type from batch
        modal_data['tray_type'] = batch.tray_type if batch else 'Normal'

        # Re-validate broken hooks based on actual jig capacity (fallback for when jig_qr_id is empty)
        if not jig_qr_id and modal_data['jig_capacity'] > 0:
            # Use actual jig capacity to determine max broken hooks
            max_broken_hooks = 10 if modal_data['jig_capacity'] >= 144 else 5
            # Restrict broken_hooks to max allowed
            if broken_hooks > max_broken_hooks:
                broken_hooks = max_broken_hooks
                modal_data['broken_buildup_hooks'] = broken_hooks
            # Update validation data
            modal_data['modal_validation']['max_broken_hooks'] = max_broken_hooks

        # Nickel Bath Type and jig calculations
        if jig_details:
            modal_data['nickel_bath_type'] = jig_details.ep_bath_type
            modal_data['broken_buildup_hooks'] = broken_hooks
            modal_data['loaded_cases_qty'] = jig_details.total_cases_loaded
            modal_data['loaded_hooks'] = jig_details.total_cases_loaded

            # --- FIX: Only allow empty_hooks > 0 if lot qty < jig capacity, else always 0 ---
            if modal_data['loaded_cases_qty'] < modal_data['jig_capacity']:
                modal_data['empty_hooks'] = modal_data['jig_capacity'] - modal_data['loaded_cases_qty']
            else:
                modal_data['empty_hooks'] = 0
            # --- END FIX ---
            modal_data['no_of_cycle'] = jig_details.no_of_cycle
        else:
            # Auto-fill for new entries with comprehensive defaults
            modal_data['nickel_bath_type'] = "Bright"  # Default
            modal_data['loaded_cases_qty'] = stock.total_stock
            modal_data['loaded_hooks'] = stock.total_stock
            # --- FIX: Only allow empty_hooks > 0 if lot qty < jig capacity, else always 0 ---
            if modal_data['loaded_cases_qty'] < modal_data['jig_capacity']:
                modal_data['empty_hooks'] = modal_data['jig_capacity'] - modal_data['loaded_cases_qty']
            else:
                modal_data['empty_hooks'] = 0
            # --- END FIX ---

        # Apply broken hooks adjustment and half-filled tray logic
        if broken_hooks > 0:
            effective_capacity = modal_data['jig_capacity'] - broken_hooks
            # Effective loaded cases: min of lot qty and effective capacity
            modal_data['effective_loaded_cases'] = min(modal_data['effective_loaded_cases'], effective_capacity)
            modal_data['loaded_hooks'] = modal_data['effective_loaded_cases']
            modal_data['empty_hooks'] = 0  # No empty hooks when broken hooks present
            modal_data['remaining_cases'] = max(0, modal_data['effective_loaded_cases'] - modal_data['effective_loaded_cases'])  # 0 for now
            modal_data['half_filled_tray_cases'] = 0  # No half-filled for broken hooks in this cycle
            modal_data['no_of_cycle'] = 1
        else:
            # No broken hooks - effective loaded cases is the lot qty
            modal_data['remaining_cases'] = 0
            modal_data['half_filled_tray_cases'] = 0

        # Delink Table preparation (existing tray data)
        modal_data['delink_table'] = self._prepare_existing_delink_table(lot_id, batch, modal_data['effective_loaded_cases'], tray_capacity, broken_hooks)

        # If lot qty >= jig capacity, force empty_hooks to 0 regardless of broken hooks
        if modal_data['loaded_cases_qty'] >= modal_data['jig_capacity']:
            modal_data['empty_hooks'] = 0

        # Model Images preparation with validation
        modal_data['model_images'] = self._prepare_model_images(model_master)

        # Add Model button logic with validation
        modal_data['add_model_enabled'] = modal_data['empty_hooks'] > 0
        
        
        # Save button logic: Enable only if empty_hooks == 0
        modal_data['can_save'] = (modal_data['empty_hooks'] == 0)

        # Modal validation rules
        modal_data['modal_validation'] = self._prepare_modal_validation(modal_data)

        # Tray Distribution and Half-Filled Tray Calculation
        modal_data['tray_distribution'] = self._calculate_tray_distribution(
            modal_data['effective_loaded_cases'], 
            modal_data['jig_capacity'], 
            modal_data['broken_buildup_hooks'],
            batch
        )

        # UI Configuration for frontend rendering
        modal_data['ui_config'] = self._prepare_ui_configuration(modal_data)

        # Comprehensive calculation logs
        modal_data['logs'] = {
            'batch_id': batch.batch_id if batch else None,
            'lot_id': lot_id,
            'jig_qr_id': jig_qr_id,
            'jig_type': modal_data['jig_type'],
            'jig_capacity': modal_data['jig_capacity'],
            'loaded_cases_qty': modal_data['loaded_cases_qty'],
            'loaded_hooks': modal_data['loaded_hooks'],
            'empty_hooks': modal_data['empty_hooks'],
            'broken_buildup_hooks': modal_data['broken_buildup_hooks'],
            'nickel_bath_type': modal_data['nickel_bath_type'],
            'delink_table': modal_data['delink_table'],
            'model_images': modal_data['model_images'],
            'add_model_enabled': modal_data['add_model_enabled'],
            'can_save': modal_data['can_save'],
            'user': request.user.username,
            'calculation_timestamp': timezone.now().isoformat(),
            'tray_type': modal_data['tray_type'],
            'tray_distribution': modal_data['tray_distribution']
        }

        logger.info(f"🎯 Modal data prepared with {len(modal_data['model_images'])} images, {len(modal_data['delink_table'])} existing trays")
        
        return modal_data

    def _prepare_model_images(self, model_master):
        """
        Prepare model images data with proper structure for frontend consumption.
        """
        model_image_data = []
        if model_master and model_master.images.exists():
            for image in model_master.images.all():
                model_image_data.append({
                    'url': image.master_image.url,
                    'model_no': model_master.model_no,
                    'image_id': image.id,
                    'alt_text': f"Model {model_master.model_no} Image"
                })
        return model_image_data
    
    def _prepare_existing_delink_table(self, lot_id, batch):
        """
        Prepare existing delink table data (for display only, not calculation).
        """
        tray_ids = JigLoadTrayId.objects.filter(lot_id=lot_id, batch_id=batch).order_by('date')
        delink_table = []
        for idx, tray in enumerate(tray_ids):
            delink_table.append({
                's_no': idx + 1,
                'tray_id': tray.tray_id,
                'tray_qty': tray.tray_quantity,
                'date_created': tray.date.isoformat() if tray.date else None,
                'is_existing': True
            })
        return delink_table
    
    def _prepare_modal_validation(self, modal_data):
        """
        Prepare validation rules and constraints for modal data.
        """
        # Fix hooks balance calculation for half-filled tray scenarios
        if modal_data['broken_buildup_hooks'] > 0:
            # When broken hooks present: loaded_hooks should equal effective capacity
            expected_loaded = modal_data['jig_capacity'] - modal_data['broken_buildup_hooks']
            actual_loaded = modal_data['loaded_hooks'] + modal_data['empty_hooks']
            hooks_balance_valid = actual_loaded == expected_loaded
        else:
            # Standard calculation when no broken hooks
            hooks_balance_valid = modal_data['loaded_hooks'] + modal_data['empty_hooks'] == modal_data['jig_capacity']
        
        validation = {
            'jig_capacity_valid': modal_data['jig_capacity'] > 0,
            'loaded_cases_valid': modal_data['loaded_cases_qty'] > 0,
            'hooks_balance_valid': hooks_balance_valid,
            'broken_hooks_valid': modal_data['broken_buildup_hooks'] >= 0,
            'nickel_bath_valid': modal_data['nickel_bath_type'] in ['Bright', 'Satin', 'Matt'],
            'has_model_images': len(modal_data['model_images']) > 0,
            'can_add_model': modal_data['add_model_enabled'],
            'empty_hooks_zero': (modal_data['empty_hooks'] == 0),
            'has_half_filled_cases': modal_data.get('half_filled_tray_cases', 0) > 0,
        }
        
        validation['overall_valid'] = all([
            validation['jig_capacity_valid'],
            validation['loaded_cases_valid'],
            validation['hooks_balance_valid'],
            validation['broken_hooks_valid'],
            validation['nickel_bath_valid'],
            validation['empty_hooks_zero'],
        ])
        
        if not validation['empty_hooks_zero']:
            validation['empty_hooks_error'] = (
                "Loaded Cases Qty must equal Jig Capacity. Use 'Add Model' to fill empty hooks with relevant tray allocation."
        )
        
        return validation
    
    def _calculate_tray_distribution(self, loaded_cases_qty, jig_capacity, broken_hooks, batch):
        """
        Calculate tray distribution for cases considering broken hooks and tray capacity.
        Returns distribution data for both current effective lot and half-filled tray lot.
        """
        # Get tray capacity from batch tray type (STRICT: Always from database)
        tray_capacity = None
        if batch and batch.tray_type:
            tray_type_obj = TrayType.objects.filter(tray_type=batch.tray_type).first()
            if tray_type_obj:
                tray_capacity = tray_type_obj.tray_capacity

        # STRICT: If tray_capacity is not found, raise error (do not fallback to hardcoded value)
        if not tray_capacity:
            raise ValueError(f"Tray capacity not configured for tray type '{getattr(batch, 'tray_type', None)}'. Please configure in admin.")

        # --- FIX START: Correct effective capacity and tray distribution with broken hooks ---
        if broken_hooks > 0:
            effective_capacity = jig_capacity - broken_hooks
            current_cycle_cases = min(loaded_cases_qty, effective_capacity)
            current_distribution = self._distribute_cases_to_trays(current_cycle_cases, tray_capacity)
            broken_distribution = self._distribute_cases_to_trays(broken_hooks, tray_capacity)
            return {
                'current_lot': {
                    'total_cases': current_cycle_cases,
                    'effective_capacity': effective_capacity,
                    'broken_hooks': broken_hooks,
                    'tray_capacity': tray_capacity,
                    'distribution': current_distribution,
                    'total_trays': len(current_distribution['trays']) if current_distribution else 0
                },
                'half_filled_lot': {
                    'total_cases': broken_hooks,
                    'distribution': broken_distribution,
                    'total_trays': len(broken_distribution['trays']) if broken_distribution else 0
                },
                'accountability_info': self._generate_accountability_info(
                    loaded_cases_qty, current_cycle_cases, broken_hooks, broken_hooks
                )
            }
        else:
            tray_distribution_cases = loaded_cases_qty
            half_filled_cases = 0

        # Calculate tray distribution for current cycle (only up to effective capacity)
        current_distribution = self._distribute_cases_to_trays(tray_distribution_cases, tray_capacity)

        # Calculate tray distribution for half-filled cases (if any)
        half_filled_distribution = None
        if half_filled_cases > 0:
            half_filled_distribution = self._distribute_half_filled_trays(half_filled_cases, tray_capacity)

        return {
            'current_lot': {
                'total_cases': tray_distribution_cases,
                'effective_capacity': jig_capacity,
                'broken_hooks': broken_hooks,
                'tray_capacity': tray_capacity,
                'distribution': current_distribution,
                'total_trays': len(current_distribution['trays']) if current_distribution else 0
            },
            'half_filled_lot': {
                'total_cases': half_filled_cases,
                'distribution': half_filled_distribution,
                'total_trays': len(half_filled_distribution['trays']) if half_filled_distribution else 0
            } if half_filled_cases > 0 else None,
            'accountability_info': self._generate_accountability_info(
                loaded_cases_qty, tray_distribution_cases, half_filled_cases, broken_hooks
            )
        }
    
    
    
    def _distribute_cases_to_trays(self, total_cases, tray_capacity):
        """
        Distribute cases into trays based on tray capacity.
        Returns distribution with full trays and partial tray details.
        For leftover lots, put partial tray first for scanning.
        """
        if total_cases <= 0:
            return None
            
        full_trays = total_cases // tray_capacity
        partial_cases = total_cases % tray_capacity
        
        trays = []
        
        # For leftover lots (when there are partial cases), put partial tray first
        if partial_cases > 0:
            trays.append({
                'tray_number': 1,
                'cases': partial_cases,
                'is_full': False,
                'is_top_tray': True,  # Mark as top tray for scanning
                'scan_required': True
            })
            # Then add full trays
            for i in range(full_trays):
                trays.append({
                    'tray_number': i + 2,  # Start from 2 since partial is 1
                    'cases': tray_capacity,
                    'is_full': True,
                    'scan_required': False
                })
        else:
            # For full trays only, add them in order
            for i in range(full_trays):
                trays.append({
                    'tray_number': i + 1,
                    'cases': tray_capacity,
                    'is_full': True,
                    'scan_required': False
                })
        
        return {
            'total_cases': total_cases,
            'full_trays_count': full_trays,
            'partial_tray_cases': partial_cases if partial_cases > 0 else 0,
            'total_trays': len(trays),
            'trays': trays
        }

    def _distribute_half_filled_trays(self, half_filled_cases, tray_capacity):
        """
        Distribute half-filled cases into trays with scan requirements.
        Partial trays require scanning, full trays can auto-assign existing tray IDs.
        """
        if half_filled_cases <= 0:
            return None
            
        partial_cases = half_filled_cases
        
        trays = []
        tray_number = 1
        
        # Add partial tray (requires scanning)
        if partial_cases > 0:
            trays.append({
                'tray_number': tray_number,
                'cases': partial_cases,
                'is_full': False,
                'scan_required': True,
                'tray_type': 'partial',
                'placeholder': f'Scan Tray ID ({partial_cases} pcs)'
            })
            tray_number += 1
        
        return {
            'total_cases': half_filled_cases,
            'full_trays_count': 0,
            'partial_tray_cases': partial_cases if partial_cases > 0 else 0,
            'total_trays': len(trays),
            'trays': trays,
            'scan_required_trays': len([t for t in trays if t.get('scan_required', False)])
        }

    def _generate_accountability_info(self, original_lot_qty, effective_loaded, leftover_cases, broken_hooks):
        """
        Generate accountability information text for user understanding.
        """
        info_lines = []
        
        if broken_hooks > 0:
            info_lines.append(f"Original Lot Qty: {original_lot_qty} cases")
            info_lines.append(f"Broken Hooks: {broken_hooks} (positions unavailable)")
            info_lines.append(f"Current Cycle: {effective_loaded} cases loaded")
            
            if leftover_cases > 0:
                info_lines.append(f"Next Cycle: {leftover_cases} cases remaining")
                info_lines.append("All cases accounted for - no quantities missing")
            else:
                info_lines.append("All cases loaded in current cycle")
        else:
            info_lines.append(f"Total cases: {original_lot_qty} - All loaded in current cycle")
            info_lines.append("No broken hooks - full capacity utilized")
        
        return " • ".join(info_lines)

    def _prepare_ui_configuration(self, modal_data):
        """
        Prepare UI configuration for optimal frontend rendering.
        """
        return {
            'show_model_images': len(modal_data['model_images']) > 0,
            'enable_add_model': modal_data['add_model_enabled'],
            'show_cycle_info': modal_data['no_of_cycle'] > 1,
            'highlight_empty_hooks': modal_data['empty_hooks'] > 0,
            'show_broken_hooks_warning': modal_data['broken_buildup_hooks'] > 0,
            'readonly_fields': ['empty_hooks', 'loaded_cases_qty', 'jig_capacity'],
            'required_fields': ['jig_id', 'nickel_bath_type'],
            'validation_enabled': True
        }

    def _calculate_broken_hooks_tray_distribution(self, lot_id, effective_qty, broken_hooks, batch):
        """
        Calculate how to distribute effective quantity across existing trays when broken hooks are present.
        This updates tray records with broken hooks calculation fields.
        
        User's calculation example:
        - Original lot: 98 cases across 9 trays (JB-A00020=2, JB-A00021=12, ..., JB-A00028=12)
        - Broken hooks: 39 cases  
        - Effective qty: 59 cases
        - Expected distribution: JB-A00020=11, JB-A00021=12, JB-A00022=12, JB-A00023=12, JB-A00024=12
        
        Logic: First tray gets remainder, subsequent trays get full capacity up to effective qty
        """
        logger = logging.getLogger(__name__)
        existing_trays = JigLoadTrayId.objects.filter(lot_id=lot_id, batch_id=batch).order_by('tray_id')
        
        if not existing_trays.exists():
            logger.warning(f"⚠️ No existing trays found for lot {lot_id} and batch {batch.batch_id if batch else 'None'}")
            return []
        
        logger.info(f"🔧 BROKEN HOOKS CALCULATION: lot={lot_id}, effective_qty={effective_qty}, broken_hooks={broken_hooks}")
        
        # Get tray capacity to determine proper distribution
        tray_capacity = 12  # Default fallback
        if existing_trays.exists():
            first_tray = existing_trays.first()
            if first_tray.tray_capacity:
                tray_capacity = first_tray.tray_capacity
            elif first_tray.batch_id and first_tray.batch_id.tray_capacity:
                tray_capacity = first_tray.batch_id.tray_capacity
        
        # Calculate how many full trays we need for effective qty
        full_trays_needed = effective_qty // tray_capacity
        remainder_qty = effective_qty % tray_capacity
        
        logger.info(f"📊 Distribution calculation: effective_qty={effective_qty}, tray_capacity={tray_capacity}, full_trays_needed={full_trays_needed}, remainder_qty={remainder_qty}")
        
        # Reset all trays first
        for tray in existing_trays:
            tray.broken_hooks_effective_tray = False
            tray.broken_hooks_excluded_qty = 0
            tray.effective_tray_qty = tray.tray_quantity  # Default to original quantity
            tray.save()
        
        # Distribute effective quantity: remainder tray first (if any), then full trays
        remaining_effective_qty = effective_qty
        effective_trays = []
        tray_index = 0
        
        # Handle remainder first (partial tray) - user's example: JB-A00020 gets 11 cases
        if remainder_qty > 0 and tray_index < existing_trays.count():
            tray = existing_trays[tray_index]
            tray_effective_qty = remainder_qty
            tray_excluded_qty = tray.tray_quantity - tray_effective_qty
            
            # Update tray with broken hooks fields
            tray.broken_hooks_effective_tray = True
            tray.broken_hooks_excluded_qty = tray_excluded_qty
            tray.effective_tray_qty = tray_effective_qty
            tray.save()
            
            effective_trays.append({
                'tray_id': tray.tray_id,
                'effective_qty': tray_effective_qty,
                'original_qty': tray.tray_quantity,
                'excluded_qty': tray_excluded_qty,
                'model_bg': self._get_model_bg(tray_index + 1)
            })
            
            remaining_effective_qty -= tray_effective_qty
            tray_index += 1
            logger.info(f"  Remainder tray {tray.tray_id}: effective={tray_effective_qty}, excluded={tray_excluded_qty}")
        
        # Handle full trays - user's example: JB-A00021, JB-A00022, JB-A00023, JB-A00024 each get 12 cases
        for i in range(full_trays_needed):
            if tray_index >= existing_trays.count():
                break
                
            tray = existing_trays[tray_index]
            tray_effective_qty = tray_capacity
            tray_excluded_qty = tray.tray_quantity - tray_effective_qty
            
            # Update tray with broken hooks fields
            tray.broken_hooks_effective_tray = True
            tray.broken_hooks_excluded_qty = tray_excluded_qty
            tray.effective_tray_qty = tray_effective_qty
            tray.save()
            
            effective_trays.append({
                'tray_id': tray.tray_id,
                'effective_qty': tray_effective_qty,
                'original_qty': tray.tray_quantity,
                'excluded_qty': tray_excluded_qty,
                'model_bg': self._get_model_bg(tray_index + 1)
            })
            
            remaining_effective_qty -= tray_effective_qty
            tray_index += 1
            logger.info(f"  Full tray {tray.tray_id}: effective={tray_effective_qty}, excluded={tray_excluded_qty}")
        
        # Mark remaining trays as excluded (not part of effective distribution)
        for i in range(tray_index, existing_trays.count()):
            tray = existing_trays[i]
            tray.broken_hooks_effective_tray = False
            tray.broken_hooks_excluded_qty = tray.tray_quantity
            tray.effective_tray_qty = 0
            tray.save()
            logger.info(f"  Excluded tray {tray.tray_id}: all {tray.tray_quantity} cases excluded")
        
        logger.info(f"✅ Broken hooks distribution complete: {len(effective_trays)} effective trays, remaining_qty={remaining_effective_qty}")
        return effective_trays

    def _prepare_existing_delink_table(self, lot_id, batch, effective_loaded_cases, tray_capacity, broken_hooks):
        logger = logging.getLogger(__name__)
        existing_trays = JigLoadTrayId.objects.filter(lot_id=lot_id, batch_id=batch).order_by('id')
        delink_table = []
    
        if existing_trays.exists():
            # When broken hooks > 0, calculate effective tray distribution and update DB
            if broken_hooks > 0:
                # Calculate tray distribution for effective loaded cases
                full_trays = effective_loaded_cases // tray_capacity
                partial_cases = effective_loaded_cases % tray_capacity
                tray_count = full_trays + (1 if partial_cases > 0 else 0)
                # Show all required trays (existing + placeholders if needed)
                for idx in range(tray_count):
                    if idx < existing_trays.count():
                        # Use existing tray
                        tray = existing_trays[idx]
                        if idx == 0 and partial_cases > 0:
                            qty = partial_cases
                        else:
                            qty = tray_capacity
                        tray.broken_hooks_effective_tray = True
                        tray.broken_hooks_excluded_qty = max(0, tray.tray_quantity - qty)
                        tray.effective_tray_qty = qty
                        tray.save()
                        model_bg = self._get_model_bg(idx + 1)
                        delink_table.append({
                            'tray_id': tray.tray_id,
                            'tray_quantity': qty,
                            'model_bg': model_bg,
                            'original_quantity': tray.tray_quantity,
                            'excluded_quantity': tray.broken_hooks_excluded_qty
                        })
                    else:
                        # Create placeholder for missing tray
                        if idx == 0 and partial_cases > 0:
                            qty = partial_cases
                        else:
                            qty = tray_capacity
                        model_bg = self._get_model_bg(idx + 1)
                        delink_table.append({
                            'tray_id': '',  # Empty for user to scan
                            'tray_quantity': qty,
                            'model_bg': model_bg,
                            'original_quantity': qty,
                            'excluded_quantity': 0
                        })
                # Mark remaining trays as excluded
                for tray in existing_trays[tray_count:]:
                    tray.broken_hooks_effective_tray = False
                    tray.broken_hooks_excluded_qty = tray.tray_quantity
                    tray.effective_tray_qty = 0
                    tray.save()
            else:
                # No broken hooks - limit trays to effective_loaded_cases
                logger.info(f"🔧 Processing no broken hooks scenario: effective_cases={effective_loaded_cases}, tray_capacity={tray_capacity}")
                if tray_capacity > 0:
                    num_trays_needed = ceil(effective_loaded_cases / tray_capacity)
                else:
                    num_trays_needed = len(existing_trays)
                limited_trays = list(existing_trays[:num_trays_needed])
                # Distribute effective_loaded_cases across limited trays
                distribution = self._distribute_cases_to_trays(effective_loaded_cases, tray_capacity)
                for idx, tray in enumerate(limited_trays):
                    qty = distribution['trays'][idx]['cases'] if idx < len(distribution['trays']) else 0
                    tray.broken_hooks_effective_tray = True
                    tray.broken_hooks_excluded_qty = max(0, tray.tray_quantity - qty)
                    tray.effective_tray_qty = qty
                    tray.save()
                    model_bg = self._get_model_bg(idx + 1)
                    delink_table.append({
                        'tray_id': tray.tray_id,
                        'tray_quantity': qty,
                        'model_bg': model_bg,
                        'original_quantity': tray.tray_quantity,
                        'excluded_quantity': tray.broken_hooks_excluded_qty
                    })
                # Mark remaining trays as excluded
                for tray in existing_trays[num_trays_needed:]:
                    tray.broken_hooks_effective_tray = False
                    tray.broken_hooks_excluded_qty = tray.tray_quantity
                    tray.effective_tray_qty = 0
                    tray.save()
        else:
            # No existing trays - NEVER create fake tray IDs
            logger.error(f"❌ CRITICAL: No existing trays found for lot {lot_id}. Cannot proceed without actual tray IDs.")
            return []
    
        return delink_table
    def _get_model_bg(self, idx):
        return f"model-bg-{(idx - 1) % 5 + 1}"

# Tray ID Validation - Delink Table View
@api_view(['GET'])
def validate_tray_id(request):
    tray_id = request.GET.get('tray_id')
    batch_id = request.GET.get('batch_id')
    lot_id = request.GET.get('lot_id')  # <-- Add this line to get lot_id from request
    if not tray_id or not batch_id or not lot_id:
        return Response({'valid': False, 'message': 'Tray ID, Batch ID, and Lot ID required'}, status=400)
    # Only accept tray_id that belongs to this lot and batch
    exists = JigLoadTrayId.objects.filter(
        tray_id=tray_id,
        batch_id__batch_id=batch_id,
        lot_id=lot_id
    ).exists()
    if exists:
        return Response({'valid': True})
    else:
        # Do NOT allow new trays for delink table (only for half-filled section, handled elsewhere)
        return Response({'valid': False, 'message': 'Invalid Tray ID.'})

# Add Jig Btn - Delink Table View


class DelinkTableAPIView(APIView):
    """
    Returns tray rows for Delink Table based on tray type, lot qty, and jig capacity.
    Calculates number of trays needed for scanning based on loaded cases qty and tray capacity.
    """
    def get(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        batch_id = request.GET.get('batch_id')
        lot_id = request.GET.get('lot_id')
        jig_qr_id = request.GET.get('jig_qr_id', None)
        broken_hooks = int(request.GET.get('broken_hooks', 0))

        if not batch_id or not lot_id:
            logger.info("❌ Missing parameters: batch_id or lot_id")
            return Response({'error': 'batch_id and lot_id required'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"🔍 Processing delink table for batch_id: {batch_id}, lot_id: {lot_id}, broken_hooks: {broken_hooks}")

        # Get TotalStockModel for loaded cases qty
        try:
            stock = TotalStockModel.objects.get(lot_id=lot_id)
            loaded_cases_qty = stock.total_stock or 0
            logger.info(f"📊 Loaded cases qty from TotalStockModel: {loaded_cases_qty}")
        except TotalStockModel.DoesNotExist:
            logger.error(f"❌ TotalStockModel not found for lot_id: {lot_id}")
            return Response({'error': 'Stock record not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get batch/model info for tray type and jig capacity
        try:
            batch = ModelMasterCreation.objects.get(batch_id=batch_id)
            model_master = batch.model_stock_no
            logger.info(f"📦 Found batch: {batch_id}, model: {model_master}")
        except ModelMasterCreation.DoesNotExist:
            logger.error(f"❌ ModelMasterCreation not found for batch_id: {batch_id}")
            return Response({'error': 'Batch not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get tray type and capacity
        tray_type_name = batch.tray_type or "Normal"  # Default to Normal if not set
        try:
            tray_type_obj = TrayType.objects.get(tray_type=tray_type_name)
            tray_capacity = tray_type_obj.tray_capacity
            logger.info(f"🗂️ Tray type: {tray_type_name}, capacity: {tray_capacity}")
        except TrayType.DoesNotExist:
            logger.warning(f"⚠️ TrayType '{tray_type_name}' not found, trying fallback options")
            fallback_types = ["Normal", "Jumbo"]
            tray_capacity = None
            for fallback_type in fallback_types:
                try:
                    fallback_tray_obj = TrayType.objects.get(tray_type=fallback_type)
                    tray_capacity = fallback_tray_obj.tray_capacity
                    logger.warning(f"⚠️ Using fallback TrayType '{fallback_type}' with capacity: {tray_capacity}")
                    break
                except TrayType.DoesNotExist:
                    continue
            if tray_capacity is None:
                logger.error(f"❌ No TrayType configurations found in database")
                return Response({'error': 'Tray type configuration missing. Please configure tray types in admin.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get jig capacity from JigLoadingMaster
        jig_capacity = 0
        if model_master:
            try:
                jig_master = JigLoadingMaster.objects.get(model_stock_no=model_master)
                jig_capacity = jig_master.jig_capacity
                logger.info(f"🔧 Jig capacity from JigLoadingMaster: {jig_capacity}")
            except JigLoadingMaster.DoesNotExist:
                logger.warning(f"⚠️ JigLoadingMaster not found for model: {model_master}")
                jig_capacity = loaded_cases_qty  # Use loaded cases qty as fallback

        # Calculate effective capacity considering broken hooks
        effective_capacity = max(0, jig_capacity - broken_hooks) if jig_capacity > 0 else loaded_cases_qty
        actual_qty = min(loaded_cases_qty, effective_capacity)
        logger.info(f"🧮 Calculation: loaded_cases_qty={loaded_cases_qty}, jig_capacity={jig_capacity}, broken_hooks={broken_hooks}, effective_capacity={effective_capacity}, actual_qty={actual_qty}")

        # Check for existing tray IDs for this lot
        existing_trays = JigLoadTrayId.objects.filter(
            lot_id=lot_id, 
            batch_id=batch
        ).order_by('date').only('tray_id', 'tray_quantity')  # Optimization

        # --- NEW LOGIC: Conditional tray distribution based on broken_hooks ---
        half_filled_tray_data = None
        rows = []
        if tray_capacity > 0 and actual_qty > 0:
            if broken_hooks == 0:
                # When broken_hooks == 0, show all trays (full and partial) in delink table
                num_full_trays = actual_qty // tray_capacity
                remainder_qty = actual_qty % tray_capacity
                total_trays = num_full_trays + (1 if remainder_qty > 0 else 0)
                
                for i in range(total_trays):
                    s_no = i + 1
                    if i < num_full_trays:
                        tray_qty = tray_capacity
                    else:
                        tray_qty = remainder_qty
                    
                    # All trays are for scanning - empty inputs
                    tray_id = ""
                    tray_quantity = tray_qty
                    placeholder = "Scan Tray Id"
                    readonly = False
                    
                    rows.append({
                        's_no': s_no,
                        'tray_id': tray_id,
                        'tray_quantity': tray_quantity,
                        'placeholder': placeholder,
                        'readonly': readonly
                    })
                
                num_trays = total_trays
            else:
                # When broken_hooks > 0, show all trays (full and partial) in delink table
                num_full_trays = actual_qty // tray_capacity
                remainder_qty = actual_qty % tray_capacity
                total_trays = num_full_trays + (1 if remainder_qty > 0 else 0)
                
                for i in range(total_trays):
                    s_no = i + 1
                    if i < num_full_trays:
                        tray_qty = tray_capacity
                    else:
                        tray_qty = remainder_qty
                    
                    # All trays are for scanning - empty inputs
                    tray_id = ""
                    tray_quantity = tray_qty
                    placeholder = "Scan Tray Id"
                    readonly = False
                    
                    rows.append({
                        's_no': s_no,
                        'tray_id': tray_id,
                        'tray_quantity': tray_quantity,
                        'placeholder': placeholder,
                        'readonly': readonly
                    })
                
                # Half-filled tray for broken hooks
                if broken_hooks > 0:
                    half_filled_cases = broken_hooks
                    half_filled_num_trays = (half_filled_cases + tray_capacity - 1) // tray_capacity  # ceil division
                    half_filled_tray_data = {
                        'tray_count': half_filled_num_trays,
                        'message': f'Scan half filled tray ID with {half_filled_cases} pieces'
                    }
                
                num_trays = total_trays
        else:
            num_trays = 0

        logger.info(f"✅ Generated {len(rows)} delink table rows")
        logger.info(f"📊 Final calculation summary - tray_type: {tray_type_name}, tray_capacity: {tray_capacity}, actual_qty: {actual_qty}, num_full_trays: {num_full_trays}, half_filled_tray: {half_filled_tray_data}")

        return Response({
            'tray_rows': rows,
            'tray_type': tray_type_name,
            'tray_capacity': tray_capacity,
            'actual_qty': actual_qty,
            'loaded_cases_qty': loaded_cases_qty,
            'jig_capacity': jig_capacity,
            'effective_capacity': effective_capacity,
            'broken_hooks': broken_hooks,
            'num_trays': num_trays,
            'half_filled_tray_data': half_filled_tray_data,
            'calculation_details': {
                'formula': f'{actual_qty} pieces = {num_full_trays} full trays + {remainder_qty if remainder_qty > 0 else 0} remainder',
                'constraint': f'effective_capacity = jig_capacity({jig_capacity}) - broken_hooks({broken_hooks}) = {effective_capacity}',
                'tray_distribution': [row['tray_quantity'] for row in rows],
                'half_filled_info': half_filled_tray_data
            }
        }, status=status.HTTP_200_OK)



# Manual Draft - Save/Update View
class JigLoadingManualDraftAPIView(APIView):
    def post(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        batch_id = request.data.get('batch_id')
        lot_id = request.data.get('lot_id')
        draft_data = request.data.get('draft_data')
        user = request.user
        
        logger.info(f"🔍 Draft request: user={user.username}, batch_id={batch_id}, lot_id={lot_id}")

        if not batch_id or not lot_id or not draft_data:
            logger.error(f"❌ Missing required fields: batch_id={batch_id}, lot_id={lot_id}, draft_data present={bool(draft_data)}")
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = JigLoadingManualDraft.objects.update_or_create(
            batch_id=batch_id,
            lot_id=lot_id,
            user=user,
            defaults={'draft_data': draft_data}
        )

        # --- Fix: Update only the correct TotalStockModel ---
        try:
            stock = TotalStockModel.objects.get(batch_id__batch_id=batch_id, lot_id=lot_id)
            stock.jig_draft = True
            stock.save()
            logger.info(f"💾 Successfully updated lot status to Draft for batch_id={batch_id}, lot_id={lot_id}")
        except TotalStockModel.DoesNotExist:
            logger.error(f"❌ No TotalStockModel for lot_id={lot_id}, batch_id={batch_id}")
            return Response({'error': 'Stock record not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # --- Update Jig table with draft info ---
        jig_id = draft_data.get('jig_id')
        if jig_id:
            jig_obj, _ = Jig.objects.get_or_create(jig_qr_id=jig_id)
            jig_obj.drafted = True
            jig_obj.current_user = user
            jig_obj.locked_at = timezone.now()
            jig_obj.batch_id = batch_id
            jig_obj.lot_id = lot_id
            jig_obj.save()
            logger.info(f"💾 Jig {jig_id} marked as drafted for batch {batch_id} by {user.username}")

        # --- Check for partial draft: if loaded cases < total stock, create remaining lot ---
        loaded_cases = sum(int(t.get('tray_qty', 0)) for t in draft_data.get('trays', []))
        remaining_cases = stock.total_stock - loaded_cases
        if remaining_cases > 0:
            new_lot_id = f"LID{timezone.now().strftime('%d%m%Y%H%M%S')}{remaining_cases:04d}"
            TotalStockModel.objects.create(
                batch_id=stock.batch_id,
                model_stock_no=stock.model_stock_no,
                version=stock.version,
                total_stock=remaining_cases,
                polish_finish=stock.polish_finish,
                plating_color=stock.plating_color,
                lot_id=new_lot_id,
                created_at=timezone.now(),
                Jig_Load_completed=False,
                jig_draft=True,
                last_process_date_time=timezone.now(),
                last_process_module="Jig Loading",
            )
            logger.info(f"💾 Created remaining lot {new_lot_id} with {remaining_cases} cases for partial draft")

        logger.info(f"✅ Draft saved successfully for batch_id={batch_id}, lot_id={lot_id}")
        return Response({'success': True, 'created': created, 'updated_at': obj.updated_at})

# Manual Draft - Retrieve View
class JigLoadingManualDraftFetchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        batch_id = request.GET.get('batch_id')
        lot_id = request.GET.get('lot_id')
        user = request.user
        try:
            draft = JigLoadingManualDraft.objects.get(batch_id=batch_id, lot_id=lot_id, user=user)
            return Response({'success': True, 'draft_data': draft.draft_data})
        except JigLoadingManualDraft.DoesNotExist:
            return Response({'success': False, 'draft_data': None})
        


@api_view(['POST'])
def validate_lock_jig_id(request):
    logger = logging.getLogger(__name__)
    try:
        # Check authentication first
        if not request.user.is_authenticated:
            logger.warning("❌ User not authenticated")
            return JsonResponse({'valid': False, 'message': 'Authentication required'}, status=401)
        
        logger.info(f"🚀 API CALLED - validate_lock_jig_id by user: {request.user.username}")
        
        jig_id = request.data.get('jig_id', '').strip()
        batch_id = request.data.get('batch_id', '').strip()
        lot_id = request.data.get('lot_id', '').strip()
        user = request.user
        
        logger.info(f"📊 Request data: jig_id={jig_id}, batch_id={batch_id}, user={user.username}")

        # Basic validation - check if jig_id is provided
        if not jig_id or len(jig_id) > 9:
            logger.info("⚠️ Basic validation failed: length check")
            return JsonResponse({'valid': False, 'message': 'Jig ID must be <= 9 characters.'}, status=200)

        # FIRST: Check for existing drafted jigs before format validation
        drafted_jig_current_batch = Jig.objects.filter(
            jig_qr_id=jig_id, drafted=True, batch_id=batch_id
        ).first()

        logger.info(f"🔍 Drafted jig current batch query result: {drafted_jig_current_batch}")

        if drafted_jig_current_batch:
            # Only allow if same user, same batch, and same lot
            if (
                drafted_jig_current_batch.current_user == user and
                getattr(drafted_jig_current_batch, 'lot_id', None) == lot_id
            ):
                logger.info("✅ Same user, same batch, same lot - allowing")
                return JsonResponse({'valid': True, 'message': 'Jig ID is valid'}, status=200)
            else:
                logger.info(f"❌ Jig ID in use for another row or user: {drafted_jig_current_batch.current_user.username}")
                return JsonResponse({'valid': False, 'message': f'Jig ID is being used by {drafted_jig_current_batch.current_user.username}.'}, status=200)

        # If not drafted for this batch, check if drafted for any other batch
        drafted_jig_other_batch = Jig.objects.filter(
            jig_qr_id=jig_id, drafted=True
        ).exclude(batch_id=batch_id).first()

        logger.info(f"🔍 Drafted jig other batch query result: {drafted_jig_other_batch}")

        if drafted_jig_other_batch:
            # If same user but different batch, restrict with correct message
            if drafted_jig_other_batch.current_user == user:
                logger.info(f"🎯 FOUND: Same user ({user.username}) but different batch - returning 'Already drafted for another batch'")
                return JsonResponse({'valid': False, 'message': 'Already drafted for another batch'}, status=200)
            # If different user, restrict
            else:
                logger.info(f"❌ Different user for different batch: {drafted_jig_other_batch.current_user.username}")
                return JsonResponse({'valid': False, 'message': f'Jig ID is being used by {drafted_jig_other_batch.current_user.username}.'}, status=200)

        # Check if jig_id exists in database
        try:
            jig = Jig.objects.get(jig_qr_id=jig_id)
        except Jig.DoesNotExist:
            return JsonResponse({'valid': False, 'message': 'Jig ID not found in database.'}, status=200)

        # Get expected jig capacity for this batch/lot
        expected_capacity = None
        try:
            stock = TotalStockModel.objects.get(lot_id=lot_id)
            batch = stock.batch_id
            
            # Resolve plating_stk_no same as modal
            plating_stk_no = ''
            if batch and batch.plating_stk_no:
                plating_stk_no = batch.plating_stk_no
            elif batch and batch.model_stock_no and batch.model_stock_no.plating_stk_no:
                plating_stk_no = batch.model_stock_no.plating_stk_no
            
            if plating_stk_no:
                jig_master = JigLoadingMaster.objects.filter(model_stock_no__plating_stk_no=plating_stk_no).first()
                if jig_master:
                    expected_capacity = jig_master.jig_capacity
                else:
                    logger.warning(f"JigLoadingMaster not found for plating_stk_no {plating_stk_no}")
            else:
                logger.warning(f"Plating stock number not found for batch {batch_id}, lot {lot_id}")
        except TotalStockModel.DoesNotExist as e:
            logger.warning(f"TotalStockModel not found for lot {lot_id}: {e}. Skipping capacity validation.")

        # Check if jig ID prefix matches expected capacity (if available)
        if expected_capacity is not None:
            expected_prefix = f"J{expected_capacity:03d}"
            if not jig_id.startswith(expected_prefix):
                return JsonResponse({'valid': False, 'message': f'Invalid jig ID for this capacity. Expected prefix: {expected_prefix}'}, status=200)

        # If not drafted/locked, show available message
        logger.info("✅ Jig ID is available")
        return JsonResponse({'valid': True, 'message': 'Jig ID is available to use'}, status=200)
        
    except Exception as e:
        logger.error(f"💥 Exception in validate_lock_jig_id: {e}")
        return JsonResponse({'valid': False, 'message': 'Internal server error'}, status=200)



@api_view(['GET'])
def jig_tray_id_list(request):
    stock_lot_id = request.GET.get('stock_lot_id')
    if not stock_lot_id:
        return JsonResponse({'success': False, 'error': 'stock_lot_id required'}, status=400)
    
    # Fetch actual tray data from JigLoadTrayId (where correct quantities are stored)
    tray_objects = JigLoadTrayId.objects.filter(lot_id=stock_lot_id).order_by('date')
    
    if tray_objects.exists():
        formatted_trays = []
        for idx, tray_obj in enumerate(tray_objects):
            # Determine tray status based on broken_hooks_effective_tray field
            tray_status = "Delinked" if tray_obj.broken_hooks_effective_tray else "Partial Draft"
            
            formatted_tray = {
                'tray_id': tray_obj.tray_id,
                'tray_quantity': tray_obj.effective_tray_qty if tray_obj.broken_hooks_effective_tray else tray_obj.tray_quantity,  # Use effective quantity for delinked trays
                'row_index': str(idx),
                'tray_status': tray_status,
                'original_quantity': tray_obj.tray_quantity,  # For reference
                'excluded_quantity': max(0, tray_obj.broken_hooks_excluded_qty),  # Ensure non-negative values
            }
            formatted_trays.append(formatted_tray)
        
        return JsonResponse({'success': True, 'trays': formatted_trays})
    else:
        # Fallback to JigDetails.delink_tray_data if no JigLoadTrayId found
        jig_detail = JigDetails.objects.filter(lot_id=stock_lot_id).first()
        if jig_detail and jig_detail.delink_tray_data:
            formatted_trays = []
            for tray in jig_detail.delink_tray_data:
                formatted_tray = {
                    'tray_id': tray.get('tray_id', ''),
                    'tray_quantity': tray.get('tray_qty', ''),
                    'row_index': tray.get('row_index', ''),
                    'tray_status': "Delinked",  # Default for legacy data
                    'original_quantity': tray.get('tray_qty', ''),
                    'excluded_quantity': 0,
                }
                formatted_trays.append(formatted_tray)
            return JsonResponse({'success': True, 'trays': formatted_trays})
        else:
            return JsonResponse({'success': True, 'trays': []})

# Jig Save API View & Move to Complete Table if valid
@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class JigSaveAPIView(APIView):
    """
    API endpoint for saving Jig details to complete table
    """

    def get_tray_capacity(stock):
        # Try batch first
        if stock.batch_id and getattr(stock.batch_id, 'tray_capacity', None):
            return stock.batch_id.tray_capacity
        # Try model_master
        if stock.model_stock_no and getattr(stock.model_stock_no, 'tray_capacity', None):
            return stock.model_stock_no.tray_capacity
        # Try tray_type
        if stock.batch_id and hasattr(stock.batch_id, 'tray_type') and stock.batch_id.tray_type:
            try:
                tray_type_obj = TrayType.objects.get(tray_type=stock.batch_id.tray_type)
                return tray_type_obj.tray_capacity
            except TrayType.DoesNotExist:
                pass
        # Try JigLoadingMaster
        jig_master = JigLoadingMaster.objects.filter(model_stock_no=stock.model_stock_no).first()
        if jig_master and getattr(jig_master, 'tray_capacity', None):
            return jig_master.tray_capacity
        return None

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            data = request.data if hasattr(request, 'data') else json.loads(request.body.decode('utf-8'))

            # Extract required fields
            batch_id = data.get('batch_id', '').strip()
            lot_id = data.get('lot_id', '').strip()
            jig_qr_id = data.get('jig_qr_id', '').strip()

            if not all([batch_id, lot_id, jig_qr_id]):
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required fields: batch_id, lot_id, jig_qr_id'
                }, status=400)

            logger.info(f"🚀 JigSaveAPIView: Saving jig {jig_qr_id} for batch {batch_id}, lot {lot_id}")

            # Try to get existing draft data, or use request data directly
            draft_data = {}
            try:
                draft = JigLoadingManualDraft.objects.get(
                    batch_id=batch_id,
                    lot_id=lot_id,
                    user=request.user
                )
                draft_data = draft.draft_data
            except JigLoadingManualDraft.DoesNotExist:
                trays_data = data.get('trays', [])
                draft_data = {
                    'batch_id': batch_id,
                    'lot_id': lot_id,
                    'jig_qr_id': jig_qr_id,
                    'broken_buildup_hooks': data.get('broken_buildup_hooks', 0),
                    'plating_stk_no': data.get('plating_stk_no', ''),
                    'no_of_cycle': data.get('no_of_cycle', 1),
                    'trays': trays_data,
                    'half_filled_tray_data': data.get('half_filled_tray_data', [])
                }

            # Validate broken hooks based on jig capacity from jig ID
            broken_hooks = int(draft_data.get('broken_buildup_hooks', 0))
            if jig_qr_id:
                import re
                match = re.match(r'J(\d+)-', jig_qr_id)
                if match:
                    jig_capacity_from_id = int(match.group(1))
                    max_broken_hooks = 10 if jig_capacity_from_id >= 144 else 5
                    if broken_hooks > max_broken_hooks:
                        return JsonResponse({
                            'success': False,
                            'error': f'Broken hooks cannot exceed {max_broken_hooks} for jig capacity {jig_capacity_from_id}'
                        }, status=400)

            half_filled_tray_data = draft_data.get('half_filled_tray_data', data.get('half_filled_tray_data', []))

            trays_data = draft_data.get('trays', [])
            all_valid_trays = [t for t in trays_data if t.get('tray_id') and t.get('tray_qty')]

            valid_trays = [t for t in all_valid_trays if not str(t.get('row_index', '')).startswith('half_')]
            half_filled_trays = [t for t in all_valid_trays if str(t.get('row_index', '')).startswith('half_')]

            if half_filled_trays:
                half_filled_tray_data = half_filled_trays

            try:
                batch_obj = ModelMasterCreation.objects.get(batch_id=batch_id)
                model_master = batch_obj.model_stock_no
                jig_master = JigLoadingMaster.objects.filter(model_stock_no=model_master).first()

                if not jig_master:
                    jig_type = getattr(batch_obj, 'tray_type', '') or getattr(model_master, 'tray_type', '')
                    jig_capacity = getattr(batch_obj, 'tray_capacity', None) or getattr(model_master, 'tray_capacity', None)
                    forging_info = getattr(model_master, 'brand', '') or ''
                else:
                    jig_type = jig_master.jig_type
                    jig_capacity = jig_master.jig_capacity
                    forging_info = jig_master.forging_info

            except ModelMasterCreation.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Batch not found'
                }, status=400)

            actual_loaded_cases = sum(int(t.get('tray_qty', 0)) for t in all_valid_trays)
            # Handle both field names: faulty_slots (frontend) and broken_buildup_hooks (draft)
            broken_hooks_count = int(data.get('faulty_slots', 0)) or int(draft_data.get('broken_buildup_hooks', 0))

            try:
                original_stock = TotalStockModel.objects.get(lot_id=lot_id)
                effective_total_cases = (original_stock.total_stock or 0) - broken_hooks_count
            except TotalStockModel.DoesNotExist:
                effective_total_cases = actual_loaded_cases

            # Main lot gets full effective quantity (98 - 39 = 59)
            total_cases_loaded = effective_total_cases

            # DO NOT modify original stock.total_stock - keep it as original lot quantity
            # The effective cases are stored in JigDetails.total_cases_loaded

            draft, created = JigLoadingManualDraft.objects.update_or_create(
                batch_id=batch_id,
                lot_id=lot_id,
                user=request.user,
                defaults={'draft_data': draft_data}
            )
            jig_detail_data = {
                'jig_qr_id': jig_qr_id,
                'jig_type': jig_type,
                'jig_capacity': jig_capacity,
                'total_cases_loaded': effective_total_cases,  # Main lot shows full effective quantity (63)
                'empty_slots': 0,
                'faulty_slots': 0,
                'broken_hooks': 0,  # Set to 0 since broken are in separate lot
                'no_of_model_cases': [draft_data.get('plating_stk_no', '')],
                'new_lot_ids': [lot_id],
                'lot_id_quantities': {lot_id: effective_total_cases},
                'lot_id': lot_id,
                'draft_save': False,
                'created_by': request.user,
                'ep_bath_type': data.get('ep_bath_type', 'Bright'),
                'plating_color': data.get('plating_color', 'Default'),
                'forging': forging_info,
                'delink_tray_data': valid_trays,
                'half_filled_tray_data': [],  # Main lot doesn't get half-filled trays
                'no_of_cycle': int(draft_data.get('no_of_cycle', 1)),
                'jig_loaded_date_time': timezone.now(),
            }

            # Calculate proper distribution for main lot first
            tray_capacity = None
            if batch_obj and batch_obj.tray_type:
                try:
                    from modelmasterapp.models import TrayType
                    tray_type_obj = TrayType.objects.get(tray_type=batch_obj.tray_type)
                    tray_capacity = tray_type_obj.tray_capacity
                except TrayType.DoesNotExist:
                    pass
            
            if not tray_capacity:
                # Try to get from model master
                if batch_obj and batch_obj.model_stock_no and batch_obj.model_stock_no.tray_capacity:
                    tray_capacity = batch_obj.model_stock_no.tray_capacity
            
            # Use fallback if still not found
            if not tray_capacity:
                tray_capacity = 12  # Default fallback
            
            # Calculate proper distribution
            num_full_trays = effective_total_cases // tray_capacity
            remainder_qty = effective_total_cases % tray_capacity
            
            # Create distribution array: partial tray first (if any), then full trays
            distribution_quantities = []
            if remainder_qty > 0:
                distribution_quantities.append(remainder_qty)  # Partial tray first
            for _ in range(num_full_trays):
                distribution_quantities.append(tray_capacity)  # Full trays

            # No AUTO tray creation - only use actual scanned tray IDs
            # Broken hooks distribution has already been handled in _calculate_broken_hooks_tray_distribution
            logger.info(f"✅ Using only existing scanned trays for lot {lot_id}")

            jig_detail, created = JigDetails.objects.update_or_create(
                lot_id=lot_id,
                jig_qr_id=jig_qr_id,
                defaults=jig_detail_data
            )

            # --- CREATE BROKEN LOT ---
            remaining_cases = broken_hooks_count
            
            if remaining_cases > 0:
                try:
                    new_lot_id = f"LID{timezone.now().strftime('%d%m%Y%H%M%S')}{remaining_cases:04d}"

                    # Create TotalStockModel for broken lot
                    original_stock = TotalStockModel.objects.get(lot_id=lot_id)
                    broken_stock = TotalStockModel.objects.create(
                        batch_id=batch_obj,
                        model_stock_no=model_master,
                        version=original_stock.version,
                        total_stock=remaining_cases,
                        polish_finish=original_stock.polish_finish,
                        plating_color=original_stock.plating_color,
                        lot_id=new_lot_id,
                        created_at=timezone.now(),
                        Jig_Load_completed=False,
                        jig_draft=True,
                        # Inherit audit acceptance flags from original lot so it appears in pick table
                        brass_audit_accptance=original_stock.brass_audit_accptance,
                        brass_audit_few_cases_accptance=original_stock.brass_audit_few_cases_accptance,
                        brass_audit_rejection=original_stock.brass_audit_rejection,
                        last_process_date_time=timezone.now(),
                        last_process_module="Jig Loading",
                    )

                    # Track cases allocated to broken lot trays
                    broken_cases_allocated = 0

                    # Create tray for half-filled from scanned tray
                    if half_filled_tray_data:
                        for tray in half_filled_tray_data:
                            tray_id = tray.get('tray_id') or f"TBD-{new_lot_id[-6:]}-01"
                            tray_qty = int(tray.get('tray_qty', 0))
                            JigLoadTrayId.objects.create(
                                lot_id=new_lot_id,
                                tray_id=tray_id,
                                tray_quantity=tray_qty,
                                batch_id=batch_obj,
                                user=request.user,
                                new_tray=True
                            )
                            broken_cases_allocated += tray_qty

                    # Always create automatic trays for broken lot cases (whether half-filled exists or not)
                    remaining_broken_cases = remaining_cases - broken_cases_allocated
                    if remaining_broken_cases > 0:
                        # Get dynamic tray capacity from batch
                        tray_capacity = None
                        if batch_obj and batch_obj.tray_type:
                            try:
                                from modelmasterapp.models import TrayType
                                tray_type_obj = TrayType.objects.get(tray_type=batch_obj.tray_type)
                                tray_capacity = tray_type_obj.tray_capacity
                            except TrayType.DoesNotExist:
                                pass
                        
                        if not tray_capacity:
                            # Try to get from model master
                            if batch_obj and batch_obj.model_stock_no and batch_obj.model_stock_no.tray_capacity:
                                tray_capacity = batch_obj.model_stock_no.tray_capacity
                        
                        if not tray_capacity:
                            raise ValueError(f"Tray capacity not configured for batch {batch_obj.batch_id}")
                        
                        # Get existing tray IDs from original lot's delink table (skip scanned ones)
                        existing_trays = JigLoadTrayId.objects.filter(
                            lot_id=lot_id, 
                            batch_id=batch_obj
                        ).order_by('date').values_list('tray_id', flat=True)
                        
                        # Find trays not used in valid_trays (scanned trays)
                        scanned_tray_ids = [t['tray_id'] for t in valid_trays]
                        half_filled_tray_ids = [t.get('tray_id') for t in half_filled_tray_data if t.get('tray_id')]
                        used_tray_ids = scanned_tray_ids + half_filled_tray_ids
                        
                        available_trays = [tray_id for tray_id in existing_trays if tray_id not in used_tray_ids]
                        
                        auto_tray_counter = 0
                        while remaining_broken_cases > 0 and auto_tray_counter < len(available_trays):
                            cases_for_this_tray = min(remaining_broken_cases, tray_capacity)
                            tray_id = available_trays[auto_tray_counter]
                            
                            JigLoadTrayId.objects.create(
                                lot_id=new_lot_id,
                                tray_id=tray_id,
                                tray_quantity=cases_for_this_tray,
                                batch_id=batch_obj,
                                user=request.user,
                                new_tray=True
                            )
                            remaining_broken_cases -= cases_for_this_tray
                            auto_tray_counter += 1

                    # Create JigDetails for broken lot
                    broken_jig_detail_data = {
                        'jig_qr_id': f"{jig_qr_id}-BROKEN",
                        'jig_type': jig_type,
                        'jig_capacity': jig_capacity,
                        'total_cases_loaded': remaining_cases,
                        'empty_slots': 0,
                        'faulty_slots': 0,
                        'broken_hooks': broken_hooks_count,
                        'no_of_model_cases': [draft_data.get('plating_stk_no', '')],
                        'new_lot_ids': [new_lot_id],
                        'lot_id_quantities': {new_lot_id: remaining_cases},
                        'lot_id': new_lot_id,
                        'draft_save': False,
                        'created_by': request.user,
                        'ep_bath_type': data.get('ep_bath_type', 'Bright'),
                        'plating_color': data.get('plating_color', 'Default'),
                        'forging': forging_info,
                        'delink_tray_data': [],
                        'half_filled_tray_data': half_filled_tray_data,
                        'no_of_cycle': int(draft_data.get('no_of_cycle', 1)),
                    }

                    # Create JigDetails for broken lot
                    JigDetails.objects.update_or_create(
                        lot_id=new_lot_id,
                        jig_qr_id=f"{jig_qr_id}-BROKEN",
                        defaults=broken_jig_detail_data
                    )
                    
                except Exception as e:
                    print(f"❌ Error creating broken lot: {str(e)}")
                    # Don't fail the entire operation, just log the error
                    remaining_cases = 0  # Reset to skip further processing

            # Map scanned tray IDs to calculated quantities
            for idx, tray in enumerate(valid_trays):
                # Use calculated quantity if available, otherwise use scanned quantity as fallback
                correct_qty = distribution_quantities[idx] if idx < len(distribution_quantities) else tray['tray_qty']
                
                JigLoadTrayId.objects.update_or_create(
                    lot_id=lot_id,
                    tray_id=tray['tray_id'],
                    batch_id=batch_obj,
                    defaults={
                        'tray_quantity': correct_qty,
                        'user': request.user,
                        'new_tray': False
                    }
                )

            # Mark used trays as delinked to prevent reuse
            for tray in valid_trays:
                JigLoadTrayId.objects.filter(
                    lot_id=lot_id,
                    tray_id=tray['tray_id'],
                    batch_id=batch_obj
                ).update(delink_tray=True)

            # Mark half-filled trays as delinked
            if half_filled_tray_data:
                for tray in half_filled_tray_data:
                    tray_id = tray.get('tray_id')
                    if tray_id:
                        JigLoadTrayId.objects.filter(
                            lot_id=lot_id,
                            tray_id=tray_id,
                            batch_id=batch_obj
                        ).update(delink_tray=True)

            # Mark automatic trays used for broken lot as delinked in original lot
            if remaining_cases > 0 and 'available_trays' in locals() and 'auto_tray_counter' in locals():
                for tray_id in available_trays[:auto_tray_counter]:
                    JigLoadTrayId.objects.filter(
                        lot_id=lot_id,
                        tray_id=tray_id,
                        batch_id=batch_obj
                    ).update(delink_tray=True)

            # JigLoadTrayId for broken lot already created above

            try:
                stock = TotalStockModel.objects.get(lot_id=lot_id)
                stock.Jig_Load_completed = True
                stock.jig_draft = False
                stock.save()
            except TotalStockModel.DoesNotExist:
                pass

            jig_obj, _ = Jig.objects.get_or_create(jig_qr_id=jig_qr_id)
            jig_obj.is_loaded = True
            jig_obj.current_user = None
            jig_obj.locked_at = None
            jig_obj.drafted = False
            jig_obj.save()

            # --- NEW LOGIC: If original lot qty > jig_capacity, create new lot for excess cases ---
            if jig_capacity and original_stock.total_stock > jig_capacity:
                remaining_cases = original_stock.total_stock - jig_capacity
                new_lot_id = f"LID{timezone.now().strftime('%d%m%Y%H%M%S')}{remaining_cases:04d}"
                TotalStockModel.objects.create(
                    batch_id=original_stock.batch_id,
                    model_stock_no=original_stock.model_stock_no,
                    version=original_stock.version,
                    total_stock=remaining_cases,
                    polish_finish=original_stock.polish_finish,
                    plating_color=original_stock.plating_color,
                    lot_id=new_lot_id,
                    created_at=timezone.now(),
                    Jig_Load_completed=False,
                    jig_draft=True,
                    last_process_date_time=timezone.now(),
                    last_process_module="Jig Loading",
                )
                extra_response = {
                    'new_lot_created': True,
                    'new_lot_id': new_lot_id,
                    'remaining_cases': remaining_cases
                }
                # Update original lot qty to jig_capacity
                original_stock.total_stock = jig_capacity
                original_stock.save()
                # Load only jig_capacity in this jig
                total_cases_loaded = jig_capacity
                jig_detail.total_cases_loaded = total_cases_loaded
                jig_detail.save()
            else:
                extra_response = {}

            return JsonResponse({
                'success': True,
                'message': 'Jig Saved Successfully',
                'jig_id': jig_detail.id,
                'total_cases_loaded': total_cases_loaded,
                'redirect_url': '/jig_loading/JigCompletedTable/',
                **extra_response
            })

        except Exception as e:
            logger.error(f"💥 Exception in JigSaveAPIView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Failed to save jig: {str(e)}'
            }, status=500)
            
                     
# Jig Loading Complete Table - Main View 
class JigCompletedTable(TemplateView):
    template_name = "JigLoading/Jig_CompletedTable.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed_qs = TotalStockModel.objects.filter(Jig_Load_completed=True)
        completed_data = []
        for stock in completed_qs:
            plating_stk_no = (
                getattr(stock.batch_id, 'plating_stk_no', None)
                or getattr(stock.model_stock_no, 'plating_stk_no', None)
            )
            polishing_stk_no = (
                getattr(stock.batch_id, 'polishing_stk_no', None)
                or getattr(stock.model_stock_no, 'polishing_stk_no', None)
            )
            tray_capacity = JigView.get_tray_capacity(stock)
            jig_type = ''
            jig_capacity = ''
            if stock.model_stock_no:
                jig_master = JigLoadingMaster.objects.filter(model_stock_no=stock.model_stock_no).first()
                if jig_master:
                    jig_type = jig_master.jig_type
                    jig_capacity = jig_master.jig_capacity

            # Fetch JigDetails for this lot (for Jig ID, loaded date, etc.)
            jig_detail = JigDetails.objects.filter(lot_id=stock.lot_id).order_by('-date_time').first()

            # Use JigDetails.total_cases_loaded as the effective lot quantity, fallback to stock.total_stock
            lot_qty = jig_detail.total_cases_loaded if jig_detail else (stock.total_stock or 0)
            
            # Calculate number of trays based on actual JigLoadTrayId entries for this lot
            actual_tray_count = JigLoadTrayId.objects.filter(
                lot_id=stock.lot_id, 
                batch_id=stock.batch_id
            ).count()
            
            # Use actual tray count if available, otherwise calculate from lot_qty
            if actual_tray_count > 0:
                no_of_trays = actual_tray_count
            else:
                no_of_trays = 0
                if tray_capacity and tray_capacity > 0 and lot_qty > 0:
                    no_of_trays = (lot_qty // tray_capacity) + (1 if lot_qty % tray_capacity else 0)

            completed_data.append({
                'batch_id': stock.batch_id.batch_id if stock.batch_id else '',
                'jig_loaded_date_time': (
                    jig_detail.jig_loaded_date_time
                    if jig_detail and jig_detail.jig_loaded_date_time
                    else (jig_detail.date_time if jig_detail else '')
                ),
                'lot_id': stock.lot_id,
                'lot_plating_stk_nos': plating_stk_no or 'No Plating Stock No',
                'lot_polishing_stk_nos': polishing_stk_no or 'No Polishing Stock No',
                'plating_color': stock.plating_color.plating_color if stock.plating_color else '',
                'polish_finish': stock.polish_finish.polish_finish if stock.polish_finish else '',
                'lot_version_names': stock.version.version_internal if stock.version else '',
                'tray_type': getattr(stock.batch_id, 'tray_type', ''),
                'tray_capacity': getattr(stock.batch_id, 'tray_capacity', ''),
                'calculated_no_of_trays': no_of_trays,
                'total_cases_loaded': jig_detail.total_cases_loaded if jig_detail else '',
                'jig_type': jig_type,
                'jig_capacity': jig_capacity,
                'jig_qr_id': jig_detail.jig_qr_id if jig_detail else '',
                'jig_loaded_date_time': jig_detail.jig_loaded_date_time if jig_detail else '',
                'model_images': [img.master_image.url for img in stock.model_stock_no.images.all()] if stock.model_stock_no else [],
                'audio_remark': getattr(jig_detail, 'pick_remarks', ''),
                'IP_jig_pick_remarks': getattr(jig_detail, 'IP_jig_pick_remarks', ''),
            })
        context['jig_details'] = completed_data
        return context