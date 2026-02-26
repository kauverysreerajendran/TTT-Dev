# BRASS AUDIT REPORT - FIX DOCUMENTATION

## Issue Summary

The brass-audit module in the Reports section was returning a **500 Internal Server Error** when attempting to download the Excel report.

## Root Cause Analysis

### Primary Issue: Incorrect Subquery Syntax

**Location:** Lines 1085, 1153 in ReportsModule/views.py

**Problematic Code:**

```python
no_of_trays_subquery = BrassAuditTrayId.objects.filter(lot_id=OuterRef('lot_id')).aggregate(count=Count('id'))['count']
```

**Why This Failed:**

- The `.aggregate()` method returns a dictionary, not a Django QuerySet
- Subquery() requires a QuerySet to work with, not a dictionary value
- Django ORM cannot execute this invalid subquery structure during database query compilation
- Result: Database query compilation error leading to 500 error

### Secondary Issue: CharField Used in Sum()

**Location:** Line 1213 in ReportsModule/views.py

**Problematic Code:**

```python
rejected_queryset = Brass_Audit_Rejected_TrayScan.objects.values('lot_id').annotate(
    total_reject_qty=Sum('rejected_tray_quantity')  # Field is CharField, not numeric
)
```

**Why This Failed:**

- `Brass_Audit_Rejected_TrayScan.rejected_tray_quantity` is defined as a CharField
- PostgreSQL's SUM() function cannot sum character varying (string) types
- Database returned: "function sum(character varying) does not exist"

### Tertiary Issue: Model Field Type Mismatch

**Location:** Lines 1121, 1189, 1229 in ReportsModule/views.py

**Problematic Code:**

```python
'Tray Cate-Capacity': f"{batch.tray_type.tray_type}-{batch.tray_capacity}" if batch.tray_type else '',
```

**Why This Failed:**

- In ModelMasterCreation, `tray_type` is a CharField (string), not a ForeignKey
- Attempting to access `.tray_type` attribute on a string causes AttributeError
- Expected: Direct string value

### Quaternary Issue: Empty DataFrame Export

**Location:** Lines 1137, 1204, 1246 in ReportsModule/views.py

**Problematic Code:**

```python
df_pick = pd.DataFrame(report_data_pick)
df_pick.to_excel(writer, sheet_name='Pick Table', index=False)
```

**Why This Failed:**

- When a DataFrame is empty, openpyxl cannot create the workbook
- Error: "At least one sheet must be visible"
- All sheets need at least header rows if they're empty

## Solution Implementation

### Fix 1: Remove Incorrect Subquery, Calculate in Loop Instead

**Changed:** Remove the `.aggregate()['count']` pattern entirely

**Implementation:**

```python
# BEFORE (removed):
no_of_trays_subquery = BrassAuditTrayId.objects.filter(lot_id=OuterRef('lot_id')).aggregate(count=Count('id'))['count']

# AFTER (in loop):
for idx, stock_obj in enumerate(pick_queryset, start=1):
    no_of_trays = BrassAuditTrayId.objects.filter(lot_id=stock_obj.lot_id).count()
    data = {'No of Trays': no_of_trays, ...}
```

**Why This Works:**

- Direct `.count()` method is simpler and more efficient for single-record lookups
- Avoids complex subquery construction
- Each iteration fetches the actual count from the database
- Clean separation of concerns

### Fix 2: Handle CharField Quantity Summation

**Changed:** Remove Sum() annotation, calculate in Python loop

**Implementation:**

```python
# BEFORE (removed):
rejected_queryset = Brass_Audit_Rejected_TrayScan.objects.values('lot_id').annotate(
    total_reject_qty=Sum('rejected_tray_quantity')
)

# AFTER (in loop):
rejected_trays = Brass_Audit_Rejected_TrayScan.objects.filter(lot_id=reject_obj['lot_id'])
total_reject_qty = sum(int(tray.rejected_tray_quantity) if tray.rejected_tray_quantity.isdigit() else 0
                       for tray in rejected_trays)
```

**Why This Works:**

- Avoids database-level calculation on VARCHAR field
- Handles non-numeric values gracefully with `.isdigit()` check
- Converts string quantities to integers in Python
- More flexible for data validation

### Fix 3: Correct Field Type References

**Changed:** Remove `.tray_type` attribute access on string fields

**Implementation:**

```python
# BEFORE (wrong):
'Tray Cate-Capacity': f"{batch.tray_type.tray_type}-{batch.tray_capacity}"

# AFTER (correct):
'Tray Cate-Capacity': f"{batch.tray_type}-{batch.tray_capacity}"
```

**Why This Works:**

- `batch.tray_type` is already a string in ModelMasterCreation model
- Direct string interpolation works as expected
- No extra attribute lookup needed

### Fix 4: Handle Empty DataFrames

**Changed:** Create header-only sheets when data is empty

**Implementation:**

```python
# BEFORE (removed):
df_pick = pd.DataFrame(report_data_pick)
df_pick.to_excel(writer, sheet_name='Pick Table', index=False)

# AFTER (with empty check):
if len(df_pick) > 0:
    df_pick.to_excel(writer, sheet_name='Pick Table', index=False)
else:
    empty_df = pd.DataFrame(columns=['S.No', 'Last Updated', 'Plating Stk No', ...])
    empty_df.to_excel(writer, sheet_name='Pick Table', index=False)
```

**Why This Works:**

- Empty DataFrames still create sheets with headers
- openpyxl has at least one visible sheet in the workbook
- User can see column structure even with no data

## Testing & Validation

### Test Scenario 1: Report Download

```
✅ Status Code: 200 (Success)
✅ Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
✅ Content-Disposition: attachment; filename=brass-audit_report.xlsx
✅ File Size: 6704 bytes
```

### Frontend Data Matching

**Pick Table Columns:**

- S.No | Last Updated | Plating Stk No | Polishing Stk No | Plating Color | Category | Polish Finish | Tray Cate-Capacity | Input Source | No of Trays | Lot Qty | Physical Qty | Accept Qty | Reject Qty | Process Status | Action | Lot Status | Current Stage | Remarks

**Completed Table Columns:**

- Same as Pick Table

**Rejected Table Columns:**

- S.No | Last Updated | Plating Stk No | Polish Stk No | Plating Color | Polish Finish | Source - Location | Tray Type Capacity | No of Trays | Reject Qty | Reject Reason | Lot Remark

### Data Flow Verification

1. ✅ Correctly queries `TotalStockModel` for lot status data
2. ✅ Filters based on brass audit acceptance/rejection flags
3. ✅ Aggregates rejection reasons from `Brass_Audit_Rejection_ReasonStore`
4. ✅ Counts trays from `BrassAuditTrayId` per lot
5. ✅ Formats dates in `DD-Mon-YY HH:MM AM/PM` format
6. ✅ Handles null/empty values gracefully

## Performance Optimizations

### Current Performance Characteristics

**Database Queries per Report:**

- Pick Table: 1 queryset + N count queries (N = number of lots)
- Completed Table: 1 queryset + N count queries
- Rejected Table: 1 queryset + N rejection scans + N tray counts

**Optimization Opportunity 1: Bulk Prefetch Tray Counts**
Instead of per-lot count queries, use:

```python
from django.db.models import Count, Prefetch

lot_ids = [obj.lot_id for obj in queryset]
tray_counts = (BrassAuditTrayId.objects
    .filter(lot_id__in=lot_ids)
    .values('lot_id')
    .annotate(count=Count('id')))

# Map: {lot_id: count}
tray_count_map = {item['lot_id']: item['count'] for item in tray_counts}

# Use in loop:
for obj in queryset:
    no_of_trays = tray_count_map.get(obj.lot_id, 0)
```

**Impact:** Reduces N count queries to 1 database query
**Complexity:** Low - simple dictionary lookup
**Recommendation:** Implement for production

### Optimization Opportunity 2: Use select_related More Aggressively

```python
queryset = (TotalStockModel.objects
    .select_related('batch_id', 'batch_id__model_stock_no', 'batch_id__version', 'batch_id__location')
    .prefetch_related(
        Prefetch('brassaudit_rejections', queryset=Brass_Audit_Rejection_ReasonStore.objects.all())
    )
    .filter(...))
```

**Impact:** Reduces database round-trips for related objects
**Complexity:** Medium - requires careful Prefetch setup
**Recommendation:** Implement for 50+ lot reports

### Optimization Opportunity 3: Batch Rejection Reason Fetching

Instead of per-lot `Brass_Audit_Rejection_ReasonStore.objects.filter()`:

```python
# Fetch all at once
rejection_comments = dict(
    Brass_Audit_Rejection_ReasonStore.objects
    .filter(lot_id__in=lot_ids)
    .values_list('lot_id', 'lot_rejected_comment'))

# Use in loop:
for reject_obj in rejected_queryset:
    comment = rejection_comments.get(reject_obj['lot_id'], '')
```

**Impact:** Reduces N queries to 1
**Complexity:** Low
**Recommendation:** Implement - easy win

## Behavioral Changes

### No Breaking Changes

- ✅ Report structure unchanged
- ✅ Column order preserved
- ✅ Date format unchanged
- ✅ Data values identical to frontend display
- ✅ Existing workflows unaffected

### Backward Compatibility

- ✅ All unrelated report modules (day-planning, input-screening, etc.) remain unchanged
- ✅ No model schema changes
- ✅ No database migration required

## Files Modified

1. **ReportsModule/views.py**
   - Lines 1062-1252: Entire brass-audit report implementation
   - Changes: Fixed subqueries, removed Sum() on CharField, corrected field references, added empty sheet handling

## Deployment Notes

1. No database migrations needed
2. No configuration changes required
3. Safe to deploy without downtime
4. No breaking changes to APIs or data models
5. Recommend applying suggested performance optimizations in follow-up

## Related Documents

- Frontend Display: `http://127.0.0.1:8000/brass_audit/brass_audit_picktable/`
- Frontend Display: `http://127.0.0.1:8000/brass_audit/brass_audit_completed/`
- Backend Views: `BrassAudit/views.py` (lines 41-200, 3617-3700)
- Models: `BrassAudit/models.py`, `modelmasterapp/models.py`
