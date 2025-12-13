# Next Steps - Quick Reference

**Date**: December 12, 2025  
**Last Update**: December 11, 2025 (Evening)

---

## 🔬 IMMEDIATE: Test Browser Back Fix

### Run This Command

```bash
cd /home/rjvisser/projects/req-tst/boardfarm-bdd/tests/ui_helpers

python ui_mbt_discovery.py \
  --url http://127.0.0.1:3000 \
  --username admin --password admin \
  --seed-map ui_map.json \
  --output fsm_graph_with_back.json
```

**Duration**: ~10-15 minutes

---

## ✅ Success Criteria

### Look for in Console:
- ✅ **NO** "Failed to locate link: Virtual Parameters"
- ✅ **NO** "Failed to locate link: Files"
- ✅ "Exploring state [depth 3]: V_ADMIN_VIRTUALPARAMETERS"
- ✅ "Exploring state [depth 3]: V_ADMIN_FILES"
- ✅ "Exploring state [depth 3]: V_ADMIN_CONFIG"
- ✅ Final count: "States explored: 15-25"

### Check Statistics:
```bash
jq '.statistics' fsm_graph_with_back.json
```

**Expected:**
```json
{
  "state_count": 38-45,        // vs 32 before
  "transition_count": 40-60,   // vs 18 before
  "visited_states": 15-25      // vs 6 before
}
```

---

## 🎯 Decision Path

### ✅ If 15+ States Explored
**→ SUCCESS! Proceed to Phase 8: Resilience Evaluation**

Next steps:
1. Compare `ui_map.json` vs `fsm_graph_with_back.json`
2. Document discovered states/transitions
3. Set up UI change simulation environment
4. Plan resilience test scenarios

---

### ⚠️ If < 15 States Explored
**→ More debugging needed**

Check:
1. How many "Failed to locate" errors?
2. How many "Browser back failed" messages?
3. Which admin pages were discovered?
4. What depth was reached?

Next fixes:
- If back failed: Adjust timeout/wait times
- If links not found: Re-discover links after navigation (Option D)
- If depth limit: Increase DFS max depth
- If other: Analyze logs for pattern

---

## 📊 Compare Before/After

### Before Browser Back Fix
```
States explored: 6
Transitions: 18
Admin pages: 2/7 (Presets, Provisions)
Issues: 50+ "Failed to locate" errors
```

### After Browser Back Fix (Expected)
```
States explored: 15-25
Transitions: 40-60
Admin pages: 5-7/7 (+ Virtual Parameters, Files, Config, Permissions, Users)
Issues: < 10 failures
```

---

## 📝 Log Analysis

### What to Grep For

**Success patterns:**
```bash
grep "Exploring state \[depth 3\]:" logs.txt
grep "Navigation transition:" logs.txt | wc -l
grep "States explored:" logs.txt
```

**Failure patterns:**
```bash
grep "Failed to locate" logs.txt | wc -l
grep "Browser back failed" logs.txt
grep "Can't navigate to" logs.txt
```

**Deduplication working:**
```bash
grep "already recorded, skipping duplicate" logs.txt | wc -l
```

**Loading states skipped:**
```bash
grep "Skipping exploration of ephemeral" logs.txt
```

---

## 🐛 Quick Debug Checklist

If results still poor:

- [ ] Check GenieACS is running on http://127.0.0.1:3000
- [ ] Check credentials: admin/admin
- [ ] Check ui_map.json exists and has 31 pages
- [ ] Check for Python errors in output
- [ ] Check browser didn't crash (look for Playwright errors)
- [ ] Check disk space (output files can be large)
- [ ] Check timeout errors (increase if many)

---

## 📚 Documentation References

- **Architecture**: `Hybrid_MBT.md`
- **Priority Fixes**: `PRIORITY_1_FIXES.md`
- **Browser Back**: `BROWSER_BACK_FIX.md`
- **Resume Guide**: `../.agent/memory_bank/RESUME_DEC_12.md`

---

## ⚡ Quick Commands

### Check Current State
```bash
# See what files we have
ls -lh *.json

# Check Stage 1 output
jq '.statistics' ui_map.json

# Check Stage 2 output (old)
jq '.statistics' fsm_graph.json
```

### Re-run Stage 1 (if needed)
```bash
python discover_ui.py \
  --url http://127.0.0.1:3000 \
  --username admin --password admin \
  --output ui_map.json
```

### Check File Sizes
```bash
wc -l ui_map.json fsm_graph*.json
```

---

**Status**: ✅ Ready to test  
**Expected Time**: 10-15 minutes for discovery run  
**Next After Success**: Phase 8 setup
