"""read(public_desk) — happening rows from a trusted desk page."""
from worker.locale_pack._desk_read_a import SRC as _A
from worker.locale_pack._desk_read_b import SRC as _B
from worker.locale_pack._desk_read_c import SRC as _C
exec(_A + _B + _C, globals())
