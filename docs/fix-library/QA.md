# QA gate — before a write, after a write

World class here means: the live card matches what the desk printed.
A green job is not Success. A library card is not Success.

## Before any write

1. Write Success for THIS miss in one sentence.
2. Save one fixture from the real desk page (the founder shot counts).
3. A test must read that fixture and return the printed fields.
4. Search this library. Reuse FL-008 / FL-009 / FL-010 if they match.
5. Do not start ingest until that test is green on master.
6. Do not start ingest on a stub. desk_read.py under 10KB or the words SEE_LOCAL / PLACEHOLDER is a fail.
7. Do not ask the founder to click Run workflow. PM runs it.

## After the write

8. Open https://1live.co/tonight
9. Stay on Tonight. Hard-refresh.
10. Open the exact cards named in Success.
11. If any named field is still wrong, the write failed. Loop.
12. Only then mark Step 11 on the library card.

## This miss (2026-09-10)

Success: one Dave Orr Band card on 1live.co/tonight shows 6:00 PM and Hays City Store. No 1:00 PM card.
Chronicle printed that. After ingest 72 the write log had Hays City Store and 2026-09-10T18:00:00-05:00. Live still shows 1:00 PM, 6:00 PM, and Place to be confirmed.
Cause: FL-010. Hole-fill left on a candidate. Public row not updated.
