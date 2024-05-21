import collections
import dataclasses
import logging
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .cfgman import ConfigMan

import pcbnew
import wx

from .simpleSchParser import sch_parse_file

logger = logging.getLogger("hierpcb")


SchPath = Tuple[str, ...]

FootprintID = str  # Unique id for a footprint across all sub-schematics.

# A class to store
# pcbnew.BOARD
# validAnchors: {identifier: UUID path}
# selected anchor
class PCBRoom:
    """Holds the data for a 'room' in the PCB layout, correponding to the layout for a schematic sheet."""

    def __init__(self, path: Path):
        self.path = path
        # Load the room data from the file.
        self.subboard = pcbnew.LoadBoard(str(path))
        assert self.subboard is not None
        logger.info(
            f"Imported {path}, with "
            f"{len(self.subboard.GetFootprints())} footprints, "
            f"{len(self.subboard.GetTracks())} tracks, and "
            f"{len(self.subboard.GetDrawings())} drawings."
        )

        self.selected_anchor: Optional[wx.FOOTPRINT] = None

    def get_anchor_ref(self) -> Optional[str]:
        if self.selected_anchor is None:
            return None
        return self.selected_anchor.GetReference()

    def set_anchor_ref(self, ref: str):
        # Find the footprint with the given reference:
        for fp in self.subboard.GetFootprints():
            if fp.GetReference() == ref:
                self.selected_anchor = fp
                return
        logger.warning(f"Could not find footprint {ref} in board {self.path}.")

    def get_heuristic_anchor_ref(self) -> Optional[str]:
        """Guess the reference prefix of the footprint that will be used as an anchor."""
        prefixes = collections.defaultdict(lambda: 0)

        def prefix(s: str) -> str:
            return s.rstrip(string.digits)

        fps = []
        for fp in self.subboard.GetFootprints():
            prefixes[prefix(fp.GetReference())] += 1
            fps.append(fp)

        heuristic_list = []
        for fp in fps:
            ref = fp.GetReference()
            heuristic_list.append((-fp.GetArea(), prefixes[prefix(ref)], ref))

        _, _, min_ref = min(heuristic_list)
        return min_ref

    def get_anchor_refs(self) -> Dict[FootprintID, str]:
        """Get the references of the footprints that can be used as anchors."""
        rv = {}
        for fp in self.subboard.GetFootprints():
            path = fp.GetPath().AsString()
            if path is None or path == "":
                logger.warn(f"Missing path: {fp.GetReference()} ({self.path})")
                continue
            rv[path] = fp.GetReference()

        return rv

    def __str__(self) -> str:
        # Head line with the sheet name and whether it has a PCB layout.
        rv = [f"PCB {self.path}"]
        for k, v in self.get_anchor_refs().items():
            ksumm = "/".join(k[:8] for k in k.split("/"))
            rv.append(f"  {ksumm}: {v}")

        return "\n".join(rv)

    @property
    def is_legal(self) -> bool:
        """Check if the room can be handled by our engine."""
        # For a room to be legal, there must be at least one footprint. That's it.
        return len(self.get_anchor_refs()) > 0


class SchSheet:
    """Class to hold information about a schematic sheet."""

    def __init__(self, sheetid: str = "", parent: Optional["SchSheet"] = None) -> None:
        # The sheet identifier, if "", this is the root sheet.
        self.sheetid: str = sheetid
        # The parent sheet. If None, this is the root sheet.
        self.parent: Optional["SchSheet"] = parent

        # The immediate child sheets of this node.
        self.children: Dict[str, "SchSheet"] = {}

        # These are only available if the sheet is referenced by a footprint:
        # The file name of the schematic sheet.
        self.file: Optional[Path] = None
        # The human-readable name of the schematic sheet.
        self.name: Optional[str] = None

        # TODO: Pointer to the PCB layout data.
        self.pcb: Optional[PCBRoom] = None

        # Metadata for UI rendering:
        self.list_ref: Optional[wx.TreeListItem] = None
        self.checked: bool = False

    def get(self, key: SchPath, create=False) -> "SchSheet":
        """Get a sheet by its key."""
        # If the key is empty, we are done.
        if len(key) == 0:
            return self
        # Otherwise the first element of the key is the sheet identifier.
        cons, rest = key[0], key[1:]
        if cons not in self.children:
            if not create:
                raise KeyError(f"Sheet {key} not found in {self.identifier}.")
            self.children[cons] = SchSheet(cons, self)
        # Recur on the rest in the child sheet.
        return self.children[cons].get(rest, create)

    def tree_iter(self, skip_root=False):
        """Iterate over the tree."""
        if not skip_root:
            yield self
        for _, child in sorted(self.children.items()):
            yield from child.tree_iter()

    def set_checked_default(self, ancestor_checked: bool = False):
        """Set the tree to its default state recursively."""
        self.checked = False
        # Check if the sheet has a PCB:
        if self.pcb and self.pcb.is_legal:
            # If an ancestor is checked, this sheet cannot be checked.
            # Otherwise, this is the first sheet from the root to be elligible,
            if not ancestor_checked:
                self.checked = True

        # Recur on the children:
        for child in self.children.values():
            child.set_checked_default(child, self.checked or ancestor_checked)

    @property
    def identifier(self) -> str:
        if self.parent is None:
            return self.sheetid
        return self.parent.identifier + "/" + self.sheetid

    @property
    def human_name(self) -> str:
        return self.name if self.name is not None else self.sheetid[:8]

    @property
    def human_path(self) -> str:
        if self.parent is None:
            return self.human_name
        return self.parent.human_path + "/" + self.human_name

    def __str__(self) -> str:
        # Head line with the sheet name and whether it has a PCB layout.
        rv = [self.human_name + (f" (+ PCB {self.pcb.path})" if self.pcb else "")]
        # If there are children, print them.
        for _, child in sorted(self.children.items()):
            c_str = str(child).splitlines()
            # The first line is the child's name, so it should look like a node in the tree.
            rv.append(f"├─ {c_str[0]}")
            for line in c_str[1:]:
                rv.append(f"│  {line}")
        return "\n".join(rv)


# MainSchData:
#   Parse functions
#   UUID
#   [UsableSubsheets]

class BaseSchData():
    def __init__(self, baseBoard: pcbnew.BOARD):
        
        if type(baseBoard) != pcbnew.BOARD:
            raise ValueError("Didn't get type: pcbnew.BOARD")

        self._board = baseBoard

        schematicPath = Path(baseBoard.GetFileName())

        if not schematicPath.exists():
            raise FileNotFoundError("Base Board Sch. not found: " + str(schematicPath))

        schematicPath = schematicPath.resolve()
        self.parsedSchematic = sch_parse_file(schematicPath)
        
        tempDict = {}
        for subSheet in self.parsedSchematic["sheet"]:
            tempDict.setdefault(subSheet.fileName.value, [])
            
            subPcbFile = schematicPath.parent / Path(subSheet.fileName.value)

            tempDict[subPcbFile].append(subSheet)

        self._subBoards = [ SubPcb(key, value) for key, value in tempDict.items() ]

    def save():
        return

    @property
    def board(self):
        return self._board

    @property
    def subBoards(self):
        return self._subBoards

# SubSchData:
#   Sub-sheet file as string ():
#       pcbnew.BOARD                          # If null, no valid pcb found
#       validAnchors: {identifier: UUID path}
#       selectedAnchor: UUID path             # Set by using fields?
#       pcbInstances:
#           [instance]

#   saves/loads
#   selected anchor

class SubPcb:
    def __init__(self, path, instanceList):
        return
# SubPcbInstance:
# enabled
# UUID /Path
# Transform
# GroupManager

# When looping through instances,
# the sub sheet can also be provided

# saves/loads the properties:

#   sheet instances: bool

class PcbInstances:

    def replicateLayouts(self, KicadSch):
        return


class HierarchicalData:
    def __init__(self, board: pcbnew.BOARD):
        self.board = board
        self.basedir = Path(board.GetFileName()).parent
        self.root_sheet, self.pcb_rooms = get_sheet_hierarchy(board, self.basedir)

    def load(self, cfg: ConfigMan):
        # Load the PCB rooms:
        for subpcb in self.pcb_rooms.values():
            anchor = cfg.get(
                "subpcb",
                str(subpcb.path.relative_to(self.basedir)),
                "anchor",
                default=subpcb.get_heuristic_anchor_ref(),
            )
            subpcb.set_anchor_ref(anchor)

        for sheet in self.root_sheet.tree_iter():
            sheet.checked = cfg.get("sheet", sheet.identifier, "checked", default=False)
        sheet.cleanup_checked()

    def save(self, cfg: ConfigMan):
        # Save the current state:
        cfg.clear("subpcb")
        for subpcb in self.pcb_rooms.values():
            cfg.set(
                "subpcb",
                str(subpcb.path.relative_to(self.basedir)),
                "anchor",
                value=subpcb.get_anchor_ref(),
            )
        cfg.clear("sheet")
        for sheet in self.root_sheet.tree_iter():
            cfg.set("sheet", sheet.identifier, "checked", value=sheet.checked)


def get_sheet_key_from_footprint(fp: pcbnew.FOOTPRINT) -> Optional[SchPath]:
    key = fp.GetPath().AsString().split("/")
    if len(key) <= 1:
        # Skip footprints that are not on a sheet.
        logger.debug(f"Footprint {fp.GetReference()} is not on a sheet, skipping...")
        return None
    assert key[0] == ""
    return tuple(key[1:-1])