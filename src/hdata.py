import logging
from pathlib import Path

#from .cfgman import ConfigMan
from .simpleSchParser import sch_parse_file
from .placement import GroupManager, PositionTransform

import pcbnew
import wx

logger = logging.getLogger("hierpcb")

# MainSchData:
#   Parse functions
#
#   (main)Board
#   (main)Schematic
#
#   UUID
#   UUID Path
#
#   [SubPcb]

class BaseSchData():
    def __init__(self, baseBoard: pcbnew.BOARD):
        
        if type(baseBoard) != pcbnew.BOARD:
            raise ValueError("Didn't get type: pcbnew.BOARD")

        self._board = baseBoard

        schematicPath = Path(baseBoard.GetFileName()).with_suffix(".kicad_sch")

        if not schematicPath.exists():
            raise FileNotFoundError("Base Board Sch. not found: " + str(schematicPath))

        schematicPath = schematicPath.resolve()
        self._path = schematicPath
        self.parsedSchematic = sch_parse_file(schematicPath)
        
        sheetsByPcb = self._order_sheets_by_pcb(self.parsedSchematic["sheet"])

        self._subBoards = [ SubPcb(self, pcbPath, sheets) for pcbPath, sheets in sheetsByPcb.items()]


    def _order_sheets_by_pcb(self, sheetList):
        tempDict = {}
        for subSheet in sheetList:

            tempDict.setdefault(subSheet["property"]["Sheetfile"], [])
            
            tempDict[subSheet["property"]["Sheetfile"]].append(subSheet)
        
        return tempDict

    @property
    def board(self):
        return self._board

    @property
    def subBoards(self):
        return self._subBoards

    def replicate(self):
        for pcb in self._subBoards:
            #subboard valid check
            pass     
        #Fixes issues with traces lingering after being deleted
        pcbnew.Refresh()

# SubPcb:
#   (sub)board              # If null, no valid pcb found
#   (sub)schematic          # the source schematic of instances
#
#   validAnchors: {identifier: UUID path}
#   selectedAnchor: UUID path             # Set by using fields?
#   anchorFootprint
#
#   pcbInstances:  [instance]
#
#   saves/loads
#   board file: selected anchor

class SubPcb:
    def __init__(self, mainSch, relPath, instanceList):

        schPath = mainSch._path.parent / Path(relPath)
        brdPath = schPath.with_suffix(".kicad_pcb")

        self._schPath = schPath
        self._brdPath = brdPath

        subBoard = pcbnew.LoadBoard(brdPath)

        self._board = subBoard

        self._validAnchors = { fp.GetPath().AsString() : fp.GetReferenceAsString() for fp in subBoard.GetFootprints() }
        self._selectedAnchor = None #uuid of selected anchor

        self.anchor = pcbnew.FOOTPRINT

        self._instances = [ PcbInstance(mainSch, self, instance) for instance in instanceList]
        return


# PcbInstance:
# enabled
#
# UUID
# UUID Path
#
# Transform
# GroupManager
#
# When looping through instances,
# the sub sheet can also be provided
#
# saves/loads the properties:
#   sheet uuid: bool

class PcbInstance():
    def __init__(self, mainSch, SubPcb, instance):
        uuid = instance["uuid"]
        self._uuid = uuid

        name = instance["property"]["Sheetname"]
        self._name = name      

        # Schematic path already in SubPcb
        # relPath = instance["property"]["Sheetfile"]
        # schPath = mainSch._path.parent / Path(relPath)

        self._mainSch = mainSch
        self._SubPcb = SubPcb

        # Prepare grouper from uuid
        self._groupManager = GroupManager(mainSch.board, uuid)

        instanceAnchor = board.GetFootprints()[0]

        # Move items relative to anchor footprints
        self._transformer = PositionTransform(SubPcb.anchor, instanceAnchor)

        return

    # Gets corrosponding fp in the main schematic
    def _fpTranslator(self, subPcbFootprint: pcbnew.FOOTPRINT):
        newPath = pcbnew.KIID_PATH(self._mainSch._path + subPcbFootprint.GetPath())
        mainFootprint = self._mainSch.board.FindFootprintByPath(newPath)
        return mainFootprint

    def replicateLayouts(self):
        """Enforce the positions of objects in PCB template on PCB mutate."""

        errors: List[ReportedError] = []
        groupman: GroupManager = GroupManager(targetBoard)

        # Find the anchor footprint on the subPCB:
        anchor_subpcb = self._SubPcb.anchor
        anchor_target = self._fpTranslator(anchor_subpcb)

        # We need to force all the footprints to be in the same group. To do that,
        # we automatically create a group for the anchor footprint if it doesn't exist and
        # move all the footprints into it.
        group_name = f"subpcb_{sheet.human_path}"
        group = groupman.create_or_get(group_name)

        # Clear Volatile items first
        self.clear_volatile_items()

        # First, move the footprints and create the net mapping:
        err_footprints = self._enforce_position_footprints()
        errors.extend(err_footprints)

        # Recreate traces:
        err_traces = self._copy_traces()
        errors.extend(err_traces)

        # Recreate Drawings
        err_drawings = self._copy_drawings()
        errors.extend(err_drawings)

        # Recreate Zones
        err_zones = self._copy_zones()
        errors.extend(err_zones)


    def _clear_volatile_items(targetBoard: pcbnew.BOARD, group: pcbnew.PCB_GROUP):
        """Remove all zones in a group."""
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
                targetBoard.RemoveNative(item)


    def _copy_footprint_fields(self,
        sourceFootprint: pcbnew.FOOTPRINT,
        targetFootprint: pcbnew.FOOTPRINT,
    ):

        transform   = self._transformer

        # NOTE: Non-center aligned Fields position changes with rotation.
        #       This is not a bug. The replicated pcbs are behaving the 
        #       exact same as the original would when rotated.

        # Do any other field values need preserved?
        originalReference = targetFootprint.GetReference()

        # Remove Existing footprint fields
        for existingField in targetFootprint.GetFields():
            targetFootprint.RemoveNative(existingField)
        
        # Add all the source fields and move them
        for sourceField in sourceFootprint.GetFields():
            newField = sourceField.CloneField()
            newField.SetParent(targetFootprint)
            
            newField.SetPosition(transform.translate(sourceField.GetPosition()))
            newField.Rotate(newField.GetPosition(), transform.orient(pcbnew.ANGLE_0))

            targetFootprint.AddField(newField)

        targetFootprint.SetReference(originalReference)


    def _copy_footprint_data(self,
        sourceFootprint: pcbnew.FOOTPRINT,
        targetFootprint: pcbnew.FOOTPRINT,
    ):
        
        transform   = self._transformer

        # Most definetly exists a better way to do this...
        # Maybe footprint cloning? 


        if sourceFootprint.IsFlipped() != targetFootprint.IsFlipped():
            targetFootprint.Flip(targetFootprint.GetPosition(), False)

        # The list of properties is from the ReplicateLayout plugin. Thanks @MitjaNemec!
        targetFootprint.SetLocalClearance(sourceFootprint.GetLocalClearance())
        targetFootprint.SetLocalSolderMaskMargin(sourceFootprint.GetLocalSolderMaskMargin())
        targetFootprint.SetLocalSolderPasteMargin(sourceFootprint.GetLocalSolderPasteMargin())
        targetFootprint.SetLocalSolderPasteMarginRatio(
            sourceFootprint.GetLocalSolderPasteMarginRatio()
        )
        targetFootprint.SetZoneConnection(sourceFootprint.GetZoneConnection())

        # Move the footprint:
        targetFootprint.SetPosition(transform.translate(sourceFootprint.GetPosition()))
        targetFootprint.SetOrientation(transform.orient(sourceFootprint.GetOrientation()))


    def _enforce_position_footprints(self):

        sourceBoard = self._SubPcb.board
        targetBoard = self._mainSch.board
        transform   = self._transformer

        errors = []

        # The keys are the sub-pcb net codes
        # The values are the new net codes
        footprintNetMapping = {}

        # For each footprint in the sub-PCB, find the corresponding footprint on the board:
        for sourceFootprint in sourceBoard.GetFootprints():
            # Find the corresponding footprint on the board:

            targetFootprint = self._fpTranslator(sourceFootprint)

            if not targetFootprint:
                errors.append(
                    ReportedError(
                        "footprint not found, skipping",
                        message=f"Corresponding to {sourceFootprint.GetReference()} for sheet {sheet.human_name}",
                        footprint=sourceFootprint,
                        pcb=sheet.pcb,
                        level=ErrorLevel.WARNING,
                    )
                )
                continue

            # Copy the properties and move the template to the target:
            self._copy_footprint_data(sourceFootprint, targetFootprint)
            
            self._copy_footprint_fields(sourceFootprint, targetFootprint)

            # Assumes pads are ordered by the pad number
            for sourcePadNum, sourcePad in enumerate(sourceFootprint.Pads()):
                targetPad = targetFootprint.Pads()[sourcePadNum]

                sourceCode = sourcePad.GetNetCode()
                targetCode = targetPad.GetNetCode()
                
                footprintNetMapping[sourceCode] = targetCode

            # Move the footprint into the group if one is provided:
            if groupmv(targetFootprint):
                errors.append(
                    ReportedError(
                        f"footprint {targetFootprint} is in the wrong group",
                        pcb=sheet.pcb,
                        level=ErrorLevel.ERROR,
                    )
                )
        
        self._footprintNetMapping = footprintNetMapping
        
        return errors


    def _copy_traces(self):

        sourceBoard = self._SubPcb.board
        targetBoard = self._mainSch.board
        transform   = self._transformer

        errors = []
        for sourceTrack in sourceBoard.Tracks():
            # Copy track to trk:
            # logger.info(f"{track} {type(track)} {track.GetStart()} -> {track.GetEnd()}")
            
            newTrack = sourceTrack.Duplicate()
            targetBoard.Add(newTrack)

            sourceNetCode = sourceTrack.GetNetCode()
            newNetCode = footprintNetMapping.get(sourceNetCode, 0)
            newTrack.SetNet(targetBoard.FindNet(newNetCode))

            # Sets Track start and end point
            # Via's ignore the end point, just copying anyways
            newTrack.SetStart(transform.translate(sourceTrack.GetStart()))
            newTrack.SetEnd  (transform.translate(sourceTrack.GetEnd()  ))

            if type(newTrack) == pcbnew.PCB_VIA:
                newTrack.SetIsFree(False)

            self.mover(newTrack)

        return errors


    def _copy_drawings(self):

        sourceBoard = self._SubPcb.board
        targetBoard = self._mainSch.board
        transform   = self._transformer

        errors = []
        for sourceDrawing in sourceBoard.GetDrawings(): 
            
            newDrawing = sourceDrawing.Duplicate()
            targetBoard.Add(newDrawing)

            # Set New Position
            newDrawing.SetPosition(transform.translate(sourceDrawing.GetPosition()))

            # Drawings dont have .SetOrientation()
            # instead do a relative rotation
            newDrawing.Rotate(newDrawing.GetPosition(), transform.orient(pcbnew.ANGLE_0))

            self.mover(newDrawing)

        return errors


    def _copy_zones(self):

        sourceBoard = self._SubPcb.board
        targetBoard = self._mainSch.board
        transform   = self._transformer

        errors = []
        for sourceZone in sheet.pcb.subboard.Zones():
            
            newZone = sourceZone.Duplicate()

            sourceNetCode = sourceZone.GetNetCode()
            newNetCode = footprintNetMapping.get(sourceNetCode, 0)
            newZone.SetNet(targetBoard.FindNet(newNetCode))

            targetBoard.Add(newZone)

            # Set New Position
            # newZone.SetPosition(transform.translate(zone.GetPosition()))

            # Temporary Workaround:
            # Move zone to 0,0 by moving relative
            newZone.Move(-newZone.GetPosition())
            # Move zone to correct location
            newZone.Move(transform.translate(sourceZone.GetPosition()))

            # Drawings dont have .SetOrientation()
            # instead do a relative rotation
            newZone.Rotate(newZone.GetPosition(), transform.orient(pcbnew.ANGLE_0))

            mover(newZone)

        return errors