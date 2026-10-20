---
name: ui-cleanup-sprint-plan
description: 1-2 week sprint plan to remove redundancy and consolidate UI
type: project
---

# UI Cleanup Sprint Plan
**Start Date**: 2026-10-19  
**Duration**: 1–2 weeks  
**Goal**: Remove clutter, consolidate navigation, standardize UI  
**Target**: Ready for Phase 7A implementation

---

## Sprint Overview

### What We're Doing
- Removing 13 redundant UI elements
- Consolidating navigation
- Standardizing headers & footers
- Cleaning up confusing buttons
- Removing placeholder/unused features

### What We're NOT Doing
- Adding new features
- Changing database schema
- Rewriting views (just organizing existing ones)
- Major design overhaul

### Expected Outcome
Cleaner, faster app with clearer user flows

---

## Week 1: Core Cleanup

### Day 1: Landing Page Removal (2–3 hours)
**Remove**: Screenshot #1 (complex hero section)

**Tasks**:
1. [ ] Delete or repurpose `landing_page.html` template
2. [ ] Update root URL `/` to redirect to `/explore-places/`
3. [ ] Remove "Explore Subscription" button code
4. [ ] Remove "Become a Partner" card code
5. [ ] Remove "My Dimension" button code
6. [ ] Test redirect works

**Files to Modify**:
- `mysite/urls.py` — Update root path
- `apps/core/templates/` — Remove landing template
- `apps/core/views.py` — Update root view

**Verification**:
- [ ] `/` redirects to `/explore-places/`
- [ ] No 404 errors
- [ ] No broken links

---

### Day 2: Navigation Consolidation (3–4 hours)
**Remove**: Duplicate navigation buttons

**Tasks**:
1. [ ] Remove "Saved Places" button from place detail page action bar
2. [ ] Remove "My Journey" button from place detail page action bar
3. [ ] Keep only in top navigation bar
4. [ ] Remove "Draft Dashboard" label from all pages
5. [ ] Move "Staff Dashboard" to hidden admin nav (show only for staff)
6. [ ] Update base template with consolidated nav

**Files to Modify**:
- `apps/places/templates/place_detail.html` — Remove action buttons
- `apps/core/templates/base.html` — Update navbar
- `apps/users/templates/user_nav.html` — Conditional staff nav
- All page templates — Remove "Draft" labels

**Current Nav** (10 items):
```
ExploreAnywhere | Explore Places | Saved Places | My Journey | More | 
Staff Dashboard | Draft Dashboard | Login | Signup | Help
```

**New Nav** (6 items):
```
ExploreAnywhere | Explore Places | Saved Places | My Journey | Help | [User Menu]
```

**Verification**:
- [ ] All main pages have consistent nav
- [ ] Staff users see "Staff Dashboard"
- [ ] Regular users don't see staff links
- [ ] No broken navigation

---

### Day 3: Search/Filter Consolidation (3–4 hours)
**Consolidate**: Multiple search entry points into ONE

**Current State** (3 different search pages):
- Screenshot #2: Explore Places search
- Screenshot #9: Discover Kabankalan (duplicate)
- Screenshot #10: Discover Kabankalan Map (duplicate)

**Tasks**:
1. [ ] Choose ONE primary search page design (recommend Screenshot #2)
2. [ ] Delete redundant search pages/views
3. [ ] Update all "Discover" links to point to primary search
4. [ ] Consolidate search filters into one form
5. [ ] Test all search entry points work

**Files to Modify**:
- `apps/search/views.py` — Keep one search view, remove duplicates
- `apps/search/urls.py` — Update URL routing
- Search templates — Keep one, delete others
- All pages with search links — Point to unified search

**New Search UX**:
```
/explore-places/ (primary search)
  - Query bar: "What are you looking for?"
  - Filters: Category, Hobby, Sort
  - View toggle: List / Map
  - Results: Grid of places
```

**Verification**:
- [ ] One clear search entry point
- [ ] All links redirect correctly
- [ ] No duplicate search pages
- [ ] Filters work on all views

---

### Day 4: Button/CTA Cleanup (2–3 hours)
**Clarify/Remove**: Confusing buttons

**Tasks**:
1. [ ] "Report a Visit" button — Clarify or merge with review
   - Option A: Rename to "Log Visit"
   - Option B: Merge "Report Visit + Write Review" into one flow
   - Decide & implement
2. [ ] Remove "Your Next Adventure" recommendations section (Screenshot #4)
3. [ ] Remove "Half-Verified" badge (replace with "Pending" or "Verified")
4. [ ] Standardize all call-to-action button text
5. [ ] Remove "Browse all areas" link (duplicate with nav)

**Button Standardization**:
```
Primary actions (blue): "Explore", "View Details", "Add to Itinerary", "Save"
Secondary actions (gray): "Learn More", "Skip"
Destructive actions (red): "Remove", "Delete"
Pending actions (orange): "Pending Approval", "Review Pending"
```

**Files to Modify**:
- Place detail template — Fix "Report Visit" button
- Dashboard template — Remove recommendations section
- All place cards — Update badge display
- CSS — Standardize button styles

**Verification**:
- [ ] All buttons have clear intent
- [ ] No redundant CTAs
- [ ] Consistent button styling
- [ ] "Report Visit" behavior is clear

---

### Day 5: Headers & Footers Standardization (2–3 hours)
**Standardize**: Inconsistent page headers and footers

**Current Footer Issues**:
- Screenshot #3: "Site Map | User Activities | End Map"
- Screenshot #6: "Site Help | Paper Numbers | Site Map"
- Screenshot #7: "Site Map | User Policies | End Map"

**Tasks**:
1. [ ] Define ONE standard footer for all pages
2. [ ] Update footer in base template
3. [ ] Add consistent header/breadcrumb to all pages
4. [ ] Remove inconsistent footer links
5. [ ] Test footer appears on all pages

**Standard Footer**:
```
© 2026 ExploreAnywhere | Help | About | Privacy | Contact | Site Map
```

**Standard Page Header** (where applicable):
```
Breadcrumb: Home > Category > Page Title
Page Title (h1)
```

**Files to Modify**:
- `apps/core/templates/base.html` — Update footer
- All page templates — Add breadcrumbs/titles
- Static footer CSS — Standardize styling

**Verification**:
- [ ] Same footer on all pages
- [ ] Breadcrumbs work correctly
- [ ] No missing or broken footer links
- [ ] Footer looks good on mobile

---

## Week 2: Testing & Polish

### Day 6-7: Cross-Browser Testing (4–5 hours)
**Test**: All changes work on different browsers/devices

**Tasks**:
1. [ ] Test desktop Chrome
2. [ ] Test desktop Firefox
3. [ ] Test mobile Chrome
4. [ ] Test mobile Safari
5. [ ] Fix any broken layouts
6. [ ] Verify navigation works on mobile
7. [ ] Check all links still work

**Test Checklist**:
- [ ] Homepage redirect works
- [ ] Navigation bar displays correctly
- [ ] Search/filters work
- [ ] Place detail page displays properly
- [ ] Dashboard loads
- [ ] No 404 errors in console
- [ ] No missing images

---

### Day 8: Performance Check (2–3 hours)
**Optimize**: Page load times after cleanup

**Tasks**:
1. [ ] Remove unused CSS from old landing page
2. [ ] Remove unused JavaScript
3. [ ] Clean up template files
4. [ ] Run Django collectstatic
5. [ ] Check page load times

**Tools**:
- Chrome DevTools (Performance tab)
- Django Debug Toolbar (if installed)

**Target**:
- Pages load in < 3 seconds
- No unused CSS/JS

---

### Day 9: Documentation Update (2–3 hours)
**Update**: All docs to reflect cleanup

**Tasks**:
1. [ ] Update QUICK_REFERENCE.md with new URLs
2. [ ] Update INDEX.md navigation guide
3. [ ] Document removed features
4. [ ] Update UI screenshots in docs (optional)
5. [ ] Create CLEANUP_CHANGELOG.md

**CLEANUP_CHANGELOG.md** should list:
- What was removed
- Why it was removed
- When it was removed
- Alternative if applicable

---

### Day 10: Final QA (3–4 hours)
**Verify**: Everything works end-to-end

**Full User Journey Test**:
1. [ ] Land on home → redirects to explore
2. [ ] Search for places → results display
3. [ ] View place details → all info shows
4. [ ] Save place → added to saved list
5. [ ] Create itinerary → itinerary created
6. [ ] Log visit → visit tracked
7. [ ] View dashboard → all stats show
8. [ ] View badges → badges display
9. [ ] Write review → review saved
10. [ ] Logout → logged out

**Staff User Test**:
1. [ ] Staff sees Staff Dashboard link
2. [ ] Staff can access admin functions
3. [ ] Can approve visits
4. [ ] Can moderate reviews

**Bug Fix Log**:
- [ ] Document any bugs found
- [ ] Fix before moving to Phase 7A

---

## Sprint Retrospective (End of Week 2)

### Measure Success
- [ ] All 13 redundant elements removed
- [ ] Navigation consolidated (10 items → 6)
- [ ] One primary search entry point
- [ ] Standard footer on all pages
- [ ] No broken links
- [ ] Full user journey works
- [ ] Performance optimized

### Before/After Comparison
```
BEFORE:
- 3 search pages (duplicate)
- 10 nav items (redundant)
- Multiple inconsistent footers
- Confusing buttons
- Complex landing page

AFTER:
- 1 primary search page
- 6 streamlined nav items
- 1 standard footer
- Clear button purposes
- Fast redirect to explore
```

---

## Detailed Task Breakdown

| Day | Task | Hours | Status |
|-----|------|-------|--------|
| 1 | Landing page removal | 2–3 | Pending |
| 2 | Navigation consolidation | 3–4 | Pending |
| 3 | Search consolidation | 3–4 | Pending |
| 4 | Button/CTA cleanup | 2–3 | Pending |
| 5 | Headers/footers standardization | 2–3 | Pending |
| 6–7 | Cross-browser testing | 4–5 | Pending |
| 8 | Performance optimization | 2–3 | Pending |
| 9 | Documentation update | 2–3 | Pending |
| 10 | Final QA | 3–4 | Pending |
| **Total** | | **24–32 hours** | |

---

## Files to Modify Summary

### Templates
- `base.html` — Navigation & footer
- `landing_page.html` — DELETE
- All search templates — Consolidate to one
- Place detail template — Remove duplicate nav buttons
- Dashboard template — Remove recommendations section

### Views
- `apps/core/views.py` — Update root view
- `apps/search/views.py` — Consolidate search views
- `apps/places/views.py` — Remove duplicate nav logic
- `apps/users/views.py` — Conditional staff nav

### URLs
- `mysite/urls.py` — Update root path
- `apps/search/urls.py` — Remove duplicate routes

### Static Files
- `static/css/` — Remove old landing page CSS
- `static/js/` — Remove unused JavaScript

---

## Risk Mitigation

**Risk: Breaking existing links**
- Solution: Check all internal links before deleting pages
- Test: Run full link checker

**Risk: Users bookmarked old URLs**
- Solution: Add redirects from old URLs to new ones
- Implement in Django: `redirect('/old-url/', '/new-url/')`

**Risk: Unintended side effects**
- Solution: Test full user journey (see Day 10)
- Keep git commits small and documented

---

## Success Criteria

✅ **All 13 redundant elements removed or consolidated**  
✅ **Navigation reduced from 10 to 6 items**  
✅ **One primary search entry point**  
✅ **Standard footer on all pages**  
✅ **No broken links or 404 errors**  
✅ **Full user journey tested and working**  
✅ **Performance optimized**  
✅ **Documentation updated**  

---

## After Cleanup: Ready for Phase 7A

Once complete, you'll have:
- ✅ Cleaner codebase
- ✅ Clearer user flows
- ✅ Reduced technical debt
- ✅ Solid foundation for Phase 7A
- ✅ 2–3 weeks saved in Phase 7 development

**Estimated Phase 7A timeline**: 2 weeks (vs 3 weeks without cleanup)

---

## Next Session

**When UI Cleanup is Complete**:
1. Verify all 13 items removed
2. Run final QA
3. Commit cleanup to git
4. Create tag: `v1.0-cleanup-complete`
5. Begin Phase 7A: Advanced Search Filters

See you in 1–2 weeks! 🚀
