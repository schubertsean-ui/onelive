"""Every readable CAPCOG door can register without a catalog JSON row."""
from worker.locale_pack.existence import exists
from worker.locale_pack.pack import hunt


def test_every_readable_pack_door_is_listable():
    doors = hunt("us-tx-capcog")
    readable = [d for d in doors if d.readable]
    assert len(readable) >= 20
    for door in readable:
        assert exists(door.readable, door.brand) is True
