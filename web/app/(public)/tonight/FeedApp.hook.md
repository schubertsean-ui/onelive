FeedApp.tsx on this branch is still master until the hook lands.

Required in FeedApp.tsx:
1. import { TwoRoomCard } from "./TwoRoomCard"
2. import { byClock } from "../../../lib/dayClock"
3. import { applyTitleSlots } from "../../../lib/titleSlots"
4. import { eventTiming, liveEvents } from "../../../lib/feed"
5. printed = events.map(e => applyTitleSlots(e, nowMs))
6. live = liveEvents(printed, nowMs)
7. eventOnNow = eventTiming(e, nowMs) === "on-now"  // no 3h
8. Today EventList = byClock(filtered).timed then .undated
9. RichCard renders <TwoRoomCard ... />
10. No Evening first chip. No kind groups on Today.
