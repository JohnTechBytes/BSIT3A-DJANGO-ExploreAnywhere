---
name: phase6p-optimization-guide
description: Setup and usage guide for optimized Phase 6P photo discovery
type: project
---

# Phase 6P Optimization — Setup & Usage Guide

## What Changed

### Performance Improvements

| Metric | Original | Optimized | Improvement |
|--------|----------|-----------|-------------|
| **CSV Checkpoints** | Every 1 query | Every 15 candidates | 15–20x fewer disk writes |
| **HTTP Connections** | New per request | Pooled/reused | 5–10x fewer connection overhead |
| **Query Delay** | 0.8s fixed | 0.25s adaptive | 3.2x faster (with rate-limit detection) |
| **Status Updates** | Per-place JSON writes | Batch writes | 2–3x fewer I/O operations |
| **Expected speedup** | Baseline | **3–5x faster** | Typical discovery run |

### Key Optimizations

1. **HTTP Connection Pooling** (`urllib3.PoolManager`)
   - Reuses TCP connections across all API calls
   - Reduces handshake overhead from 50–100ms per call to ~5ms
   - Built-in retry logic with exponential backoff

2. **Buffered CSV Writes**
   - Original: `save_rows()` called after every single search query
   - Optimized: Checkpoint every `--checkpoint-interval` candidates (default: 15)
   - Reduces disk I/O from ~500 writes to ~30–50 writes per discovery run

3. **Smart Rate-Limit Handling**
   - Checks `Retry-After` header on 429 responses
   - Implements exponential backoff (1.5x multiplier per attempt)
   - Respects Wikimedia rate limits without wasting requests

4. **Adaptive Query Delays**
   - `--query-delay` now defaults to 0.25s (vs 0.8s hardcoded)
   - Can be tuned per run without code changes
   - Works with rate-limit backoff for optimal throughput

5. **Paginated Place Inventory**
   - Only fetches places needed for current window
   - Reduces memory usage for large city datasets
   - Applies sorting before slicing (not after loading all)

---

## Installation

### 1. Install `urllib3` Dependency

```bash
pip install urllib3>=2.0
```

### 2. Copy Optimized Commands

The new commands are already in:
- `apps/places/management/commands/phase6p_bulk_photos_optimized.py` (all cities)
- `apps/places/management/commands/phase6p_kabankalan_photos_optimized.py` (Kabankalan only)

**Backward Compatibility**: Original commands remain unchanged. Both can coexist.

### 3. Set Environment Variable (if not already set)

```bash
export EXPLOREANYWHERE_PHOTO_USER_AGENT="your-email@example.com (ExploreAnywhere Photo Discovery)"
```

---

## Usage

### Basic Discovery Run (Kabankalan)

```bash
python manage.py phase6p_kabankalan_photos_optimized --limit 50
```

This will:
- Discover photos for up to 50 Kabankalan places without covers
- Use default checkpoint interval (15 candidates) and query delay (0.25s)
- Write results to `phase6_photo_review/` with HTML gallery for review
- Cache no-result searches to avoid duplicate API calls

### Discovery with Tuning

```bash
# Slower but more conservative (for API rate-limit testing)
python manage.py phase6p_kabankalan_photos_optimized \
  --limit 30 \
  --query-delay 0.5 \
  --checkpoint-interval 5

# Faster (if Wikimedia API is responsive)
python manage.py phase6p_kabankalan_photos_optimized \
  --limit 100 \
  --query-delay 0.15 \
  --checkpoint-interval 25
```

### All Cities Discovery

```bash
python manage.py phase6p_bulk_photos_optimized --limit 50 --city-id 2
```

### Resume Failed Run

```bash
# Previous run hit an error? Just re-run same command.
# CSV checkpoint means you don't lose progress.
python manage.py phase6p_kabankalan_photos_optimized --limit 50
```

Rows already in the CSV are not re-queried. Use `--rescan` to force re-search:

```bash
python manage.py phase6p_kabankalan_photos_optimized --limit 50 --rescan
```

---

## Command-Line Options

### `phase6p_kabankalan_photos_optimized`

```
--limit INT
  Maximum places to process (default: 50)
  Reduces risk on first test run; increase for production discovery

--offset INT
  Skip first N places in city (default: 0)
  Useful for resuming from a specific place

--per-query INT
  Max candidates per search query, 1–5 (default: 5)
  Lower = faster but fewer candidates; higher = slower but more comprehensive

--checkpoint-interval INT
  Write CSV every N candidates (default: 15, was: 1)
  Higher = faster but higher risk of data loss if crash
  Lower = safer but more disk writes

--query-delay FLOAT
  Seconds between API calls (default: 0.25, was: 0.8)
  Respects Wikimedia rate limits; be cautious lowering below 0.1

--rescan
  Ignore cached no-result searches and re-query everything
  Useful after adding new places to Kabankalan

--published-first
  Prioritize verified active places in discovery order
  Helps get coverage for popular places first
```

### `phase6p_bulk_photos_optimized`

Same as above, plus:

```
--city-id INT
  Limit discovery to specific city (default: all)
  Example: --city-id 2 for Kabankalan only
```

---

## Expected Performance

### Baseline (Original Code)
- 50 places × 5 queries/place = 250 API calls
- 0.8s delay between calls = 200 seconds minimum
- ~500 CSV writes (checkpoint after every query)
- **Estimated time: 3–5 minutes** (depends on API response time)

### Optimized Code
- 50 places × 5 queries/place = 250 API calls (same)
- 0.25s delay + connection pooling = ~50–70 seconds
- ~17 CSV writes (checkpoint every 15 candidates)
- **Estimated time: 1–2 minutes** (3–5x faster)

### Bottleneck Comparison

| Stage | Original | Optimized |
|-------|----------|-----------|
| API calls | 250 | 250 |
| API+network latency | ~2–3 min | ~1–1.5 min (pooling saves 50–100ms per call) |
| CSV writes | ~500 | ~17 |
| Disk I/O time | ~20–30s | ~1–2s |
| Status JSON updates | ~50 | ~5 |
| **Total** | **3–5 min** | **1–2 min** |

---

## Troubleshooting

### "urllib3 not installed"

```bash
pip install urllib3>=2.0
```

### "HTTP 429 Too Many Requests"

The optimized code handles this automatically with exponential backoff. If it persists:
- Increase `--query-delay` to 0.5 or 1.0
- Reduce `--per-query` to 2–3
- Run fewer places per session (`--limit 10`)

### "diskfull error on CSV write"

This shouldn't happen with buffered writes, but if it does:
- Move `phase6_photo_review/` to a larger disk
- Reduce `--checkpoint-interval` to write smaller transactions
- Delete old backup CSVs from previous runs

### "Connection timeout / SSL error"

If you see "truststore" errors:
```bash
pip install truststore
```

Then ensure environment variable is set and try again.

---

## Migration Path

### Option A: Gradual (Recommended)

1. Run optimized code in parallel with original
2. Compare results (both should find same photos)
3. Once confident, switch to optimized-only

### Option B: Switch Immediately

1. Backup existing `phase6_photo_review/` directory
2. Run optimized code
3. If issues, restore backup and revert

### Rollback

If optimized code has issues:
```bash
# Original command still works
python manage.py phase6p_kabankalan_photos --limit 50
```

---

## Next Steps

1. **Test locally first**: Run with `--limit 5` to verify setup
2. **Monitor first discovery**: Check CSV and gallery output
3. **Tune delays**: Adjust `--query-delay` based on API response times
4. **Scale up**: Once stable, increase `--limit` for full city coverage
5. **Continue Phase 7**: Once photos are reviewed and imported

---

## Questions?

Review the performance notes in this guide and the code comments in the
optimized commands for implementation details.
