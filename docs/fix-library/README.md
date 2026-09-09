# Fix library

Search here before a new fix (step 5). Save here after live verify (step 12).
Access: classify, then this index. Evaluate same class + same observable. Existing fix wins.

| ID | Class | Failure | Cause | Fix | Step 11 |
|---|---|---|---|---|---|
| FL-001 | VIEW | Today N below union | Missing end treated as over | Missing end stays the locale day | FAIL — 16 vs 196 |
| FL-002 | IMPORT | Ingest dies after a long walk | Missing import name | Export complete_year | Fixed |
| FL-003 | VIEW | Date-only missing from Today | UTC midnight | Date-only is that locale day | Partial |
| FL-004 | STUB | Product file became SEE_FILE | Stub shipped | Restore real module | Restored |
| FL-005 | CATALOG | Validated desk never publishes | Gate wants two sources | One validated door is enough | Not yet |
| FL-006 | OPS | Old ingest blocks the new one | cancel-in-progress: false | Newest master ingest wins; no ingest on docs-only | Applied |
