---
name: ui-cleanup-checkpoint-system
description: Save progress during UI cleanup sprint - pause anytime, resume later
type: project
---

# UI Cleanup Sprint — Checkpoint System
**Purpose**: Build incrementally, pause anytime, resume seamlessly

---

## How to Use Checkpoints

### Before Starting Work
1. Create a new git branch: `git checkout -b cleanup/day-1-landing-page`
2. Pull the latest code: `git pull origin main`
3. Work on ONE day's tasks only

### During Work
- Check off tasks as you complete them
- Test as you go (don't wait until end)
- Keep edits small and focused

### When You Get Tired / Need to Pause
1. **Commit your work**:
   ```bash
   git add .
   git commit -m "WIP: Day 1 - Landing page removal (checkpoint)"
   ```

2. **Update checkpoint log** (create this file):
   - What you completed
   - What you started but didn't finish
   - Next steps for tomorrow

3. **Push to backup branch**:
   ```bash
   git push origin cleanup/day-1-landing-page
   ```

### When You Resume Later
1. Check the checkpoint log
2. Switch to the cleanup branch: `git checkout cleanup/day-1-landing-page`
3. Pick up where you left off
4. Continue with remaining tasks

---

## Checkpoint Log Template

Create a file: `CLEANUP_CHECKPOINT.md`

```markdown
# UI Cleanup Progress Log

## Current Session: [DATE & TIME]

### Completed Tasks
- [x] Task 1
- [x] Task 2

### In Progress
- [ ] Task 3 (started, 50% done)
  - Status: [describe what's done]
  - Next: [what needs to be done next]

### Not Started
- [ ] Task 4
- [ ] Task 5

### Blockers / Issues
- [list any problems encountered]

### Time Spent
- Started: [time]
- Ended: [time]
- Total: [hours]

### Notes for Next Session
- Remember to [important thing]
- Watch out for [potential issue]
- Before resuming, [setup needed]
```

---

## Sprint Breakdown (Pause-Friendly)

### Day 1: Landing Page Removal (2–3 hours)
**Can stop after**: Any of these subtasks
```
1. Delete landing_page.html
2. Update mysite/urls.py
3. Update views
4. Test redirect
```

**Checkpoint file**: `CLEANUP_DAY1_CHECKPOINT.md`

---

### Day 2: Navigation Consolidation (3–4 hours)
**Can stop after**: Any of these subtasks
```
1. Remove "Saved Places" button from place detail
2. Remove "My Journey" button from place detail
3. Move "Staff Dashboard" to admin nav
4. Update base.html navigation
5. Test navigation works
```

**Checkpoint file**: `CLEANUP_DAY2_CHECKPOINT.md`

---

### Day 3: Search Consolidation (3–4 hours)
**Can stop after**: Any of these subtasks
```
1. Identify which search page to keep
2. Delete duplicate search pages
3. Update URL routing
4. Test search entry points
```

**Checkpoint file**: `CLEANUP_DAY3_CHECKPOINT.md`

---

### Day 4: Button/CTA Cleanup (2–3 hours)
**Can stop after**: Any of these subtasks
```
1. Clarify "Report a Visit" button
2. Remove "Your Next Adventure" section
3. Fix "Half-Verified" badges
4. Standardize button text
5. Test all buttons
```

**Checkpoint file**: `CLEANUP_DAY4_CHECKPOINT.md`

---

### Day 5: Headers/Footers (2–3 hours)
**Can stop after**: Any of these subtasks
```
1. Define standard footer
2. Update base.html footer
3. Add breadcrumbs to pages
4. Test footer on all pages
```

**Checkpoint file**: `CLEANUP_DAY5_CHECKPOINT.md`

---

### Days 6–10: Testing & Polish (13–17 hours)
**Can stop after**: Each browser/device tested

---

## Git Strategy for Pausing/Resuming

### Session 1: Day 1 Morning
```bash
git checkout -b cleanup/sprint
# Do Day 1 tasks
git add .
git commit -m "Day 1: Remove landing page"
git push origin cleanup/sprint
```

### Session 2: Day 1 Afternoon (Resume)
```bash
git checkout cleanup/sprint
git pull origin cleanup/sprint
# Continue Day 1 or start Day 2
git add .
git commit -m "Day 1: Complete - redirect verified"
git push origin cleanup/sprint
```

### Session 3: Day 2 (Next Day)
```bash
git checkout cleanup/sprint
git pull origin cleanup/sprint
# Do Day 2 tasks
git add .
git commit -m "Day 2: Consolidate navigation"
git push origin cleanup/sprint
```

### After Full Completion
```bash
git checkout main
git merge cleanup/sprint
git tag v1.0-cleanup-complete
git push origin main --tags
```

---

## Tracking Progress

### Quick Progress Checklist
Update this as you work:

```
WEEK 1 PROGRESS
[ ] Day 1 — Landing page removal
[ ] Day 2 — Navigation consolidation  
[ ] Day 3 — Search consolidation
[ ] Day 4 — Button/CTA cleanup
[ ] Day 5 — Headers/footers

WEEK 2 PROGRESS
[ ] Days 6–7 — Cross-browser testing
[ ] Day 8 — Performance check
[ ] Day 9 — Documentation update
[ ] Day 10 — Final QA
[ ] COMPLETE — Merge to main, tag v1.0
```

---

## Time Estimation

**If you work 2 hours per day**:
- Week 1: Mon–Fri (10 hours total)
- Week 2: Mon–Fri (10 hours total)
- **Total: 2 weeks** ✓

**If you work 4 hours per day**:
- Week 1: Mon–Wed (12 hours, finish Day 5)
- Week 2: Thu–Fri (12 hours, finish all)
- **Total: 1 week** ✓

**If you work in short bursts**:
- 1 hour per day = 24–32 days (do one sub-task per session)
- 30 min per day = 50+ days (micro-work, still progresses)

---

## Session Template

Save this as `SESSION_TEMPLATE.md` and copy it for each session:

```markdown
# UI Cleanup Session — [DATE]

## Start Time
[time started]

## Planned Tasks (Today)
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

## Work Log
### Task 1: [name]
- Status: [in progress / completed]
- Time: [start] – [end]
- Notes: [what went well, what was tricky]

### Task 2: [name]
- Status: [in progress / completed]
- Time: [start] – [end]
- Notes: [...]

## Completed Today
[list what got done]

## Blockers / Issues
[anything that stopped you]

## Next Session Plan
- Start with: [specific task]
- Remember to: [important setup]
- Estimated time: [hours]

## End Time
[time ended]

## Total Time Spent
[hours]
```

---

## Emergency Pause

**If you need to stop urgently** (mid-task, mid-day):

1. **Commit what you have** (even if broken):
   ```bash
   git add .
   git commit -m "PAUSE: [Day X] - [task] incomplete, see notes"
   git push origin cleanup/sprint
   ```

2. **Leave detailed notes** in checkpoint file:
   - Exactly where you stopped
   - What's broken (if anything)
   - How to resume

3. **Don't worry about breakage** — You can always:
   ```bash
   git checkout main  # Go back to working version
   git checkout cleanup/sprint  # Resume cleanup branch later
   ```

---

## Resuming After Long Break

If you pause for a week or more:

1. **Check checkpoint log** — Understand where you left off
2. **Test the current state**:
   ```bash
   git checkout cleanup/sprint
   python manage.py runserver
   # Visit localhost:8000 and verify things work
   ```
3. **Re-read the day's tasks** — Jog your memory
4. **Continue from checkpoint** — Pick up where you left off

---

## Progress Tracking Tips

### Keep a simple log on your desk
```
Week 1:
✓ Mon: Day 1 complete (2 hrs)
✓ Tue: Day 2 complete (3 hrs)
✓ Wed: Day 3 complete (3 hrs)
_ Thu: Day 4 (started, 1 hr, paused)
_ Fri: Day 5 (not started)

Week 2:
_ Mon: Days 6-7 testing
_ Tue: ...
```

### Celebrate small wins
Each day completed = progress toward cleaner app

### Don't aim for perfection
If you finish 8 of 10 days, that's still huge improvement

---

## Commands Cheat Sheet

```bash
# Before starting a session
git status
git pull origin cleanup/sprint

# During work
git add .
git commit -m "WIP: [description]"

# When pausing
git add .
git commit -m "PAUSE: Day X - [what's done]"
git push origin cleanup/sprint

# When resuming
git checkout cleanup/sprint
git pull origin cleanup/sprint

# After full completion
git checkout main
git merge cleanup/sprint
git tag v1.0-cleanup-complete
git push origin main --tags
```

---

## Summary

**You can work on UI cleanup in any sized chunks**:
- 30 min per session ✓
- 2 hours per session ✓
- All day marathon ✓

**Just**:
1. Commit when you pause
2. Leave checkpoint notes
3. Resume from checkpoint next time

**No pressure** — progress at your pace. Even 30 min per day = done in 1–2 months.

Good luck! 🚀
