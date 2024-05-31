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
        
        sheetsByPcb = self._order_sheets_by_pcb(self.parsedSchematic.get("sheet", {}))

        self._subBoards = { pcbPath : SubPcb(self, pcbPath, sheets) for pcbPath, sheets in sheetsByPcb.items()}

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

    @property
    def validSubBoards(self):
        return {key:value for key, value in self._subBoards.items() if value.isValid}


    def save(self, cfg: ConfigMan):
        for subBoard in self.validSubBoards.values():
            enabledDict = { instance._uuid: instance.enabled for instance in subBoard._instances}
            boardData = {"selAnchor" : subBoard.selectedAnchor, "enabledDict": enabledDict}
            cfg.set(subBoard._name, value=boardData)

    def load(self, cfg: ConfigMan):
        for subBoard in self.validSubBoards.values():
            
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
        for subBoard in self.validSubBoards.values():
            subBoard.replicateInstances()

        #Fixes issues with traces lingering after being deleted
        pcbnew.Refresh()


class SubPcb:
    def __init__(self, mainSch, relPath, instanceList):
        self._name = str(Path(relPath).with_suffix(".kicad_pcb"))
        schPath = mainSch._path.parent / Path(relPath)
        brdPath = schPath.with_suffix(".kicad_pcb")

        self._schPath = schPath
        self._brdPath = brdPath

        if not brdPath.exists():
            print(f"{str(brdPath)} doesn't exist")
            self._isValid = False
            return

        subBoard = pcbnew.LoadBoard(brdPath)
            
        if len(subBoard.GetFootprints()) < 1:
            print(f"{str(brdPath)} Has no footprints")
            self._isValid = False
            return

        self._isValid = True

        self._board = subBoard
        self._validAnchors = [ fp.GetReferenceAsString() for fp in subBoard.GetFootprints() ]
        self.selectedAnchor = self._validAnchors[0]

        self.anchorFootprint = subBoard.FindFootprintByReference(self._selectedAnchor)

        self._instances = [ PcbInstance(mainSch, self, instance) for instance in instanceList]


    @property
    def board(self):
        return self._board

    @property
    def isValid(self):
        return self._isValid

    @property
    def validAnchors(self):
        return self._validAnchors

    @property
    def selectedAnchor(self):
        return self._selectedAnchor

    @selectedAnchor.setter
    def selectedAnchor(self, value):
        if not self.isValid:
            return

        if value in self.validAnchors:
            self._selectedAnchor = value
        else:
            self._selectedAnchor = self.validAnchors[0]
            print("Not valid anchor: " + str(value))
        
        self.anchorFootprint = self.board.FindFootprintByReference(self._selectedAnchor)


    # Tri-state: -1 undefined, 0- none, 1- all
    def getStateFromInstances(self):
        if not self.board:
            return 0
        enabledCount = 0
        instanceNum  = len(self._instances)

        for instance in self._instances:
            if instance.enabled:
                enabledCount += 1
        
        if enabledCount == 0:
            return 0 # No instances enabled
        elif enabledCount == instanceNum:
            return 1 # All instances enabled
        else:
            return -1 # Some Instances enabled

    def setInstancesState(self, checked):
        for instance in self._instances:
            instance.enabled = checked


    def replicateInstances(self):
        if not self.isValid:
            return

        for instance in self._instances:
            if not instance.enabled:
                continue
            instance.replicateLayout()


class PcbInstance():
    def __init__(self, mainSch, SubPcb, instanceDict):
        uuid = instanceDict["uuid"]
        self._uuid = uuid
        self._uuidPath = "/" + uuid

        name = instanceDict["property"]["Sheetname"]
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

        if not instanceAnchor:
            return

        replContext: ReplicateContext = ReplicateContext(subPcbAnchor, instanceAnchor, self._uuid)

        # Clear Volatile items first
        clear_volatile_items(replContext.group)

        # First, move the footprints and create the net mapping:
        netMap = enforce_position_footprints(replContext, fpTranslator)

        # Recreate Volatile items:
        copy_drawings(replContext)
        copy_traces  (replContext, netMap)
        copy_zones   (replContext, netMap)