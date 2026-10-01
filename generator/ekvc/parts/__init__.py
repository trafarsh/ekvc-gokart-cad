"""Part builders.  Every builder returns a `PartDef`."""
from dataclasses import dataclass, field


@dataclass
class PartDef:
    pid: str                 # part number / file stem, e.g. "C-WHL-01"
    name: str                # human readable
    shape: object            # cq.Shape (single or multi-body)
    rgb: tuple = (0.7, 0.7, 0.7)
    material: str = ""
    desc: str = ""
    group: str = "misc"      # for BOM grouping
    meta: dict = field(default_factory=dict)

    @property
    def stem(self):
        n = "".join(c if c.isalnum() else "_" for c in self.name).strip("_")
        while "__" in n:
            n = n.replace("__", "_")
        return f"{self.pid}_{n}"
