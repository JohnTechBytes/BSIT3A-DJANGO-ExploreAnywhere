---
name: why-remove-landing-page
description: Rationale for removing the landing page during UI cleanup
type: project
---

# Why Remove the Landing Page?

## The Problem (From Your UI Review)

Looking at Screenshot #1 (your landing page), we identified these issues:

### 1. **Redundant with Explore Places Page**
```
Landing page shows:
- "Discover what you love" (categories grid)
- Search bar
- "Explore Subscription" button
- Call-to-action cards

But ALSO exists:
- Explore Places page (Screenshot #2) — Does the SAME thing
- Discover Kabankalan page (Screenshots #9-10) — Does the SAME thing

Result: THREE pages doing the same job = confusion + maintenance burden
```

### 2. **Confusing User Journey**
```
Current flow:
User lands on / (landing page)
  → Sees "Explore Subscription" button (unclear what it is)
  → Sees "Become a Partner" card (not relevant to user)
  → Sees multiple CTA buttons (which one to click?)
  → Finally clicks "Explore" and goes to /explore-places/

Cleaner flow:
User lands on / (REDIRECTS to /explore-places/)
  → Immediately sees places to explore
  → Clear goal: discover places
  → Fewer decisions = better UX
```

### 3. **Maintenance & Development Cost**
```
Landing page requires:
- Separate template file (landing.html)
- Separate view (landing_page view)
- Separate CSS/styling
- Separate JavaScript
- Separate testing
- Documentation

Removing it:
- Eliminates redundancy
- Reduces code to maintain
- Fewer places for bugs
- Faster development
```

### 4. **"Explore Subscription" Not Implemented**
```
Screenshot #1 shows: "Explore Subscription" button
But searching your code: NOT FOUND ANYWHERE

This is either:
- Dead code (never implemented)
- A planned feature (not ready yet)

Recommendation: Remove the button, not add more UI debt
```

### 5. **"Become a Partner" Out of Scope**
```
Your app is: Place discovery for users
Not: Business/partner management system

"Become a Partner" card:
- Doesn't fit user goals
- Requires separate backend (partner system)
- Adds complexity
- Better as separate page (if needed later)
```

---

## What We're NOT Losing

### You Keep:
- ✅ All place discovery functionality
- ✅ All search/filter capabilities
- ✅ Explore Places page (better UI anyway)
- ✅ All user features (itineraries, visits, reviews)
- ✅ Dashboard and badges

### You Only Remove:
- ❌ Landing page (redundant)
- ❌ "Explore Subscription" button (not implemented)
- ❌ "Become a Partner" card (out of scope)
- ❌ "My Dimension" button (unclear purpose)

---

## The Benefits of Removing It

### 1. **Faster Onboarding for Users**
```
Before: / → landing page (confusing)
After:  / → /explore-places/ (direct to action)

Result: Users reach real content 1 click faster
```

### 2. **Cleaner Codebase**
```
Fewer files = easier to understand
Fewer views = faster to test
Fewer templates = less CSS to maintain
```

### 3. **Easier Phase 7 Development**
```
You won't be asking:
"Should this Phase 7 feature go on landing or explore page?"

Clear answer:
"There's only ONE explore page. Put it there."
```

### 4. **Better Mobile Experience**
```
Landing pages are usually cluttered
Mobile users don't want landing pages
They want to GET TO CONTENT immediately

After redirect: Users see /explore-places/ on mobile
Clean, focused, works great on small screens
```

### 5. **Metrics & Analytics**
```
Before: Users land on /
  → Get confused by multiple CTAs
  → Leave or click wrong button
  → Bounce rate high

After: Users land on / → redirect to /explore-places/
  → See places immediately
  → More likely to engage
  → Analytics clearer (one entry point)
```

---

## Comparison: Landing Page vs. Direct to Explore

### **With Landing Page**
```
User visits site
  ↓
Sees confusing hero with 5 options
  ↓
Clicks "Explore Places" button
  ↓
Arrives at /explore-places/
  ↓
FINALLY sees real content (wasted 2 clicks)
```

### **Without Landing Page (Clean)**
```
User visits site
  ↓
Automatically redirects to /explore-places/
  ↓
IMMEDIATELY sees real content (1 click saved)
```

---

## When Would You KEEP a Landing Page?

Landing pages ARE useful if:
- ✅ You're explaining WHAT your product is (SaaS companies)
- ✅ You need marketing messaging (startup pitch)
- ✅ You have multiple user types (different entry points)
- ✅ You need pricing/plans page

**Your app**: ExploreAnywhere is discovery-focused
- Users know what it is (find places)
- No pricing page needed
- One main user type
- Goal: Get users exploring ASAP

**Verdict**: Landing page is unnecessary overhead

---

## After Removal: Simpler App

### Files Deleted
```
apps/core/templates/landing.html        ← Remove
apps/core/views.py (landing_page view)  ← Remove
```

### Files Updated
```
mysite/urls.py                          ← Add redirect
```

### Result
```
- 1 fewer template to maintain
- 1 fewer view to test
- 1 clearer user journey
- 3 redundant pages → 1 primary explore page
```

---

## Could We Keep It?

**Sure, but at what cost?**

```
Keeping landing page:
- Adds ~200 lines of code
- Requires testing
- Adds confusion in UI
- Slows onboarding
- Creates "which explore page?" question

For what benefit?
- Users can see a pretty hero section?
- But they see the same info on /explore-places/ anyway

ROI: Negative. Better to remove.
```

---

## Real-World Example

### Similar Apps & How They Handle It

**Airbnb** (discovery-focused like you):
- Landing: Shows search bar immediately
- Goal: Get you searching for places

**Google Maps** (discovery-focused like you):
- Landing: Search bar, show nearby
- Goal: Get you exploring places

**Your app** (discovery-focused):
- Current: Landing page with confusing CTAs
- Better: Direct to /explore-places/ with search/filter
- Goal: Get you discovering places

---

## Bottom Line

### Remove Landing Page Because:

1. ✅ **Redundant** — Same as Explore Places page
2. ✅ **Confusing** — Multiple CTAs don't help
3. ✅ **Unmaintained code** — "Explore Subscription" not implemented
4. ✅ **Slower UX** — Extra clicks to reach content
5. ✅ **Technical debt** — More code to maintain

### What You Get Back:
- Cleaner codebase
- Faster user onboarding
- Fewer maintenance headaches
- Ready for Phase 7 (no "where should this go?" questions)

---

## Decision: Keep or Remove?

### Option A: Remove (Recommended) ✅
- Cleaner app
- Faster development
- Better UX
- Less maintenance

### Option B: Keep It (Not Recommended)
- Keep current redundancy
- Slower Phase 7 development
- More UI confusion
- More code to maintain

**Our Recommendation**: **REMOVE IT** 🎯

The landing page adds complexity without value. Users just want to discover places. Let them do that immediately.

---

## Next Steps

1. **Understand the why** ← You just did this ✓
2. **Execute Day 1** — Remove landing page
3. **See the improvement** — Cleaner, faster app
4. **Move to Day 2** — Continue cleanup

Ready? Let's go! 🚀
