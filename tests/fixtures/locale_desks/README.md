# Locale-desk fixtures

Hand-written pages in the SHAPES a public desk uses, not copies of any live
site: this sandbox's egress answers `CONNECT tunnel failed, response 403` for
every host, so nothing here was fetched. They exist so `worker/locale/desk_read.read`
can be exercised offline and so `tools/locale_desks.py --fixtures` can print a
real happening count per door shape.

A count printed from these files is a FIXTURE count. It says the reader works on
that shape; it says nothing about how many happenings the live desk lists.

| file | shape it stands for |
|---|---|
| `desk_listing.html` | a local desk's dated list: `<div class="event">` cards, `<time datetime>`, one row with a date but NO clock, one row with NO date at all |
| `civic_jsonld.html` | a civic/campus calendar that publishes schema.org Event JSON-LD |
| `official_list.html` | an official list whose rows state a `<time>` but no link — a happening with no identity of its own |
| `marketplace_microdata.html` | a marketplace using schema.org microdata (`itemtype`) containers |
| `wall_login.html` | a page that is really a sign-in wall — a door read must never reach this |
