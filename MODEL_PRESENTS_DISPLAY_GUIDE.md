# INPROCESS INSPECTION - MODEL PRESENTS DISPLAY GUIDE

## Visual Representation

### BEFORE (Multiple Circles):

```
┌─────────────────────────────────────────┐
│ Model Presents                          │
├─────────────────────────────────────────┤
│ 🔴 🟡 🟢 🔵                             │
│ Multiple colored circles for each model  │
└─────────────────────────────────────────┘
```

### AFTER (Single Circle):

```
┌─────────────────────────────────────────┐
│ Model Presents                          │
├─────────────────────────────────────────┤
│ 🔴 2617 ▼                              │
│ Single circle + Model number + Expand   │
└─────────────────────────────────────────┘
```

---

## Feature Behavior

### Case 1: With Model Data

```
Input: no_of_model_cases = ['2617', '2618', '2619']
       model_colors = {'2617': '#e74c3c', '2618': '#f1c40f', ...}

Display:
  🔴 2617 ▼

Clicking ▼ (expand arrow):
  → Opens gallery modal
  → Shows all 3 models: 2617, 2618, 2619
  → Each with color circle and image (or placeholder)
```

### Case 2: No Model Data

```
Input: no_of_model_cases = None or []

Display:
  ⚪ N/A ▼

Clicking ▼ (expand arrow):
  → Opens empty gallery
  → Or shows message: "No models available"
```

---

## CSS Styling Details

```css
/* Single color circle */
.model-circle {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    margin-right: 6px;
}

/* Model number text reference */
<span style="font-size:11px; color:#666; vertical-align:middle;">
    {{ first_model }}
</span>

/* Expand arrow icon */
.expand-model-remark {
    display: inline-block;
    width: 18px;
    height: 18px;
    vertical-align: middle;
    cursor: pointer;
    margin-left: 4px;
    title: "View model gallery"
}

/* Fallback when no data */
background: #ccc;  /* Gray circle */
color: #999;       /* Lighter text */
text-content: "N/A"
```

---

## JavaScript Integration

The expand arrow works with existing JavaScript handlers:

```javascript
// When user clicks the expand arrow
$(".expand-model-remark").click(function () {
  // Reads data attributes from <td>
  var images = $(this).closest("td").data("images");
  var colors = $(this).closest("td").data("model-colors");
  var models = $(this).closest("td").data("model-list");

  // Opens gallery modal with all models
  showModelGallery(models, colors, images);
});
```

### Data Attributes Available:

```html
<td
  data-images='{"2617": ["/img1.jpg"], "2618": ["/img2.jpg"]}'
  data-model-colors='{"2617": "#e74c3c", "2618": "#f1c40f"}'
  data-model-list='["2617", "2618", "2619"]'
></td>
```

---

## Backend Data Preparation

### The `apply_existing_logic()` Method

Prepares three key dictionaries:

```python
1. model_colors: Dict[model_no → color_hex]
   Example: {'2617': '#e74c3c', '2618': '#f1c40f'}

2. model_images: Dict[model_no → [image_urls]]
   Example: {
       '2617': ['/media/model_images/2617_01.jpg'],
       '2618': ['/media/model_images/2618_01.jpg', '/media/model_images/2618_02.jpg']
   }

3. no_of_model_cases: List[model_no]
   Example: ['2617', '2618', '2619']

   From: JigCompleted.no_of_model_cases (JSONField)
```

### Color Palette (Consistent Across Sessions)

```python
color_palette = [
    "#e74c3c",  # 0: Red
    "#f1c40f",  # 1: Yellow
    "#2ecc71",  # 2: Green
    "#3498db",  # 3: Blue
    "#9b59b6",  # 4: Purple
    ... (20 more colors)
]

Model colors are assigned once and cached in _global_model_colors:
- First occurrence: Gets color_palette[0]
- Second occurrence: Gets color_palette[1]
- etc.
```

---

## Template Logic Flow

```
START: Render Model Presents cell
  │
  ├─→ Does no_of_model_cases exist?
  │   │
  │   ├─ YES (has models):
  │   │   ├─ Get first_model = no_of_model_cases[0]
  │   │   ├─ Look up color: model_colors[first_model]
  │   │   ├─ Display: [COLOR_CIRCLE] model_number [DOWN_ARROW]
  │   │   └─ Data: Pass all models/colors/images to expand handler
  │   │
  │   └─ NO (no models):
  │       └─ Display: [GRAY_CIRCLE] N/A [DOWN_ARROW]
  │
  └─ End: Render complete

When user clicks [DOWN_ARROW]:
  → JavaScript reads data-* attributes
  → Opens gallery modal
  → Shows all models with images/colors
```

---

## Database Queries (Data Sources)

### Query 1: Get Plating Color

```python
# Source: TotalStockModel
tsm = TotalStockModel.objects.filter(lot_id=jig.lot_id).first()
plating_color = tsm.plating_color.plating_color if tsm else None
```

### Query 2: Get Tray Info

```python
# Source: ModelMaster via TotalStockModel.batch_id
tsm = TotalStockModel.objects.filter(lot_id=jig.lot_id).first()
if tsm and tsm.batch_id:
    tray_type = tsm.batch_id.model_stock_no.tray_type.tray_type
    tray_capacity = tsm.batch_id.model_stock_no.tray_capacity
```

### Query 3: Get Model Images

```python
# Source: ModelMaster.images M2M relationship
for model_no in jig_detail.no_of_model_cases:
    model_master = ModelMaster.objects.filter(
        model_no=extract_numeric(model_no)
    ).prefetch_related('images').first()

    if model_master and model_master.images.exists():
        images = [img.master_image.url for img in model_master.images.all()]
    else:
        images = ['/static/assets/images/imagePlaceholder.png']
```

---

## Configuration & Customization

### To Change Circle Size:

```html
<!-- Current: 14px × 14px -->
<span class="model-circle" style="width:14px;height:14px;...">
  <!-- Example: Make larger -->
  <span class="model-circle" style="width:20px;height:20px;..."></span
></span>
```

### To Change Model Number Font:

```html
<!-- Current: 11px gray -->
<span style="font-size:11px;color:#666;">{{ first_model }}</span>

<!-- Example: Larger, darker -->
<span style="font-size:13px;color:#333;font-weight:bold;"
  >{{ first_model }}</span
>
```

### To Change Expand Arrow Icon:

```html
<!-- Current: SVG down arrow -->
<svg width="18" height="18" viewBox="0 0 18 18">
  <circle cx="9" cy="9" r="8" fill="#bbb" />
  <polygon points="6,7 12,7 9,12" fill="#fff" />
</svg>

<!-- Alternative: Unicode arrow -->
<span style="font-size:16px;">▼</span>

<!-- Alternative: Font icon (e.g., FontAwesome) -->
<i class="fas fa-chevron-down"></i>
```

---

## Troubleshooting

### Issue: Circle shows, but model number is blank

**Cause:** `first_model` variable not being set  
**Fix:** Ensure `no_of_model_cases` is a non-empty list in backend

### Issue: Wrong color displayed

**Cause:** Model not in `model_colors` dictionary  
**Fix:** Check `apply_existing_logic()` is building the colors dict

### Issue: Expand arrow doesn't work

**Cause:** JavaScript handler not connected  
**Fix:** Verify `.expand-model-remark` class selector matches template

### Issue: Gallery shows placeholder instead of image

**Cause:** ModelMaster.images not populated for the model  
**Fix:** Add images to ModelMaster in admin panel

### Issue: Performance slow when loading page

**Cause:** Too many database queries in loop  
**Fix:** Ensure `prefetch_related('images')` is used in ModelMaster queries

---

## Performance Optimization Tips

1. **Cache model colors:**

   ```python
   # Already implemented via _global_model_colors dictionary
   # Colors assigned once, reused for all subsequent renders
   ```

2. **Batch load images:**

   ```python
   # Use prefetch_related instead of separate queries
   .prefetch_related('images')  # ✓ Already implemented
   ```

3. **Limit gallery load:**
   ```python
   # Consider pagination if model_images is very large
   images_per_page = 5  # Example
   ```

---

## Testing Checklist

- [ ] Displays single circle for first model
- [ ] Shows model number next to circle
- [ ] Shows gray circle + N/A when no models
- [ ] Expand arrow is clickable
- [ ] Expand arrow opens gallery modal
- [ ] Gallery shows all models (not just first)
- [ ] Gallery displays model images or placeholder
- [ ] Images are properly sized
- [ ] No broken links in gallery
- [ ] Color assignment is consistent across page reloads
- [ ] Works with various model numbers
- [ ] Works when model_cases is empty
- [ ] Works when model_cases has 1 model
- [ ] Works when model_cases has many models

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Status:** Production Ready
