# Day 1: Landing Page Removal — Quick Start
**Start Time**: 2026-10-19 14:06 UTC  
**Goal**: Remove landing page, redirect to /explore-places/  
**Estimated Time**: 2–3 hours

---

## Step 1: Create Git Branch (1 min)

```bash
cd C:\Users\ADMIN\Desktop\BSIT3A-DJANGO-ExploreAnywhere
git checkout -b cleanup/sprint
git pull origin main
```

**Result**: You're now on `cleanup/sprint` branch ✓

---

## Step 2: Identify Landing Page Files (5 min)

### Find the landing page template
```bash
# Search for landing page files
find . -name "*landing*" -o -name "*home*" -o -name "*index*" | grep -v node_modules | grep -v __pycache__
```

**Look for**:
- `apps/core/templates/landing.html` or `home.html` or `index.html`
- `apps/core/templates/` directory

### Check current URLs
```bash
# Look at current URL routing
cat mysite/urls.py | grep -A 5 "path(''"
```

**Expected**: Shows root path `/` pointing to landing page view

---

## Step 3: Find & Update URLs (15 min)

### Open `mysite/urls.py`
```python
# Current (likely):
path('', views.landing_page, name='landing'),  # or similar

# Change to:
path('', RedirectView.as_view(url='/explore-places/', permanent=True), name='home'),
```

**Steps**:
1. Open file: `C:\Users\ADMIN\Desktop\BSIT3A-DJANGO-ExploreAnywhere\mysite\urls.py`
2. Find the root path (`path('')`)
3. Replace with redirect to `/explore-places/`
4. Add import: `from django.views.generic import RedirectView`

**Verify**:
```python
# At top of file:
from django.views.generic import RedirectView

# In urlpatterns:
path('', RedirectView.as_view(url='/explore-places/', permanent=True), name='home'),
```

---

## Step 4: Find & Delete Landing Page View (10 min)

### Find the view
```bash
# Search for landing view
grep -r "def landing" apps/
grep -r "def home" apps/
grep -r "def index" apps/
```

**Look in**:
- `apps/core/views.py` (most likely)
- Could also be in `apps/users/views.py`

### Delete or comment out
**Find this**:
```python
def landing_page(request):
    # ... code ...
    return render(request, 'landing.html', {...})
```

**Delete the entire function** (mark it with `# DELETED` if unsure)

---

## Step 5: Find & Delete Landing Page Template (10 min)

### Find the template file
```bash
find apps/ -name "landing.html" -o -name "home.html" -o -name "index.html" | grep -v __pycache__
```

**Most likely**: `apps/core/templates/landing.html` or similar

### Delete it
```bash
# Or just rename for safety
mv apps/core/templates/landing.html apps/core/templates/landing.html.backup
```

---

## Step 6: Test the Redirect (20 min)

### Start Django dev server
```bash
# In your project root
python manage.py runserver
```

### Test in browser
```
Go to: http://localhost:8000/
Expected: Redirects to http://localhost:8000/explore-places/

If it works: ✓ Success!
If 404 error: Check Step 3 & 4
```

### Check Django console
- Look for any `ImportError` or `NameError`
- Fix any issues before continuing

---

## Step 7: Remove Unused Code (10 min)

### Remove buttons from landing
**Search for**:
- "Explore Subscription" button code
- "Become a Partner" card code
- "My Dimension" button code

**These might be in**:
- Template files
- Static HTML
- JavaScript files

**Delete or comment out** any references

### Search command:
```bash
grep -r "Explore Subscription" apps/
grep -r "Become a Partner" apps/
grep -r "My Dimension" apps/
```

---

## Step 8: Commit Your Work (5 min)

```bash
git add .
git commit -m "Day 1: Remove landing page, redirect to /explore-places/"
git push origin cleanup/sprint
```

**Result**: Your work is saved! ✓

---

## Step 9: Verify No Broken Links (15 min)

### Test key pages
1. [ ] Home redirect works (/ → /explore-places/)
2. [ ] Explore places loads (localhost:8000/explore-places/)
3. [ ] Place detail works
4. [ ] Navigation works
5. [ ] No 404 errors in console

### Quick test script
```bash
# Check for common errors
curl http://localhost:8000/
# Should show 302 redirect or redirect to explore-places

curl http://localhost:8000/explore-places/
# Should show 200 OK and page content
```

---

## 🎉 Day 1 Complete!

**What you did**:
- ✅ Removed landing page template
- ✅ Removed landing page view
- ✅ Added redirect from / to /explore-places/
- ✅ Removed unused buttons
- ✅ Committed to git

**Time spent**: ~2 hours (or less!)

---

## If You Hit Issues

### Issue: "landing_page view doesn't exist"
**Solution**: Search harder with:
```bash
grep -r "landing" . --include="*.py" | grep "def \|url"
```

### Issue: "Template not found"
**Solution**: Django will show you the path. Find it there.

### Issue: "Redirect not working"
**Solution**: Make sure you imported `RedirectView`:
```python
from django.views.generic import RedirectView
```

### Issue: "Import error after changes"
**Solution**: 
```bash
python manage.py check
```
This tells you exactly what's wrong.

---

## When You're Tired

**Just do this**:
```bash
git add .
git commit -m "PAUSE: Day 1 [describe what's done]"
git push origin cleanup/sprint
```

**Tomorrow**: `git checkout cleanup/sprint` and continue!

---

## Next Steps (After Day 1 Complete)

1. Move to **Day 2: Navigation Consolidation**
2. Or save for tomorrow
3. Update checkpoint log

**See**: `UI_CLEANUP_SPRINT_PLAN.md` for Day 2

---

**Ready? Let's go! 🚀**
