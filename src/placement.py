import logging
import math
from itertools import zip_longest
from typing import Callable, Dict, List, Optional, Tuple

import pcbnew

logger = logging.getLogger("hierpcb")


class ErrorLevel:
    INFO = 0
    WARNING = 1
    ERROR = 2


class ReportedError:
    def __init__(
        self,
        title: str,
        message: Optional[str] = None,
        level: ErrorLevel = ErrorLevel.ERROR,
        footprint: pcbnew.FOOTPRINT = None,
    ):
        self.title = title
        self.message = message
        self.level = level
        self.footprint = footprint

        logger.debug(str(self))

    def __str__(self):
        msg = [f"ERR.{self.level}\t{self.title}"]
        if self.message:
            msg += [f" Message: {self.message}"]
        if self.footprint:
            msg += [f" Footprint: {self.footprint.GetReference()}"]
        if self.sheet:
            msg += [f" Sheet: {self.sheet.identifier}"]
        if self.pcb:
            msg += [f" SubPCB: {self.pcb.path}"]

        return "\n".join(msg)


class PositionTransform:
    def __init__(self, template: pcbnew.FOOTPRINT, mutate: pcbnew.FOOTPRINT) -> None:
        # These are stored such that adding these to the position and rotation of the `template`
        # will yield the position and rotation of the `mutate`.
        self.anchor_template = template
        self.anchor_mutate = mutate

    def translate(self, pos_template: pcbnew.VECTOR2I) -> pcbnew.VECTOR2I:
        # Find the position of fp_template relative to the anchor_template:
        delta_x: int = pos_template.x - self.anchor_template.GetPosition().x
        delta_y: int = pos_template.y - self.anchor_template.GetPosition().y
        rotation = math.radians(
            self.anchor_mutate.GetOrientationDegrees()
            - self.anchor_template.GetOrientationDegrees()
        )

        # With this information, we can compute the net position after any rotation:
        new_x = (
            delta_y * math.sin(rotation)
            + delta_x * math.cos(rotation)
            + self.anchor_mutate.GetPosition().x
        )
        new_y = (
            delta_y * math.cos(rotation)
            - delta_x * math.sin(rotation)
            + self.anchor_mutate.GetPosition().y
        )
        return pcbnew.VECTOR2I(int(new_x), int(new_y))

    def orient(self, rot_template: float):
        return (
            rot_template
            - self.anchor_template.GetOrientation()
            + self.anchor_mutate.GetOrientation()
        )

class GroupManager:
    def __init__(self, board: pcbnew.BOARD, groupName: str) -> None:
        self.board: pcbnew.BOARD = board
        self.group = self._create_or_get(groupName)


    def _create_or_get(self, group_name: str) -> pcbnew.PCB_GROUP:
        """Get a group by name, creating it if it doesn't exist."""
        retGroup = None
        for group in self.board.Groups():
            if group.GetName() == group_name:
                retGroup = group
        if retGroup is None:
            retGroup = pcbnew.PCB_GROUP(None)
            retGroup.SetName(group_name)
            self.board.Add(retGroup)
        return retGroup

    def move(self, item: pcbnew.BOARD_ITEM) -> bool:
        """Force an item to be in our group, returning True if the item was moved."""
        moved = False
        # First, check if the footprint is already in the group:
        parent_group = item.GetParentGroup()
        # If the footprint is not already in the group, remove it from the current group:
        if parent_group and parent_group.GetName() != self.group.GetName():
            moved = True
            parent_group.RemoveItem(item)
            parent_group = None
        # If the footprint is not in any group, or was in the wrong group, add it to the right one:
        if parent_group is None:
            self.group.AddItem(item)

        return moved


class ContextManager(PositionTransform, GroupManager):
    def __init__(self, sourceFootprint: pcbnew.FOOTPRINT, targetFootprint: pcbnew.FOOTPRINT):
        PositionTransform.__init__(self, sourceFootprint, targetFootprint)

        sourceBoard = sourceFootprint.GetBoard()
        targetBoard = targetFootprint.GetBoard()

        #GroupManager.__init__(self, sourceBoard, )

        self.transform = PositionTransform(sourceFootprint, targetFootprint)
        self.netMapping = {}

    ## Contains information to:
    #  MoveFootprints relative to anchor
    #  Place footprints in the group
    #  Translate between nets


def clear_volatile_items(group: pcbnew.PCB_GROUP):
    """Remove all Traces, Drawings, Zones in a group."""
    board = group.GetBoard()

    itemTypesToRemove = (
        # Traces
        pcbnew.PCB_TRACK, pcbnew.ZONE,
        # Drawings
        pcbnew.PCB_SHAPE, pcbnew.PCB_TEXT,
        # Zones
        pcbnew.ZONE
    )

    for item in group.GetItems():

        # Gets all drawings in a group
        if isinstance(item.Cast(), itemTypesToRemove):
            # Remove every drawing
            board.RemoveNative(item)

