# QA gate — before a write, after a write

World class here means: the live card matches what the desk printed.
A green job is not Success. A library card is not Success.

## Before any write

1. Write Success for THIS miss in one sentence.
2. Save one fixture from the real desk page (the founder shot counts).
3. A test must read that fixture and return the printed fields.
4. Search this library. Reuse FL-008 / FL-009 if they match.
5. Do not start ingest until that test is green on master.

## After the write

6. Open https://1live.co/tonight
7. Stay on Tonight. Hard-refresh.
8. Open the exact cards named in Success.
9. If any named field is still wrong, the write failed. Loop.
10. Only then mark Step 11 on the library card.

## This miss (2026-09-10)

Success: Dave Orr Band on 1live.co/tonight shows 6:00 PM and Hays City Store.
Chronicle printed that. 1Live showed 1:00 PM and Place to be confirmed.

Do not start another write until tests/test_fl008_fl009_chronicle_list.py is green
and desk_read uses card_place on the list card.
