---
name: phase7-features-plan
description: Phase 7 feature roadmap for ExploreAnywhere - Kabankalan Edition
type: project
---

# Phase 7 — Feature Expansion Plan

## Current Status (as of 2026-10-19)
- **Phase 6P**: Photo discovery system optimized (3–5x faster)
- **Discovery pipeline**: Kabankalan photos being collected from Wikimedia Commons
- **Architecture**: Stable Django app with users, places, itineraries, visits, rewards
- **Ready for**: New engagement features, user experience improvements

---

## Phase 7 Feature Categories

### Category A: User Engagement & Social (High Impact)

#### A1. Favorite Places / Wishlist
**Goal**: Let users save places they want to visit
- Add `favorites` many-to-many relationship on `Place` model
- Create favorite management views (add/remove)
- Show favorite count on place detail pages
- Add "Favorites" tab in user profile
- **Effort**: 2–3 hours | **Priority**: High
- **Why**: Low-cost engagement booster; encourages return visits

#### A2. Place Ratings & Reviews System (Lite)
**Goal**: User-submitted 1–5 star ratings with optional text
- Add `Rating` model with user, place, stars, timestamp
- Aggregate ratings on place cards (show avg stars)
- Prevent duplicate ratings per user
- Display top/recent reviews on place detail page
- **Effort**: 3–4 hours | **Priority**: High
- **Why**: Social proof drives discovery; already have reviews app, extend it

#### A3. User Following / Friend System
**Goal**: Users can follow other explorers and see their activity
- Add `Follow` relationship model
- Activity feed showing follows' recent visited places
- "Who visited this" sidebar on place detail
- User profile shows followers/following counts
- **Effort**: 4–5 hours | **Priority**: Medium
- **Why**: Engagement loop; encourages competition/sharing

#### A4. Activity Feed / Timeline
**Goal**: Personalized activity feed of user + friends' activities
- Aggregate: places visited, itineraries created, achievements unlocked
- Real-time or lazy-loaded feed view
- Filter by activity type (visit, itinerary, review, photo)
- **Effort**: 3–4 hours | **Priority**: Medium
- **Why**: Retention driver; gives users reason to return daily

---

### Category B: Gamification & Rewards (Medium Impact)

#### B1. Achievement Badges / Milestones
**Goal**: Unlock badges for place discovery milestones
- Badge types: "First 10 places", "All museums in Kabankalan", "Photo contributor", etc.
- Store unlocked badges per user
- Display on user profile
- Notify user on unlock
- **Effort**: 3 hours | **Priority**: Medium
- **Why**: Extends visits/rewards system; motivates exploration

#### B2. Leaderboards (City & Category)
**Goal**: Rank users by places visited, visits this week, etc.
- Global city leaderboard (most places visited)
- Category leaderboards (most cafes, most natural sites, etc.)
- Weekly/monthly snapshots
- **Effort**: 2–3 hours | **Priority**: Low
- **Why**: Optional; good for engagement but not essential

#### B3. Streak Tracking
**Goal**: Reward consistent daily/weekly exploration
- Track "visit streak" (consecutive days with at least 1 visit)
- Bonus rewards for extending streaks
- Display on user profile
- **Effort**: 2 hours | **Priority**: Low
- **Why**: Habit formation; nice-to-have

---

### Category C: Discovery & Search (High Impact)

#### C1. Advanced Search / Filtering
**Goal**: Find places by multiple criteria
- Filter by: hobby, rating, distance from user, has-reviews, has-photos
- Sort by: rating, distance, newest, most-visited
- Save search filters as "saved searches"
- **Effort**: 4–5 hours | **Priority**: High
- **Why**: Places database growing; users need better discovery

#### C2. Smart Recommendations
**Goal**: Suggest places based on user's past visits
- Collaborative filtering: "users who visited X also visited Y"
- Content-based: "similar to places you visited"
- Show on home page or dedicated "For You" page
- **Effort**: 5–6 hours | **Priority**: Medium
- **Why**: Drives engagement; reduces cold-start problem

#### C3. Location-Based Nearby Places
**Goal**: Show places near user's current location
- Real-time geolocation on explore map
- "Places near me" radius-based search
- Sort by distance
- **Effort**: 2–3 hours | **Priority**: Medium
- **Why**: Mobile-friendly feature; increases spontaneous visits

#### C4. Category Browsing
**Goal**: Browse places organized by hobby/category
- Category detail pages (e.g., "All Cafes in Kabankalan")
- Featured categories on home page
- Category-specific itineraries
- **Effort**: 2 hours | **Priority**: Low
- **Why**: Nice-to-have; complements search

---

### Category D: Itinerary & Planning (Medium Impact)

#### D1. Itinerary Sharing / Public Profiles
**Goal**: Share itineraries publicly, discover others' plans
- Toggle public/private on itineraries
- Public itinerary gallery
- Fork/remix others' itineraries
- View count on public itineraries
- **Effort**: 3 hours | **Priority**: Medium
- **Why**: Community contribution; social discovery

#### D2. Itinerary Templates
**Goal**: Pre-built itineraries for common visit patterns
- "First-time visitor" itinerary (must-see places)
- "Weekend escape" itinerary (3 top-rated places)
- "Foodie tour" itinerary (best restaurants)
- Users can clone and customize
- **Effort**: 2–3 hours | **Priority**: Medium
- **Why**: Reduces friction for new users

#### D3. Smart Itinerary Suggestions
**Goal**: AI-suggest places to add to user's itinerary
- Based on: nearby places, matching hobbies, ratings
- One-click add to itinerary
- **Effort**: 3–4 hours | **Priority**: Low
- **Why**: Nice-to-have; can be basic at first

---

### Category E: Content & Media (Medium Impact)

#### E1. User Photo Uploads (Lite)
**Goal**: Let users upload photos of places they visit
- Upload photo when logging a visit
- Photo moderation queue (volunteer review)
- Approved photos become "user-generated covers"
- Credit user on place page
- **Effort**: 4–5 hours | **Priority**: High
- **Why**: Phase 6P photos are static; user-generated adds recency

#### E2. Photo Gallery Enhancements
**Goal**: Improve display of place photos
- Carousel/lightbox on place detail
- Photo timeline (sort by date uploaded)
- "See all photos" page
- Most-upvoted photos featured first
- **Effort**: 2–3 hours | **Priority**: Medium
- **Why**: Photos drive engagement; worth showcasing well

#### E3. Description / Wiki-style Place Details
**Goal**: Crowdsourced place descriptions
- Allow users to contribute descriptions
- Version history / edit approval
- Flag inaccurate info
- **Effort**: 3–4 hours | **Priority**: Low
- **Why**: Scales content; but requires moderation

---

### Category F: Analytics & Insights (Low Impact)

#### F1. User Dashboard / Statistics
**Goal**: Show users their exploration metrics
- Places visited: count, breakdown by category
- Total rewards earned
- Favorite categories
- Progress toward achievements
- **Effort**: 2–3 hours | **Priority**: Low
- **Why**: Fun mirror; increases retention

#### F2. Admin Analytics Dashboard
**Goal**: Monitor app health and usage patterns
- Daily active users
- Most visited places (trending)
- Least visited places (recommendations)
- Review/photo contribution rates
- **Effort**: 3–4 hours | **Priority**: Low
- **Why**: Operational insights; not user-facing

---

## Recommended Phase 7 Roadmap

### Phase 7A (Weeks 1–2): Foundation
1. **A1 — Favorite Places** (quick win, high impact)
2. **E1 — User Photo Uploads** (complements Phase 6P photos)
3. **C1 — Advanced Search** (scales for growing place count)

**Rationale**: 
- Favorites & search are low-risk, high-impact
- User uploads leverage photo infrastructure already built
- Together = better discovery + user content

### Phase 7B (Weeks 3–4): Engagement Loop
1. **A2 — Ratings & Reviews** (extend existing reviews app)
2. **D1 — Itinerary Sharing** (community contribution)
3. **B1 — Achievement Badges** (gamification)

**Rationale**: 
- Builds on existing reviews infrastructure
- Encourages sharing and returning
- Badges reward milestones

### Phase 7C (Weeks 5–6): Social & Analytics
1. **A3 — User Following** (optional; community feature)
2. **C2 — Smart Recommendations** (engagement driver)
3. **F1 — User Dashboard** (retention metric)

**Rationale**: 
- Social features boost engagement
- Recommendations reduce exploration friction
- Dashboard shows progress to users

### Phase 7D (Future): Nice-to-Have
- C3 — Nearby places (mobile feature)
- D2 — Itinerary templates
- D3 — Smart suggestions
- E2 — Photo gallery UI
- A4 — Activity feed (complex)
- B2, B3 — Leaderboards & streaks

---

## Implementation Notes

### Database Schema Additions

```python
# Favorites
class Favorite(models.Model):
    user = ForeignKey(User)
    place = ForeignKey(Place)
    created_at = DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'place')

# Ratings (extend existing Review?)
class Rating(models.Model):
    user = ForeignKey(User)
    place = ForeignKey(Place)
    stars = IntegerField(1, 5)  # 1–5 stars
    created_at = DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'place')

# Follows
class Follow(models.Model):
    follower = ForeignKey(User, related_name='following')
    following = ForeignKey(User, related_name='followers')
    created_at = DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('follower', 'following')

# Badges
class Badge(models.Model):
    name = CharField(max_length=100)
    description = TextField()
    icon_url = URLField()

class UserBadge(models.Model):
    user = ForeignKey(User)
    badge = ForeignKey(Badge)
    unlocked_at = DateTimeField(auto_now_add=True)

# User Photo (for uploads)
class UserPhoto(models.Model):
    user = ForeignKey(User)
    place = ForeignKey(Place)
    image = ImageField()
    caption = TextField(blank=True)
    status = CharField(choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')])
    created_at = DateTimeField(auto_now_add=True)
```

### Frontend Priorities
- Favorites: Simple heart icon on place cards + favorites tab
- Search: Filter sidebar on explore page
- User photos: Upload modal on place detail page
- Ratings: Star display + review form on place detail

---

## Success Metrics

| Feature | Success Metric |
|---------|----------------|
| **Favorites** | >30% of users favorite ≥1 place |
| **Search** | >20% of discovery via filters |
| **User Photos** | >50 user photos/month (after 2 months) |
| **Ratings** | >100 ratings across places |
| **Following** | >10% of users follow ≥1 other user |
| **Badges** | >50% of active users unlock ≥1 badge |

---

## Timeline Estimate

- **Phase 7A (Foundation)**: 1–2 weeks (30 hours)
- **Phase 7B (Engagement)**: 1–2 weeks (25 hours)
- **Phase 7C (Social)**: 1–2 weeks (20 hours)
- **Phase 7D (Future)**: 1–4 weeks per feature (as time allows)

**Total for 7A+7B+7C: ~8 weeks (~75 developer hours)**

---

## Questions to Answer Before Starting

1. **Mobile first?** If yes, prioritize nearby places (C3) and simpler UI
2. **Content moderation capacity?** User uploads (E1) need review workflow
3. **Analytics backend?** If needed, add database for recommendations (C2)
4. **API for 3rd parties?** Consider REST endpoints for itinerary sharing (D1)
5. **Real-time features?** Activity feed (A4) benefits from websockets/polling

