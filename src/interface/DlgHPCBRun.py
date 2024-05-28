import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import wx

from ..hdata import BaseSchData, SubPcb, PcbInstance
from .DlgHPCBRun_Base import DlgHPCBRun_Base

logger = logging.getLogger("hierpcb")


class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, parent: wx.Window, schData: BaseSchData):
        # Set up the user interface from the designer.
        super().__init__(parent)

        # Populate the dialog with data:
        self.schData = schData

        rootItem = self.treeApplyTo.GetRootItem()
        
        for subPcb in schData.subBoards.values():
            subPcbItem: wx.TreeListItem = self.treeApplyTo.AppendItem(
                parent=rootItem, text=str(subPcb._name), data=subPcb
            )

            for instance in subPcb._instances:
                instanceItem: wx.TreeListItem = self.treeApplyTo.AppendItem(
                    parent=subPcbItem, text=instance._name, data=instance
                )
                if instance.enabled:
                    self.treeApplyTo.CheckItem(instanceItem)
            
            self.treeApplyTo.Expand(subPcbItem)


    def getSelectedSubPCB(self) -> Optional[SubPcb]:
        selItem = self.treeApplyTo.GetSelection()
        instanceOrPcb = self.treeApplyTo.GetItemData(selItem)

        subPcb = None

        if isinstance(instanceOrPcb, PcbInstance):
            subPcb = instanceOrPcb._SubPcb
        elif isinstance(instanceOrPcb, SubPcb):
            subPcb = instanceOrPcb

        return subPcb

    def handleTreeCheck( self, event ):
        eventItem = event.GetItem()
        objData = self.treeApplyTo.GetItemData(eventItem)
        if isinstance(objData, SubPcb):
            # Toggle all children's state
            pass
        if isinstance(objData, PcbInstance):
            checked = self.treeApplyTo.GetCheckedState(eventItem)
            PcbInstance.enabled = (checked == 1)

    def handleSelectionChange( self, event ):
       subPcb = self.getSelectedSubPCB()
       self.anchorChoice.Clear()
       self.anchorChoice.AppendItems(subPcb.validAnchors)
       self.anchorChoice.SetSelection(subPcb.validAnchors.index(subPcb.selectedAnchor))

    def handleAnchorChange( self, event ):
        # Set the anchor:
        subpcb = self.getSelectedSubPCB()

        if subpcb is None:
            return

        # Get the selected anchor:
        sel = self.anchorChoice.GetSelection()
        sel_anchor = subpcb.validAnchors[sel]

        if sel == wx.NOT_FOUND:
            logger.warning("No anchor selected!")
            return

        subpcb.selectedAnchor = sel_anchor


    def handleApply(self, event):
        """Submit the form."""
        # Mutate the tree structure and
        self.EndModal(wx.ID_OK)
