# Fix library

Search here before a new fix (step 5). Save here after live verify (step 12).

| ID | Failure | Cause | Fix | Step 11 |
|---|---|---|---|---|
| FL-001 | Today N below that locale’s aggregator today union | Missing end treated as over | Missing end stays the locale day | FAIL — Austin 16 vs Chronicle 196 |
| FL-002 | Ingest dies after a long walk | Missing import name | Export complete_year; smoke-import test | Ingest 22 fail |
| FL-003 | Date-only start missing from Today | YYYY-MM-DD as UTC midnight | Date-only is that locale day | Partial |
| FL-004 | Product file became SEE_FILE | Stub shipped | Restore real module. Stubs forbidden | Restored |
