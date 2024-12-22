import logging
from pathlib import Path

from .cfgman import ConfigMan
from .simpleSchParser import sch_parse_file
from .placement import *

import pcbnew
import wx

logger = logging.getLogger("hierpcb")

def sch_from_brd_path(brdPath):
    return brdPath.with_suffix(".kicad_sch")
def brd_from_sch_path(schPath):
    return schPath.with_suffix(".kicad_pcb")

# For every subsheet in a sheet, we need to check if it has a pcb,
# if it does, the search ends there, the pcb is added to the list. 
# If not, it isnt in the list and, 
# we need to search every sub-sheet the same as step 1.


# A board always has a sheet
# A sheet doesn't always have a board
class SheetFile():
    def __init__(self, sheetPath: Path):
        
        if not isinstance(sheetPath, Path) :
            raise ValueError(f"Didn't get type pathlib.Path, instead got: {type(sheetPath)}")

        if not sheetPath.exists():
            raise FileNotFoundError("Base Board Sch. not found: " + str(schematicPath))
        
        self._sheetPath = sheetPath.resolve()
        self._sheet = sch_parse_file(sheetPath)
        self._uuid = self._sheet.get("uuid")
        self._boardPath = sheetPath.with_suffix(".kicad_pcb").resolve()

        self._board = None
        #Check Board Path
        if not self._boardPath.exists():
            logger.warn(f"{str(brdPath)} doesn't exist")
            return

        try:
            tmpBoard = pcbnew.LoadBoard(str(self._boardPath))
        except:
            logger.warn(f"{str(self._boardPath)} Board file invalid")
            return

        if len(tmpBoard.GetFootprints()) < 1:
            logger.warn(f"{str(self._boardPath)} Has no footprints")
            return

        logger.info(f"Valid Board found for {sheetPath}")
        self._board = tmpBoard

        # self.anchorFootprint
        # self.validAnchors
        # self.selectedAnchor

    def generate_subsheets(self, parentUUIDPath):

        subsheetList = self._sheet.get("sheet", {})

        logger.info(f"{len(subsheetList)} sheet instances entries in {self._sheetPath}")

        # first organize all the sheets by file, so that
        # sub sheets can share the same sheet data/pointer
        sortSubsheets = {}
        for subSheet in subsheetList:

            absFile = self._sheetPath.parent / subSheet["property"]["Sheetfile"]

            sortSubsheets.setdefault(absFile, [])
            sortSubsheets[absFile].append(subSheet)

        returnedList = []
        for sheetFile, subSheetList in sortSubsheets.items():
            sheetInfo = SheetFile(sheetFile)

            for subSheet in subsheetList:
                returnedList.append( SheetInstance(sheetInfo, subSheet, parentUUIDPath))

        logger.info(f"{len(subsheetList)} subsheets found for {self._sheetPath}")
        return returnedList

    def makeRootSheet(self):
        # The root board is gotten with pcbnew.GetBoard()
        # This also makes the root act like a branch instead of leaf
        self._board = None

    def save(self, cfg: ConfigMan):
        data = cfg.get("sheetByUUID")
        data[self._uuid] = self.anchorRef
        cfg.set("sheetByUUID", value=data)

    def load(self, cfg: ConfigMan):
        data = cfg.get("sheetByUUID")[self._uuid]

        if not boardData:
            logger.warn("boardData empty")
            return

        self.anchorRef = data

    @property
    def board(self):
        return self._board

class SheetInstance():
    def __init__(self, sheetData: SheetFile, subSheetDict: dict, parentUUIDPath: str):
        self._sheet = sheetData
        # Exclude the last two parameters if we are the root sheet.
        # It doesn't have a uuid or parent
        self._name = subSheetDict["property"]["Sheetname"]
        self._uuid = subSheetDict["uuid"]
        self._uuidPath = parentUUIDPath + "/" + self._uuid

        self._subSheets = sheetData.generate_subsheets(self._uuidPath)

    # Tri-state: -1 undefined, 0- none, 1- all
    def get_state(self):
        # Returns a True False or Neither
        if self._sheet.board:
            # Is a true or false because leaf
            return ConfigMan.get("enByUUID")[self._uuid]

        return False
        #Our state now depends entirely on children:
        # Checked if all children are checked
        # Semi-Checked if one child is checked
        # UnChecked if all children are unchecked
        #for subSheet in self._subSheets:
        #    if subSheet.check_state():
        #        continue

    def set_state(self, state: bool):
        oldData = ConfigMan.get("enByUUID")
        oldData[self._uuid] = state

    def ancestorHasValidBoard(self):
        if self._sheet.board:
            #We are a valid board, return true
            logger.info(f"Valid board for {self._uuid}")
            return True

        for subSheet in self._subSheets:
            if subSheet.ancestorHasValidBoard():
                logger.info(f"Valid child board for {self._uuid}")
                return True

        logger.info(f"No Valid Child board for {self._uuid}")
        return False
            

    def applyChildren(self):
        if self._sheet.board :
            # Schematics with a board actually replicate
            self.applyBoard()
        else:
            # Schematics without a board get a replicate signal
            # That they pass up the tree
            for subSheet in self._subSheets:
                subSheet.applyChildren()

    def applyBoard(self):
        """Enforce the positions of objects in PCB template on PCB mutate."""
        targetBoard = pcbnew.GetBoard()
        sourceBoard = self._sheet.board

        fpTranslator = FootprintTranslator(targetBoard, self._uuidPath)

        # TODO: Anchor on non-footprints?
        # Alternatives to anchor footprint:
        # Align centers: looses rotation
        # Find the anchor footprint on the PCBs:
        subPcbAnchor = sourceBoard.Footprints()[0]# self._sourceBoard.anchorFootprint
        subSheetAnchor = fpTranslator.getTarget(subPcbAnchor)

        if not subSheetAnchor:
            return

        replContext: ReplicateContext = ReplicateContext(subPcbAnchor, subSheetAnchor, self._uuid)

        # Clear Volatile items first
        clear_volatile_items(replContext.group)

        # First, move the footprints and create the net mapping:
        netMap = enforce_position_footprints(replContext, fpTranslator)

        # Recreate Volatile items:
        copy_drawings(replContext)
        copy_traces  (replContext, netMap)
        copy_zones   (replContext, netMap) 

        #Fixes issues with traces lingering after being deleted
        pcbnew.Refresh()

class RootInstance(SheetInstance):
    def __init__(self, sheetFile: SheetFile):
        sheetFile.makeRootSheet()
        self._sheet = sheetFile
        self._uuid = ""
        self._uuidPath = ""
        self._name = "Root"

        self._subSheets = sheetFile.generate_subsheets(self._uuidPath)





"""
class SubBoard:
    def __init__(self, mainSch, relPath, instanceList):

        self._board = subBoard
        self._validAnchors = [ fp.GetReferenceAsString() for fp in subBoard.GetFootprints() ]
        logger.debug(f"anchor count: {len(self._validAnchors)}")
        self.selectedAnchor = self._validAnchors[0]

        self.anchorFootprint = subBoard.FindFootprintByReference(self._selectedAnchor)

    @selectedAnchor.setter
    def selectedAnchor(self, value):
        if not self.isValid:
            return

        if value in self.validAnchors:
            self._selectedAnchor = value
        else:
            self._selectedAnchor = self.validAnchors[0]
            logger.warn("Not valid anchor: " + str(value))
        
        self.anchorFootprint = self.board.FindFootprintByReference(self._selectedAnchor)

    @property
    def enabledInstances(self):
        return [instance for instance in self._instances if instance.enabled]

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

def Tmp():
    def tmp():
        # The footprint has a uuid path, with the last uuid in the path
        # being the footprint's uuid. The last uuid is always the same
        # but the rest of the path changes between instances.

        name = instanceDict["property"]["Sheetname"]
        self._name = name

        self._targetBoard = targetBoard
        self._sourceBoard = sourceBoard

        self._enabled = False

    @property
    def enabled(self):
        return self._enabled
    
    @enabled.setter
    def enabled(self, value):
        self._enabled = value
"""