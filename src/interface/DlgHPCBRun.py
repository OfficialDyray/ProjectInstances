import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import wx

from ..hdata import SheetInstance,RootInstance
from .DlgHPCBRun_Base import DlgHPCBRun_Base

logger = logging.getLogger("hierpcb")

def wxStateFromBool(inVal):
    match inVal:
        case False:
            return wx.CHK_UNCHECKED
        case True:
            return wx.CHK_CHECKED

class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, parent: wx.Window, rootInstance: RootInstance):
        # Set up the user interface from the designer.
        super().__init__(parent)

        rootItem = self.treeApplyTo.GetRootItem()
        logger.info(f"Root item: {rootItem}")
        self._buildTreeFromSubSheet(rootInstance, rootItem)

    def _buildTreeFromSubSheet(self, sheetInstance , parentItem):
        if not sheetInstance.ancestorHasValidBoard():
            # Not a branch ending in a leaf, end recursion
            # TODO: Add node anyways to help users know why it might not be working?
            logger.info(f"Instance is a dead branch: {sheetInstance._uuidPath}")
            return

        if sheetInstance._sheet.board:
            # This subsheet is a leaf
            logger.info(f"Instance is a leaf: {sheetInstance._uuidPath}")

            #Add leaf 
            instanceLeaf: wx.TreeListItem = self.treeApplyTo.PrependItem(
                parent=parentItem, text=str(sheetInstance._name), data=sheetInstance
            )
            self.treeApplyTo.Expand(instanceLeaf)
            checkState = wxStateFromBool(sheetInstance.enabled)
            self.treeApplyTo.CheckItem(instanceLeaf, checkState)
            self.treeApplyTo.UpdateItemParentStateRecursively(instanceLeaf)
            return

        # This subsheet is a branch
        logger.info(f"Instance is a branch: {sheetInstance._name}")
        # Add Branch
        instanceBranch: wx.TreeListItem = self.treeApplyTo.PrependItem(
            parent=parentItem, text=str(sheetInstance._name), data=sheetInstance
        )
        self.treeApplyTo.Expand(instanceBranch)
        # Impliment branch checkbox later
        #checkState = wxStateFromTri(subPcb.getStateFromInstances())
        #self.treeApplyTo.CheckItem(subSheetBranch, checkState)

        # Populate with leaves/branches
        for sheetInstanceIt in sheetInstance._subSheets:
            self._buildTreeFromSubSheet(sheetInstanceIt, instanceBranch)

    def getSelectedInstance(self) -> Optional[SheetInstance]:
        selItem = self.treeApplyTo.GetSelection()
        instance = self.treeApplyTo.GetItemData(selItem)

        if not isinstance(instance, SheetInstance):
            return None

        return instance

    def handleTreeCheck( self, event ):
        eventItem = event.GetItem()
        objData = self.treeApplyTo.GetItemData(eventItem)

        if not isinstance(objData, SheetInstance):
            return

        if objData._sheet.board:
            # We are a leaf
            state = self.treeApplyTo.GetCheckedState(eventItem)
            boolState = (state == wx.CHK_CHECKED)
            objData.enabled = boolState

        else:
            # A branch has changed, recursively apply to leaves
            state = self.treeApplyTo.GetCheckedState(eventItem)
            # This doesn't trigger a leaf change..
            self.treeApplyTo.CheckItemRecursively(eventItem, state)

            # Force sync the tree to instace data
            self.syncTreeDataToInstances()

        self.treeApplyTo.UpdateItemParentStateRecursively(eventItem)

    def syncTreeDataToInstances(self):
        item = self.treeApplyTo.GetFirstItem()
        while item.IsOk():
            itemData =self.treeApplyTo.GetItemData(item) 
            if not isinstance(itemData, SheetInstance):
                item = self.treeApplyTo.GetNextItem(item)
                continue
            if not itemData._sheet.board:
                item = self.treeApplyTo.GetNextItem(item)
                continue

            state = self.treeApplyTo.GetCheckedState(item) == wx.CHK_CHECKED
            itemData.enabled = state
            item = self.treeApplyTo.GetNextItem(item)

    def handleSelectionChange( self, event ):
        self.anchorChoice.Clear()

        selInstance: SheetInstance = self.getSelectedInstance()
        if selInstance is None:
            logger.warn("Selected Subpcb returned none")
            return

        selSheetFile = selInstance.sheetFile
        if not selSheetFile.board:
            return 

        logger.info(f"subPcb selected {selInstance._name} with {len(selSheetFile.fpByRef)} anchors")
        self.anchorChoice.AppendItems(selSheetFile.fpByRef)
        self.anchorChoice.SetSelection(selSheetFile.fpByRef.index(selSheetFile.anchorRef))

    def handleAnchorChange( self, event ):
        # Set the anchor:
        selInstance: SheetInstance = self.getSelectedInstance()

        if selInstance is None:
            return

        selSheetFile = selInstance.sheetFile
        # Get the selected anchor:
        sel = self.anchorChoice.GetSelection()
        
        if sel == wx.NOT_FOUND:
            logger.warning("No anchor selected!")
            return
        
        selAnchor = selSheetFile.fpByRef[sel]
        logger.info(f"Anchor changed to {selAnchor} on {selSheetFile._sheetPath}")
        selSheetFile.anchorRef = selAnchor

    def handleApply(self, event):
        """Submit the form."""
        # Mutate the tree structure and
        self.EndModal(wx.ID_OK)