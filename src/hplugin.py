import logging
import os
import pprint
import sys
import time
import traceback
from pathlib import Path

import pcbnew
import wx

from .cfgman import ConfigMan
from .hdata import BaseSchData
from .interface import DlgHPCBRun

logger = logging.getLogger("hierpcb")
logger.setLevel(logging.DEBUG)


class ProjectInstancesPlugin(pcbnew.ActionPlugin):
    def __init__(self):
        super().__init__()
        self.version = "0.0.1"

    def defaults(self):
        self.name = "ProjectInstances"
        self.category = "Layout"
        self.description = (
            "Import the schematics and pcb layout of another kicad project."
            "The schematics are imported through sheets, and pcb layout is"
            "imported through the use of this plugin."
        )
        self.icon_file_name = str(Path(__file__).parent / "icon.png")
        self.show_toolbar_button = True

    def Run(self):
        # grab PCB editor frame
        wx_frame = wx.FindWindowByName("PcbFrame")
        boardPath = Path(pcbnew.GetBoard().GetFileName())

        for lH in list(logger.handlers):
            logger.removeHandler(lH)
        logger.addHandler(
            logging.FileHandler(filename=boardPath.with_suffix(".projinst.log"), mode="w")
        )

        # set up logger
        logger.info(
            f"Plugin v{self.version} running on KiCad {pcbnew.GetBuildVersion()} and Python {sys.version} on {sys.platform}."
        )
        with ConfigMan(boardPath.with_suffix(".projinst.json")) as cfg:
            RunActual(cfg, wx_frame)


def RunActual(cfg, wx_frame: wx.Window):

    schData = BaseSchData(pcbnew.GetBoard())
    schData.load(cfg)

    if DlgHPCBRun(wx_frame, schData).ShowModal() == wx.ID_OK:
        schData.save(cfg)
        schData.replicate()
        logger.info("Saved.")
