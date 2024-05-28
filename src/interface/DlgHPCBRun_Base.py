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

###########################################################################
## Class DlgHPCBRun_Base
###########################################################################

class DlgHPCBRun_Base ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"HierarchicalPCB", pos = wx.DefaultPosition, size = wx.Size( 465,766 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizerMain = wx.BoxSizer( wx.VERTICAL )

		self.m_staticText1 = wx.StaticText( self, wx.ID_ANY, u"Choose which sub-PCB layouts to apply:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText1.Wrap( -1 )

		bSizerMain.Add( self.m_staticText1, 0, wx.ALL, 5 )

		self.treeApplyTo = wx.dataview.TreeListCtrl( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.dataview.TL_3STATE|wx.dataview.TL_CHECKBOX )
		self.treeApplyTo.AppendColumn( u"Column1", wx.COL_WIDTH_DEFAULT, wx.ALIGN_LEFT, 0 )

		bSizerMain.Add( self.treeApplyTo, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText3 = wx.StaticText( self, wx.ID_ANY, u"Select Anchor", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText3.Wrap( -1 )

		bSizerMain.Add( self.m_staticText3, 0, wx.ALL|wx.EXPAND|wx.RIGHT, 5 )

		anchorChoiceChoices = []
		self.anchorChoice = wx.Choice( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( -1,-1 ), anchorChoiceChoices, 0 )
		self.anchorChoice.SetSelection( 0 )
		self.anchorChoice.SetMinSize( wx.Size( 999999,-1 ) )

		bSizerMain.Add( self.anchorChoice, 0, wx.ALL, 5 )

		m_sdbSizer1 = wx.StdDialogButtonSizer()
		self.m_sdbSizer1Apply = wx.Button( self, wx.ID_APPLY )
		m_sdbSizer1.AddButton( self.m_sdbSizer1Apply )
		self.m_sdbSizer1Cancel = wx.Button( self, wx.ID_CANCEL )
		m_sdbSizer1.AddButton( self.m_sdbSizer1Cancel )
		self.m_sdbSizer1Help = wx.Button( self, wx.ID_HELP )
		m_sdbSizer1.AddButton( self.m_sdbSizer1Help )
		m_sdbSizer1.Realize();
		m_sdbSizer1.SetMinSize( wx.Size( -1,50 ) )

		bSizerMain.Add( m_sdbSizer1, 0, wx.EXPAND, 5 )


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