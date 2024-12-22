import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import wx

from ..hdata import SheetInstance,RootInstance
from .DlgHPCBRun_Base import DlgHPCBRun_Base

logger = logging.getLogger("hierpcb")

def wxStateFromTri(int):
    match int:
        case -1:
            return wx.CHK_UNDETERMINED
        case 0:
            return wx.CHK_UNCHECKED
        case 1:
            return wx.CHK_CHECKED

class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, parent: wx.Window, rootInstance: RootInstance):
        # Set up the user interface from the designer.
        super().__init__(parent)

        rootItem = self.treeApplyTo.GetRootItem()
        logger.info(f"Root item: {rootItem}")
        self.buildTreeFromSubSheet(rootInstance, rootItem)

            # #Show invalid pcbs
            # if not subPcb.isValid:
            #     invalidText = f"{subPcb._name} INVALID!"
            #     subPcbItem: wx.TreeListItem = self.treeApplyTo.AppendItem(
            #         parent=rootItem, text=invalidText, data=subPcb
            #     )
            #     continue
            
            # # Populate subpcb instances
            # for instance in subPcb._instances:
            #     instanceItem: wx.TreeListItem = self.treeApplyTo.AppendItem(
            #         parent=subPcbItem, text=instance._name, data=instance
            #     )
            #     if instance.enabled:
            #         self.treeApplyTo.CheckItem(instanceItem)
            
            # self.treeApplyTo.Expand(subPcbItem)

    def buildTreeFromSubSheet(self, sheetInstance , parentItem):
        if not sheetInstance.ancestorHasValidBoard():
            # Not a branch ending in a leaf, end recursion
            logger.info(f"Instance is a dead branch: {sheetInstance._uuidPath}")
            return

        if sheetInstance._sheet.board:
            # This subsheet is a leaf
            logger.info(f"Instance is a leaf: {sheetInstance._uuidPath}")

            #Add leaf 
            subSheetLeaf: wx.TreeListItem = self.treeApplyTo.PrependItem(
                parent=parentItem, text=str(sheetInstance._name), data=sheetInstance
            )
            #checkState = wxStateFromTri(subPcb.getStateFromInstances())
            #self.treeApplyTo.CheckItem(subPcbItem, checkState)
            return

        # This subsheet is a branch
        logger.info(f"Instance is a branch: {sheetInstance._name}")
        # Add Branch
        subSheetBranch: wx.TreeListItem = self.treeApplyTo.PrependItem(
            parent=parentItem, text=str(sheetInstance._name), data=sheetInstance
        )
        # Impliment branch checkbox later
        #checkState = wxStateFromTri(subPcb.getStateFromInstances())
        #self.treeApplyTo.CheckItem(subSheetBranch, checkState)

        # Populate with leaves/branches
        for sheetInstanceIt in sheetInstance._subSheets:
            self.buildTreeFromSubSheet(sheetInstanceIt, subSheetBranch)

    # def getSelectedSubPCB(self) -> Optional[SubBoard]:
    #     selItem = self.treeApplyTo.GetSelection()
    #     instanceOrPcb = self.treeApplyTo.GetItemData(selItem)

    #     subPcb = None

    #     if isinstance(instanceOrPcb, SheetInstance):
    #         subPcb = instanceOrPcb._SubPcb
    #     elif isinstance(instanceOrPcb, SubBoard):
    #         subPcb = instanceOrPcb

    #     return subPcb

    def handleTreeCheck( self, event ):
        eventItem = event.GetItem()
        objData = self.treeApplyTo.GetItemData(eventItem)

        if isinstance(objData, SheetInstance):
            if objData._sheet.board:
                # Toggle all children's state
                state = self.treeApplyTo.GetCheckedState(eventItem)
                boolState = (state == wx.CHK_CHECKED)
                objData.setInstancesState(boolState)
            #self.treeApplyTo.CheckItemRecursively(eventItem, state)

        #elif isinstance(objData, SheetInstance):
            #Set Instance State
            #state = self.treeApplyTo.GetCheckedState(eventItem)
            #objData.enabled = (state == wx.CHK_CHECKED)

            #Update parent tri state
            #parent = self.treeApplyTo.GetItemParent(eventItem)

            #parentSubpcb = self.treeApplyTo.GetItemData(parent)
            #checkState = wxStateFromTri(parentSubpcb.getStateFromInstances())
            #self.treeApplyTo.CheckItem(parent, checkState)

    # def handleSelectionChange( self, event ):
    #     subPcb = self.getSelectedSubPCB()
    #     self.anchorChoice.Clear()

    #     if subPcb is None:
    #         logger.warn("Selected Subpcb returned none")
    #         return
    #     if not subPcb.isValid:
    #         logger.debug(f"invalid subPcb selected {subPcb._name}")
    #         return

    #     logger.debug(f"subPcb selected {subPcb._name} with {len(subPcb.validAnchors)} anchors")
    #     self.anchorChoice.AppendItems(subPcb.validAnchors)
    #     if subPcb.selectedAnchor in subPcb.validAnchors:
    #         self.anchorChoice.SetSelection(subPcb.validAnchors.index(subPcb.selectedAnchor))

    # def handleAnchorChange( self, event ):
    #     # Set the anchor:
    #     subpcb = self.getSelectedSubPCB()

    #     if subpcb is None:
    #         return
    #     if not subpcb.isValid:
    #         return

    #     # Get the selected anchor:
    #     sel = self.anchorChoice.GetSelection()
        
    #     if sel == wx.NOT_FOUND:
    #         logger.warning("No anchor selected!")
    #         return
        
    #     selAnchor = subpcb.validAnchors[sel]
    #     subpcb.selectedAnchor = selAnchor

    def handleApply(self, event):
        """Submit the form."""
        # Mutate the tree structure and
        self.EndModal(wx.ID_OK)