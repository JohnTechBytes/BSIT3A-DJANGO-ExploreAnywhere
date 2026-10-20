---
name: explore-places-ui-review
description: Comprehensive UI/UX review and improvement plan for the Explore Places page
type: project
---

# Explore Places Page — UI/UX Review & Improvement Plan

**Current Status**: The page is functional but has UX friction points and visual confusion that slow down discovery.

**User Goal**: Find places to visit quickly based on interests, location, and categories.

---

## Current Issues Analysis

### 1. **Cognitive Overload in Discovery Tools**
**Problem**: The search/filter section has 5 different inputs (search, category, hobby, sort, buttons) crammed into one horizontal form. On mobile, this becomes confusing.

**Current Layout**:
```
[Search input (2 cols)] [Category ▼] [Hobby ▼] [Sort ▼] [Show places] [Clear]
```

**Impact**: 
- Users don't know where to start
- Unclear which filters are optional vs required
- Mobile: everything wraps awkwardly
- "Show places" button is unclear (why click if results auto-load?)

---

### 2. **Redundant Navigation Modes**
**Problem**: Three navigation tabs (All Places, Near Me, Map View) but the actual view toggle is *below* the filters, not above.

**Current Flow**:
1. User sees "Discover Kabankalan" header
2. Discovery mode tabs (All Places | Near Me | Map View)
3. Search/filter tools
4. Results
5. Another view toggle (List/Carousel | Map View | Change Search)

**Impact**: 
- Two places to switch views is confusing
- Users might switch to Map View in the tabs, then see the results toggle below and not understand they're related
- "Change Search" link is obscure

---

### 3. **Unclear Relevance Scoring**
**Problem**: The relevance badge shows "25% Personalized Relevance" or "Not scored yet" but the explanation is a long paragraph below the search tools that most users won't read.

**Current Text**:
> "Finding a destination with search or filters does not mean it matches your personal hobbies. Personalized relevance is calculated using selected hobbies and available ratings, normalized over available signals. A lower percentage is not a destination-quality rating. No GPS distance is scored. Gray map markers mean there is not enough personalization information; colored map markers use the displayed score."

**Impact**:
- Users see "25%" and think "why only 25%? Is this place bad?"
- The scoring logic is invisible
- No tooltip or context on the badge itself
- Mobile users definitely don't read the paragraph

---

### 4. **Information Density in Cards**
**Problem**: Each place card shows:
- Image
- Category badge
- Title
- Photo attribution (3-4 lines!)
- Search relevance (if applicable)
- Personalized relevance badge
- Match reason (2-3 lines)
- Location
- Description
- 2 footer buttons

**Impact**:
- Users scroll through lots of text before reaching the description
- Card feels cramped
- On mobile, one card takes up 2-3 viewport heights
- Visual hierarchy is unclear

---

### 5. **Confusing Filter Chips**
**Problem**: Active filters show as chips with remove (✕) links, but there's also a "Clear all" link and a separate "Clear filters / Browse all" button in the form.

**Current State**:
```
[Active search and display settings]
[Coffee ✕] [Hiking ✕] [Recent ✕] ... [Clear all]
```

**And also**:
```
[Show places button] [Clear filters / Browse all link]
```

**Impact**:
- Three ways to clear filters (chip ✕, "Clear all", "Clear filters / Browse all")
- Users don't know which one to use
- Redundant UI

---

### 6. **Empty State & Onboarding**
**Problem**: When there are no places or no hobby selected, the page shows a generic message:
> "Destinations for Kabankalan are still being reviewed"

**Current Logic**:
- If search/category/hobby filters → "No matching places found"
- Else → "No published places yet"

**Impact**:
- First-time users see 9 published places but don't know how to find them
- No guidance on how to use the hobby filter
- No suggestion to "Try a hobby" or "Browse all places"

---

### 7. **Pagination UX**
**Problem**: Pagination controls show "Page 2 of 3" but users scroll through all 12 cards before realizing there's pagination at the bottom.

**Impact**:
- Users don't realize there are more results
- Pagination should be sticky or cards should load on scroll

---

## Recommended Improvements

### **Priority 1: Simplify Discovery Tools (Quick Win)**

**Change**: Consolidate and clarify the search form.

**Before**:
```
[Search (2 cols)] [Category] [Hobby] [Sort] [Show places] [Clear filters]
```

**After**:
```
[Search query - full width, prominent]

[Category ▼] [Hobby ▼]     [Sort ▼]

[Show places]
```

**Benefits**:
- Search is the hero (full width)
- Filters are secondary (one row)
- Sort is visible
- Clear action hierarchy
- Mobile: search → filters → button naturally flows

---

### **Priority 2: Unify View Controls (Reduce Confusion)**

**Change**: Remove the top navigation tabs (All Places | Near Me | Map View) and put view controls directly above results.

**New Layout**:
```
Header + Filters
↓
[List] [Map]  [Sort: Recommended ▼]
↓
Results
```

**Benefits**:
- One place to switch views
- Sort is always visible
- View switcher is right above results (matches intent)
- Cleaner header

---

### **Priority 3: Clarify Relevance Scoring (UX Clarity)**

**Change**: Add a tooltip/info icon to the relevance badge, show the score reason inline.

**Before**:
```
Card:
25% Personalized Relevance
Matching selected hobbies: Hiking, Photography.
```

**After**:
```
Card:
🎯 25% Match (ℹ️ tooltip: "Based on your selected hobbies")
↳ Matches: Hiking, Photography
```

**Benefits**:
- Score is immediately explained
- Users understand why a place scores 25%
- Less text, more clarity
- Tooltip reduces cognitive load

---

### **Priority 4: Optimize Card Density (Faster Scanning)**

**Change**: Reduce text, prioritize discovery speed.

**Before**:
```
[Image]
Category
Title
Photo attribution (3 lines)
Search relevance
Personalized relevance badge
Match reason
Location
Description
[View Details] [Directions]
```

**After**:
```
[Image]
Category  |  🎯 25% Match
Title
Quick description (1 line max)
Location
[View Details] [Map]
```

**Benefits**:
- Card height reduced by 40%
- Users see 3-4 cards per scroll instead of 1-2
- Faster scanning
- Photo attribution moves to detail page

---

### **Priority 5: Single Filter Reset (Remove Redundancy)**

**Change**: Keep only "Clear filters / Browse all" button, remove chip-by-chip removal.

**Before**:
```
[Coffee ✕] [Hiking ✕] ... [Clear all]
+ separate [Clear filters / Browse all] button
```

**After**:
```
Active filters: Coffee, Hiking, Recent
[Clear all]
```

**Benefits**:
- One clear way to reset
- Less UI clutter
- Cleaner form

---

### **Priority 6: Smart Empty State (Better Onboarding)**

**Change**: When no hobby is selected, show guidance instead of empty state.

**Before**:
> "No published places yet"

**After**:
```
🎯 Get personalized recommendations
Select a hobby above to see places that match your interests.

Popular: Hiking • Café • Photography • Basketball

[Browse All →]
```

**Benefits**:
- Teaches users how to use hobbies
- Shows popular options
- Clear next step
- Reduces friction

---

### **Priority 7: Sticky Results Header (Better Navigation)**

**Change**: Keep the view toggle (List/Map) sticky at the top when scrolling through results.

**Current**: User scrolls past header, view toggle disappears.
**After**: Sticky header shows "Results" + [List/Map] + pagination indicator.

**Benefits**:
- Users can switch views without scrolling back up
- Pagination is always visible
- Better for long result lists

---

## Implementation Plan

### **Phase 1: Quick Wins (2-3 hours)**
1. ✅ Consolidate search form (Priority 1)
2. ✅ Unify view controls (Priority 2)
3. ✅ Remove redundant filter UI (Priority 5)

**Result**: Cleaner, less confusing interface.

---

### **Phase 2: Clarity Improvements (3-4 hours)**
1. ✅ Add relevance score tooltip (Priority 3)
2. ✅ Optimize card layout (Priority 4)
3. ✅ Improve empty state (Priority 6)

**Result**: Users understand scoring, faster scanning.

---

### **Phase 3: Navigation Polish (2 hours)**
1. ✅ Make results header sticky (Priority 7)
2. ✅ Add pagination indicator
3. ✅ Test on mobile

**Result**: Smooth navigation, no lost context.

---

## Mockup: After Improvements

```
╔════════════════════════════════════════════════════════════╗
║ ExploreAnywhere | Home | Explore Places | ...             ║
╚════════════════════════════════════════════════════════════╝

┌─ EXPLOREANYWHERE · KABANKALAN ONLY ─────────────────────┐
│                                                           │
│ Discover Kabankalan                                       │
│ Find verified destinations and businesses in Kabankalan. │
│                                                           │
└─────────────────────────────────────────────────────────┘

┌─ BROWSE ────────────────────────────────────────────────┐
│ [All Places] [Near Me] [Map View]                        │
└─────────────────────────────────────────────────────────┘

┌─ SEARCH & FILTER ───────────────────────────────────────┐
│ [🔍 Search "coffee shops" or "hiking trails"          ] │
│                                                           │
│ [Category: All ▼]  [Hobby: All ▼]  [Sort: Best ▼]      │
│                                                           │
│ Active filters: Coffee, Hiking  [Clear all]             │
└─────────────────────────────────────────────────────────┘

9 Places Found | [List] [Map]

🎯 Personalized matching explained
(ℹ️ tooltip available)

┌─ RESULTS ──────────────────────────────────────────────┐
│                                                          │
│ ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│ │[Image]     │  │[Image]     │  │[Image]     │         │
│ │Mountain    │  │Café        │  │Museum      │         │
│ │25% Match   │  │Not scored  │  │80% Match   │         │
│ │Amyan Hill  │  │Coffee &    │  │CPSU Museum │         │
│ │A scenic    │  │Talk        │  │Learn about │         │
│ │peak near.. │  │Cozy spot.. │  │local..     │         │
│ │📍 Kabanka..│  │📍 Kabanka..│  │📍 Kabanka..│         │
│ │[Details] →│  │[Details] →│  │[Details] →│         │
│ └────────────┘  └────────────┘  └────────────┘         │
│                                                          │
└─────────────────────────────────────────────────────────┘

                Page 1 of 2 → Next
```

---

## Files to Modify

1. **`templates/places/attraction_carousel.html`**
   - Restructure `.ea-discovery-tools` form layout
   - Simplify `.ea-match-badge` with tooltip
   - Reduce card text density
   - Make results header sticky
   - Improve empty state

2. **`apps/places/views.py`** (minimal changes)
   - Pass additional context for empty state
   - No logic changes needed

3. **Static CSS** (new additions)
   - Tooltip styles
   - Sticky header
   - Simplified card layout

---

## Expected Outcomes

### Before Cleanup
- 1590 lines of template HTML
- Complex card layouts with multiple badge types
- Confusing navigation modes
- High cognitive load

### After Cleanup
- ~1200-1300 lines (clearer, smaller)
- Simplified card with clear hierarchy
- Single view switcher
- Reduced cognitive load
- Better mobile experience
- Faster user onboarding

---

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **1** | 2-3 hrs  | Consolidate form, unify views, remove redundancy |
| **2** | 3-4 hrs  | Add tooltips, optimize cards, improve empty state |
| **3** | 2 hrs    | Sticky headers, pagination, mobile testing |
| **Total** | **7-9 hrs** | Complete Explore Places redesign |

---

## Success Metrics

✅ **Before**: Users scroll through confusing filters and dense cards  
✅ **After**: Users find places in <30 seconds, understand scoring, enjoy browsing

- Page load time: Same or faster
- Cards per viewport: 3-4 (vs current 1-2)
- Bounce rate on empty results: Decrease with better guidance
- Time to discover first place: Reduced

---

## Ready to Build?

Ready to start Phase 1 (Quick Wins) now?

