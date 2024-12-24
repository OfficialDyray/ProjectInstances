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

# Used to make sure every instance of a sheet is referencing the same data
class SheetFileManager():
    def __init__(self):
        self.sheetDict = {}
    
    def get_file_by_path(self, sheetPath: Path):
        if not self.sheetDict.get(sheetPath):
            # Sheet doesn't exist, create it
            self.sheetDict[sheetPath] = SheetFile(sheetPath)
        
        return self.sheetDict[sheetPath]
    
    def load_file_data(self, cfg: ConfigMan):
        for sheetFile  in self.sheetDict.values():
            sheetFile:SheetFile
            sheetFile.load(cfg)

    def save_file_data(self, cfg: ConfigMan):
        for sheetFile  in self.sheetDict.values():
            sheetFile:SheetFile
            sheetFile.save(cfg)

sheetFileManager = SheetFileManager()

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
        self._fpByRef =[]
        self._anchorRef = None

        #Check Board Path
        if not self._boardPath.exists():
            logger.warn(f"{str(self._boardPath)} doesn't exist")
            return

        try:
            board = pcbnew.LoadBoard(str(self._boardPath))
        except:
            logger.warn(f"{str(self._boardPath)} Board file invalid")
            return

        if len(board.GetFootprints()) < 1:
            logger.warn(f"{str(self._boardPath)} Has no footprints")
            return

        logger.info(f"Valid Board found for {sheetPath}")
        self._board = board
        self._fpByRef = [ fp.GetReferenceAsString() for fp in board.GetFootprints() ]
        
        # Default anchor as first footprint
        self._anchorRef = self.fpByRef[0]

    def generate_subsheets(self, parentUUIDPath):

        sheetInstanceList = self._sheet.get("sheet", {})

        logger.info(f"{len(sheetInstanceList)} sheet instances entries in {self._sheetPath}")

        returnedList = []
        for instanceData in sheetInstanceList:

            sheetPath = self._sheetPath.parent / instanceData["property"]["Sheetfile"]
            sheetPath.resolve()

            sheetInfo = sheetFileManager.get_file_by_path( sheetPath )

            returnedList.append( SheetInstance(sheetInfo, instanceData, parentUUIDPath))

        return returnedList

    def makeRootSheet(self):
        # The root board is gotten with pcbnew.GetBoard()
        # This also makes the root act like a branch instead of leaf
        self._board = None

    # Only Leaf SheetFiles need to save/load
    def save(self, cfg: ConfigMan):
        # BUG: When you copy a sheet, a new uuid is not generated
        # So selecting footprints will overwrite the other copies
        logger.debug(f"Saving anchor {self.anchorRef} for {self._sheetPath}") 
        cfg.set(self._uuid, value=self.anchorRef)

    def load(self, cfg: ConfigMan):
        savedRef = cfg.get(self._uuid)
        self.anchorRef = savedRef

    @property
    def board(self):
        return self._board

    @property
    def fpByRef(self):
        if not self.board:
            return None

        return self._fpByRef

    @property
    def anchorRef(self):
        return self._anchorRef

    @anchorRef.setter
    def anchorRef(self, value):
        if not self.board:
            return None

        if not value in self.fpByRef:
            self._anchorRef = self.fpByRef[0]
            logger.warn("New Anchor not found")
            return
        
        logger.info(f"Anchor changed to {value}")
        self._anchorRef = value


class SheetInstance():
    def __init__(self, sheetData: SheetFile, subSheetDict: dict, parentUUIDPath: str):
        self._sheet = sheetData
        self._enabled = False
        # Exclude the last two parameters if we are the root sheet.
        # It doesn't have a uuid or parent
        self._name = subSheetDict["property"]["Sheetname"]
        self._uuid = subSheetDict["uuid"]
        self._uuidPath = parentUUIDPath + "/" + self._uuid

        if not sheetData.board:
            self._subSheets = sheetData.generate_subsheets(self._uuidPath)

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

    # Only leaves need to save whether they are enabled or not
    def save(self, cfg: ConfigMan):
        if not self.sheetFile.board:
            for childInstance in self._subSheets:
                childInstance.save(cfg)
            return

        # BUG: When you copy a sheet, a new uuid is not generated
        # So selecting footprints will overwrite the other copies
        logger.debug(f"Saving info for {self._uuid}") 
        cfg.set(self._uuid, value=self.enabled)

    def load(self, cfg: ConfigMan):
        if not self.sheetFile.board:
            for childInstance in self._subSheets:
                childInstance.load(cfg)
            return

        savedEnabled = cfg.get(self._uuid, default=False)
        self.enabled = savedEnabled


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
        if not self.enabled:
            return

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

    @property
    def name(self):
        return self._name

    @property
    def sheetFile(self):
        return self._sheet

    # We only need to save enabled for leaves
    @property
    def enabled(self):
        if not self.sheetFile.board:
            return False

        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if not self.sheetFile.board:
            logger.warn(f"Tried to change enabled on nonleaf instance: {self._uuid}")
            return

        logger.info(f"Enabled leaf: {self._uuid}")
        self._enabled = value


class RootInstance(SheetInstance):
    def __init__(self, sheetFile: SheetFile):
        sheetFile.makeRootSheet()
        self._sheet = sheetFile
        self._uuid = ""
        self._uuidPath = ""
        self._name = "Root"

        self._subSheets = sheetFile.generate_subsheets(self._uuidPath)