import logging
from pathlib import Path

from .cfgman import ConfigMan
from .simpleSchParser import sch_parse_file
from .placement import *

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

        self._subBoards = { pcbPath : SubPcb(self, pcbPath, sheets) for pcbPath, sheets in sheetsByPcb.items()}
        print(self._subBoards)

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

    def save(self, cfg: ConfigMan):
        for subBoard in self.subBoards.values():
            enabledDict = { instance._uuid: instance.enabled for instance in subBoard._instances}
            boardData = {"selAnchor" : subBoard.selectedAnchor, "enabledDict": enabledDict}
            print(boardData)
            cfg.set(subBoard._name, value=boardData)

    def load(self, cfg: ConfigMan):
        for subBoard in self.subBoards.values():
            boardData = cfg.get(subBoard._name)
            if not boardData:
                print("boardData empty")
                # Add error output
                continue

            print(boardData)

            subBoard.selectedAnchor = boardData.get("selAnchor")

            for instance in subBoard._instances:
                isEnabled = boardData.get("enabledDict").get(instance._uuid, None)
                if isEnabled == None:
                    print("isEnabled empty")
                    continue
                instance._enabled = isEnabled

    def replicate(self):
        for subBoard in self.subBoards.values():
            subBoard.replicateInstances()

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
        self._name = relPath
        schPath = mainSch._path.parent / Path(relPath)
        brdPath = schPath.with_suffix(".kicad_pcb")

        self._schPath = schPath
        self._brdPath = brdPath

        subBoard = pcbnew.LoadBoard(brdPath)

        self._board = subBoard

        self._validAnchors = [ fp.GetReferenceAsString() for fp in subBoard.GetFootprints() ]
        self._selectedAnchor = self._validAnchors[0]

        self.anchorFootprint = subBoard.FindFootprintByReference(self._selectedAnchor)

        self._instances = [ PcbInstance(mainSch, self, instance) for instance in instanceList]
        

    def replicateInstances(self):
        for instance in self._instances:
            if not instance.enabled:
                continue
            instance.replicateLayout()

    @property
    def board(self):
        return self._board

    @property
    def validAnchors(self):
        return self._validAnchors

    @property
    def selectedAnchor(self):
        return self._selectedAnchor
    
    @selectedAnchor.setter
    def selectedAnchor(self, value):
        if value in self.validAnchors:
            self._selectedAnchor = value
        else:
            self._selectedAnchor = self.validAnchors[0]
            print("Not valid anchor: " + str(value))
        
        self.anchorFootprint = self.board.FindFootprintByReference(self._selectedAnchor)

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
        self._uuidPath = "/" + uuid

        name = instance["property"]["Sheetname"]
        self._name = name

        self._mainSch = mainSch
        self._SubPcb = SubPcb

        self._enabled = False

    @property
    def enabled(self):
        return self._enabled
    
    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    def replicateLayout(self):
        """Enforce the positions of objects in PCB template on PCB mutate."""

        fpTranslator = FootprintTranslator(self._mainSch.board, self._uuidPath)

        # Find the anchor footprint on the subPCB:
        subPcbAnchor = self._SubPcb.anchorFootprint
        instanceAnchor = fpTranslator.getTarget(subPcbAnchor)

        replContext: ReplicateContext = ReplicateContext(subPcbAnchor, instanceAnchor, self._name)

        # Clear Volatile items first
        clear_volatile_items(replContext.group)

        # First, move the footprints and create the net mapping:
        netMap = enforce_position_footprints(replContext, fpTranslator)

        # Recreate Volatile items:
        copy_drawings(replContext)
        copy_traces  (replContext, netMap)
        copy_zones   (replContext, netMap)