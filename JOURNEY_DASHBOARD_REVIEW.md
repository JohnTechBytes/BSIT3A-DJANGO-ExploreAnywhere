---
name: journey-dashboard-review
description: Comprehensive review and cleanup plan for Journey Dashboard - Remove gamification, simplify design
type: project
---

# Journey Dashboard — UI/UX Review & Cleanup Plan

**Current Status**: The dashboard has heavy gamification (points, badges, rewards) and feels cluttered with 6+ metrics and redundant CTAs.

**User Goal**: See your saved places, trips, reviews, and visits at a glance. Quick access to your content.

---

## Current Issues Analysis

### 1. **Excessive Gamification**
**Problem**: The dashboard heavily emphasizes gamified features that don't serve the core goal.

**Current Gamification**:
- "Earned points" display (112 prominently shown)
- "Badges & Rewards" section with locked/unlocked achievements
- Visit points tied to "staff approval"
- Achievement system feels like a game, not a discovery tool

**Impact**:
- Users focus on points/badges instead of their actual content
- Adds cognitive load (what are points for? why do I need badges?)
- Feels juvenile for adults discovering places
- Doesn't align with the app's core purpose (discover Kabankalan)

**Remove These**:
- ❌ "Earned points" metric and display
- ❌ "Badges & Rewards" section entirely
- ❌ Points calculation logic (hide visit points)
- ❌ Achievement definitions and badges UI

---

### 2. **6 Metrics in the Hero (Cognitive Overload)**
**Problem**: The metrics row shows too many things at once, making it hard to scan.

**Current Metrics**:
```
[❤️ 2 Saved] [☰ 3 Plans] [⭐ 1 Reviews] [✓ 1 Approved] [⏱ 0 Pending] [◆ 100 Points]
```

**Impact**:
- Users don't know which metrics matter
- "Pending visits" and "Points" are noise
- Mobile: Everything wraps and becomes unreadable
- Too many clickable links (all 6 are links)

**Simplify To**:
```
[❤️ 2 Saved Places] [☰ 3 Trip Plans] [⭐ 1 Review] [✓ 1 Visited]
```

**Remove**:
- Pending visits (duplicate info, use the "My Visits" section instead)
- Points (part of gamification removal)

---

### 3. **Too Many Panels & Sections**
**Problem**: The dashboard has 6 major sections + a "Your Next Adventure" section + quick nav at bottom = 8 CTAs to different places.

**Current Layout**:
```
Hero + 6 metrics
├─ Saved Places
├─ My Itinerary Plans
├─ My Reviews
├─ My Visits
├─ Badges & Rewards ← REMOVE
└─ Your Next Adventure ← SIMPLIFY

+ Quick nav at bottom (3 more links)
```

**Impact**:
- Information overload
- Users don't know where to start
- Redundant CTAs (save/plan/review links appear in 3 places)
- Long page with lots of scrolling

**Simplify To**:
```
Hero + 4 metrics (saved, plans, reviews, visited)
├─ Saved Places
├─ My Itinerary Plans
├─ My Reviews
└─ My Visits

(Remove badges, remove "next adventure", remove bottom quick nav)
```

---

### 4. **Redundant Navigation & CTAs**
**Problem**: Users see the same actions repeated multiple times.

**Current Redundancy**:
```
Hero: "Explore Places" + "Plan a Trip"
Saved Places card: "Find a place" + "My Saved Places" link + link in header
Itineraries card: "Create an itinerary" + "+ New Itinerary" + link in header
Bottom quick nav: "Discover destinations" + "Build an itinerary" + "Check visit status"
```

**Impact**:
- Users confused about which CTA to use
- Too many buttons (15+ CTAs on one page)
- Visual noise

**Solution**: Keep only the most direct CTAs in each section. Remove bottom quick nav.

---

### 5. **Unclear Card Hierarchy**
**Problem**: All 6 panels look identical, making it hard to scan.

**Current Structure**:
- Saved Places (left panel)
- Plans (right panel)
- Reviews (left panel)
- Visits (right panel)
- Badges (spans both) ← Not needed
- Next Adventure (spans both) ← Not needed

**Impact**:
- No visual priority
- All equal weight, but some are more important
- Desktop: 2-column layout breaks on mobile
- Lots of wasted vertical space

---

### 6. **"Your Next Adventure" is Vague**
**Problem**: A full section with 3 buttons that could easily be in the hero or removed.

**Current**:
```
Your Next Adventure
├─ Find recommendations
├─ Saved places
└─ Your plans
```

**Impact**:
- Redundant (already have these links above)
- Takes up space
- Doesn't tell users *what* to do next
- Feels like filler

**Solution**: Remove entirely. Users already know how to navigate.

---

### 7. **Privacy/Explanatory Text is Clutter**
**Problem**: Multiple paragraphs explain what data is shown and how gamification works.

**Current Text**:
- "Only your own Kabankalan records are displayed."
- "Only staff-approved check-ins count toward points and badges." (in empty state)
- "Viewing a place... does not verify a physical visit." (in My Visits)
- "Rewards are calculated from approved records..." (in Badges)
- "ExploreAnywhere is focused exclusively on Kabankalan City..." (at bottom)

**Impact**:
- Too many explanations = users don't read any
- Clutters the interface
- Feels defensive (like explaining why gamification isn't cheating)

**Solution**: Remove most of this. Keep only essential info.

---

## Recommended Improvements

### **Priority 1: Remove Gamification (High Impact, Quick Win)**

**Remove Entirely**:
- ❌ 6th metric: "Points" display
- ❌ "Badges & Rewards" section (whole thing)
- ❌ "Pending visits" metric (not a key insight)

**Result**: Cleaner, less cluttered, focused on actual content.

---

### **Priority 2: Simplify Metrics (Quick Win)**

**Before** (6 metrics):
```
[❤️ 2 Saved] [☰ 3 Plans] [⭐ 1 Reviews] [✓ 1 Approved] [⏱ 0 Pending] [◆ 100 Points]
```

**After** (4 metrics):
```
[❤️ 2 Saved Places] [☰ 3 Trip Plans] [⭐ 1 Review] [✓ 1 Visited]
```

**Benefits**:
- Easier to scan
- Mobile-friendly (2 rows instead of 6 columns that wrap)
- All metrics are meaningful
- Reduced visual weight

---

### **Priority 3: Remove Redundant Sections (Quick Win)**

**Remove**:
- ❌ "Your Next Adventure" section (users already know how to navigate)
- ❌ Bottom quick nav (3 redundant links)

**Result**: Shorter page, cleaner focus.

---

### **Priority 4: Clean Up Empty States & Privacy Text (Polish)**

**Remove or Simplify**:
- ❌ Long explanations about staff approval and gamification
- ✅ Keep: "Saved Places" empty state (helps first-time users)
- ✅ Keep: "My Itineraries" empty state (encourages action)
- ✅ Keep: "My Visits" empty state (explains what a visit is)
- ❌ Remove: Privacy text about gamification calculation

**Result**: Less defensive, more welcoming.

---

### **Priority 5: Improve Card Layout (Polish)**

**Before**: All 6 panels in a 2-column grid, looks uniform.

**After**: 
- Keep 4 panels (saved, plans, reviews, visits)
- Remove badges/rewards + next adventure
- Maintain 2-column layout on desktop
- Stack on mobile (simpler)

**Benefits**:
- Cleaner visual hierarchy
- Easier to navigate
- Less scrolling

---

## Before & After Comparison

### **BEFORE (Current)**
```
┌─────────────────────────────────────────┐
│ My Kabankalan Journey                   │
│ [Explore Places] [Plan a Trip]          │
└─────────────────────────────────────────┘

Your journey at a glance
[❤️ 2] [☰ 3] [⭐ 1] [✓ 1] [⏱ 0] [◆ 100]   ← 6 metrics, points visible
         ↑ Pending/Points are noise

Keep your adventure organized
┌─ Saved Places ──┬─ Trip Plans ──┐
│ Coffee & Talk   │ Weekend Trip  │
│ [Find place]    │ [Create] [+]  │
└─────────────────┴───────────────┘

┌─ Reviews ───────┬─ Visits ──────┐
│ CPSU Museum: 5⭐│ Amyan (Appr.) │
│ [Explore]       │ [Check status]│
└─────────────────┴───────────────┘

┌─ Badges & Rewards ────────────────────┐  ← REMOVE
│ 100 points (stuff about achievements) │
│ [Earned] [Locked] [Locked]            │
└───────────────────────────────────────┘

┌─ Your Next Adventure ─────────────────┐  ← REMOVE
│ [Recommendations] [Saved] [Plans]     │
└───────────────────────────────────────┘

[Discover] [Build] [Check visit status]  ← REMOVE
```

### **AFTER (Cleaned Up)**
```
┌─────────────────────────────────────────┐
│ My Kabankalan Journey                   │
│ [Explore Places] [Plan a Trip]          │
└─────────────────────────────────────────┘

Your journey at a glance
[❤️ 2 Saved] [☰ 3 Plans] [⭐ 1 Review] [✓ 1 Visited]  ← 4 clear metrics

┌─ Saved Places ──┬─ Trip Plans ──┐
│ Coffee & Talk   │ Weekend Trip  │
│ Kabankalan      │ 2 stops       │
│ [My Saved] →    │ [My Plans] →  │
└─────────────────┴───────────────┘

┌─ My Reviews ────┬─ My Visits ───┐
│ CPSU Museum: 5⭐│ Amyan         │
│ "Great place"   │ Oct 18, 2026  │
│ [My Reviews] →  │ Approved ✓    │
│                 │ [My Visits] → │
└─────────────────┴───────────────┘
```

---

## Implementation Plan

### **Phase 1: Remove Gamification (1 hour)**
1. ✅ Hide "Points" metric from metrics row
2. ✅ Remove "Pending visits" metric
3. ✅ Remove "Badges & Rewards" section entirely
4. ✅ Remove gamification explanatory text

**Result**: Cleaner, less cluttered dashboard.

---

### **Phase 2: Simplify Layout (1 hour)**
1. ✅ Update CSS for 4-column metrics grid (mobile: 2 columns)
2. ✅ Remove "Your Next Adventure" section
3. ✅ Remove bottom quick nav
4. ✅ Clean up empty state messaging

**Result**: Shorter page, clearer focus.

---

### **Phase 3: Polish & Mobile (30 min)**
1. ✅ Test responsive layout on mobile
2. ✅ Verify all CTAs work
3. ✅ Clean up spacing and typography
4. ✅ Ensure accessibility (keyboard nav, contrast)

**Result**: Production-ready, clean dashboard.

---

## Files to Modify

1. **`templates/places/journey_dashboard.html`** (~220 lines)
   - Remove badges section (lines 190–201)
   - Remove "Your Next Adventure" section (lines 203–212)
   - Remove quick nav section (lines 214–218)
   - Remove/simplify privacy text
   - Update metrics row: remove pending + points

2. **CSS in journey_dashboard.html**
   - Update `.ea4b-metrics` grid: `repeat(6, ...)` → `repeat(4, ...)`
   - Update mobile breakpoints for 4-column layout
   - Remove unused classes (`.ea4b-badges`, `.ea4b-rewards`, `.ea4b-quick`, etc.)

---

## Expected Outcomes

### **Before Cleanup**
- 6 metrics + 6 sections + gamification = 220 lines, feels overwhelming
- Points/badges distract from core content
- Too many CTAs (15+)
- Doesn't work well on mobile

### **After Cleanup**
- 4 metrics + 4 sections = ~150 lines, clean and focused
- No gamification, focus on user content
- Clear CTAs in each section
- Mobile-friendly and scannable

---

## Metrics

✅ **Page length**: Reduce from 220 lines to ~150 lines  
✅ **Visual elements**: 6 panels → 4 panels  
✅ **Metrics displayed**: 6 → 4  
✅ **CTAs**: 15+ → ~8 (one per section + hero)  
✅ **Gamification elements**: Many → 0  

---

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **1** | 1 hr | Remove gamification, badges, pending visits |
| **2** | 1 hr | Remove redundant sections, simplify layout |
| **3** | 30 min | Polish, mobile testing, accessibility |
| **Total** | **2.5 hrs** | Complete dashboard redesign |

---

## Ready to Build?

Ready to start Phase 1 (Remove Gamification) now, or test the Explore Places redesign first?

