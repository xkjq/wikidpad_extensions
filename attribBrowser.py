import wx
import threading

WIKIDPAD_PLUGIN = (("MenuFunctions",1),)

def describeMenuItems(wiki):
        return ((AttribBrowser, "Attribute Browser\tCtrl-Alt-B", "Tool for browsing attributes"),)

class ResultsList(wx.HtmlListBox):
    def __init__(self, parent, pWiki):
        wx.HtmlListBox.__init__(self, parent, -1)

        self.pWiki = pWiki

        self.parent = parent

        wx.EVT_LISTBOX_DCLICK(self, -1, self.OnDClick)

    def SetResults(self, results):
        self.results = results

        self.Refresh()

    def OnGetItem(self, n):
        wikipage, attrib, value = self.results[n]


        return "<table><tr><td bgcolor='lightblue' width='6'></td><td><font color='black'><u>{0}</u>:  {1} </font><font color='gray'>({2})</font></td></tr></table>".format(wikipage, value, attrib)


    def GetCount(self):
        return len(self.results)

    def OnDClick(self, evt):
        sel = self.GetSelection()

        if sel == -1 or self.GetCount() == 0:
            return

        wikiWord, attrib, value = self.results[sel]
        self.pWiki.openWikiPage(wikiWord)


class AttribBrowserDialog(wx.Dialog):
    def __init__(self, pWiki, id=wx.ID_ANY, title="Attribute Browser"):
        wx.Dialog.__init__(self, pWiki, id, title, 
                style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.pWiki = pWiki

        search_attrib = wx.TextCtrl(self, -1)
        search_attrib_text = wx.StaticText(self, -1, "Attribute")

        search_value = wx.TextCtrl(self, -1)
        search_value_text = wx.StaticText(self, -1, "Key Value")

        search_children_checkbox = wx.CheckBox(self, -1, 
                "Search Child Attributes")
        self.search_children_checkbox = search_children_checkbox

        search_terms_sizer = wx.GridSizer(rows=2, cols=2, hgap=1)

        search_terms_sizer.AddMany([
                (search_attrib_text, 0, wx.EXPAND), 
                (search_attrib, 0, wx.EXPAND), 
                (search_value_text, 0, wx.EXPAND), 
                (search_value, 0, wx.EXPAND), 
                ])

        results_box = ResultsList(self, pWiki)

        self.results_box = results_box

        btnFind = wx.Button(self, label="&Search", id=wx.ID_FIND)
        btnCancel = wx.Button(self, label="&Cancel", id=wx.ID_CANCEL)

        buttons = wx.BoxSizer(wx.HORIZONTAL)

        buttons.Add(btnFind)
        buttons.Add(btnCancel)

        btnFind.Bind(wx.EVT_BUTTON, self.OnSearch)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnClose)

        btnFind.SetDefault()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(results_box, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(search_terms_sizer, 0, wx.HORIZONTAL|wx.EXPAND, 5)
        sizer.Add(search_children_checkbox, 0, wx.HORIZONTAL|wx.EXPAND, 5)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizerAndFit(sizer)
        self.SetSize((200, 400))

        search_attrib.SetFocus()

        self.search_attrib = search_attrib
        self.search_value = search_value

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def OnKeyDown(self, evt):
        self.OnClose()

    def OnSearch(self, evt):
        search_attrib_string = self.search_attrib.GetValue()
        search_value_string = self.search_value.GetValue()
        search_attrib_children = self.search_children_checkbox.GetValue()

        if not search_attrib_string and not search_value_string:
            return

        if not search_attrib_string:
            search_attrib_string = None

        if not search_value_string:
            search_value_string = None


        t = threading.Thread(target=self.Search, args=(search_attrib_string, search_value_string, search_attrib_children))

        self.SetTitle("Searching")
        self.results_box.SetItemCount(0)

        t.start()

    def LoadResults(self):

        results = []

        for i in self.results:
            results.append(i)

        self.results_box.SetResults(results)

        self.results_box.SetItemCount(len(results))

        self.SetTitle("Found {0} matches".format(len(results)))


    def Search(self, search_attrib_string, search_value_string, search_attrib_children):
        attribs_to_search = [search_attrib_string]
        if search_attrib_string is not None and search_attrib_children:
            attribs_to_search.extend(self.pWiki.getWikiDocument().\
                    getAttributeNamesStartingWith(
                            "{0}.".format(search_attrib_string)))

        
        attrib_list = []
        for search_attrib in attribs_to_search:
            attrib_list.extend(
                    self.pWiki.getWikiDocument().getAttributeTriples(
                            None, search_attrib, search_value_string))
            

        if not attrib_list or attrib_list is None:
            wx.CallAfter(self.SetTitle, "No Results")
            return

        self.results = attrib_list
        wx.CallAfter(self.LoadResults)


    def OnClose(self, evt=None):
        self.Destroy()


def AttribBrowser(pWiki, evt):
    browser = AttribBrowserDialog(pWiki)
    browser.Show()
