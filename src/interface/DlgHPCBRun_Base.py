# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.1.0-0-g733bf3d-dirty)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.dataview
import wx.adv

###########################################################################
## Class DlgHPCBRun_Base
###########################################################################

class DlgHPCBRun_Base ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Project Instances", pos = wx.DefaultPosition, size = wx.Size( 465,766 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizerMain = wx.BoxSizer( wx.VERTICAL )

		self.treeApplyTo = wx.dataview.TreeListCtrl( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.dataview.TL_3STATE|wx.dataview.TL_CHECKBOX )
		self.treeApplyTo.AppendColumn( u"Choose which project instances to import:", wx.COL_WIDTH_DEFAULT, wx.ALIGN_LEFT, 0 )

		bSizerMain.Add( self.treeApplyTo, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText3 = wx.StaticText( self, wx.ID_ANY, u"Select Anchor:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText3.Wrap( -1 )

		bSizerMain.Add( self.m_staticText3, 0, wx.ALL|wx.EXPAND|wx.RIGHT, 5 )

		anchorChoiceChoices = []
		self.anchorChoice = wx.Choice( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( -1,-1 ), anchorChoiceChoices, 0 )
		self.anchorChoice.SetSelection( 0 )
		self.anchorChoice.SetMinSize( wx.Size( 999999,-1 ) )

		bSizerMain.Add( self.anchorChoice, 0, wx.ALL, 5 )

		bSizer2 = wx.BoxSizer( wx.HORIZONTAL )

		self.m_hyperlink1 = wx.adv.HyperlinkCtrl( self, wx.ID_ANY, u"Help", u"https://github.com/OfficialDyray/ProjectInstances/blob/master/README.md", wx.DefaultPosition, wx.DefaultSize, wx.adv.HL_DEFAULT_STYLE )
		bSizer2.Add( self.m_hyperlink1, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		m_sdbSizer1 = wx.StdDialogButtonSizer()
		self.m_sdbSizer1Apply = wx.Button( self, wx.ID_APPLY )
		m_sdbSizer1.AddButton( self.m_sdbSizer1Apply )
		self.m_sdbSizer1Cancel = wx.Button( self, wx.ID_CANCEL )
		m_sdbSizer1.AddButton( self.m_sdbSizer1Cancel )
		m_sdbSizer1.Realize();
		m_sdbSizer1.SetMinSize( wx.Size( -1,50 ) )

		bSizer2.Add( m_sdbSizer1, 8, wx.ALIGN_RIGHT, 5 )


		bSizerMain.Add( bSizer2, 0, wx.EXPAND, 5 )


		self.SetSizer( bSizerMain )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.treeApplyTo.Bind( wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.handleTreeCheck )
		self.treeApplyTo.Bind( wx.dataview.EVT_TREELIST_SELECTION_CHANGED, self.handleSelectionChange )
		self.anchorChoice.Bind( wx.EVT_CHOICE, self.handleAnchorChange )
		self.m_sdbSizer1Apply.Bind( wx.EVT_BUTTON, self.handleApply )

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def handleTreeCheck( self, event ):
		event.Skip()

	def handleSelectionChange( self, event ):
		event.Skip()

	def handleAnchorChange( self, event ):
		event.Skip()

	def handleApply( self, event ):
		event.Skip()