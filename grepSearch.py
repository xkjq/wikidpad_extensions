import os, wx, subprocess, re
from collections import defaultdict
from urllib2 import unquote
import threading

WIKIDPAD_PLUGIN = (("MenuFunctions",1),)

def describeMenuItems(wiki):
        global nextnumber
        return ((Grep, "Grep Search\tCtrl-Shift-F", "Search with Grep"),)

class ResultsList(wx.HtmlListBox):
    def __init__(self, parent, pWiki):
        wx.HtmlListBox.__init__(self, parent, -1)

        self.pWiki = pWiki

        self.parent = parent

        wx.EVT_LISTBOX_DCLICK(self, -1, self.OnDClick)

    def SetResults(self, results, results_count):
        self.results = results
        self.results_count = results_count

        self.Refresh()

    def OnGetItem(self, n):
        wikipage, line, string = self.results[n]

        if line is None: # Header
            return "<table><tr><td width=100%></td></tr></table><table><tr><td bgcolor='blue' width='6'></td><td><font color='blue'><b>{0} <u>({1})</u></b></font></td></tr></table>".format(wikipage, self.results_count[wikipage])

        return "<table><tr><td bgcolor='lightblue' width='6'></td><td><font color='black'><u>Line {0}</u> - {1}</font></td></tr></table>".format(line, string)


    def GetCount(self):
        return len(self.results)

    def OnDClick(self, evt):
        sel = self.GetSelection()

        if sel == -1 or self.GetCount() == 0:
            return



        wikiWord, line, string = self.results[sel]
        self.pWiki.openWikiPage(wikiWord)

        # TODO: check editor state and goto line
        if line:
            l = int(line)
            editor = self.pWiki.getActiveEditor()

            if editor is not None:
                #editor.SetCurrentPos(0)
                #editor.SetAnchor(0)

                editor.GotoLine(l-1)
                #print self.parent.search_string

                editor.SearchAnchor()
                editor.SearchNext(wx.stc.STC_FIND_REGEXP, self.parent.search_string) 
                #editor.SetCaretLineVisible(True) 
                #editor.SetCaretLineBack("red") 


class GrepDialog(wx.Dialog):
    def __init__(self, pWiki, id=wx.ID_ANY, title="Grep Search"):
        wx.Dialog.__init__(self, pWiki, id, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.pWiki = pWiki

        search_box = wx.TextCtrl(self, -1)
        pre_search_box = wx.TextCtrl(self, -1)

        results_box = ResultsList(self, pWiki)
        #results_box.SetItemCount(0)
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
        sizer.Add(search_box, 0, wx.HORIZONTAL|wx.EXPAND, 5)
        sizer.Add(pre_search_box, 0, wx.HORIZONTAL|wx.EXPAND, 5)
        sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizerAndFit(sizer)
        self.SetSize((200, 400))

        search_box.SetFocus()

        self.search_box = search_box
        self.pre_search_box = pre_search_box

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def OnKeyDown(self, evt):
        self.OnClose()

    def OnSearch(self, evt):
        search_string = self.search_box.GetValue()

        if not search_string:
            return

        self.search_string = search_string

        data_dir = self.pWiki.dataDir

        self.data_dir = data_dir

        pre_search = self.pre_search_box.GetValue()


        t = threading.Thread(target=self.Search, args=(search_string, data_dir, pre_search))

        self.SetTitle("Searching for: {0}".format(self.search_box.GetValue()))
        self.results_box.SetItemCount(0)

        t.start()

        #t.join()

    def LoadResults(self):
        
        results = []
        pages = set()

        results_count = defaultdict(int)

        l = len(self.data_dir) + 1


        for i in self.results.split("\n")[:-1]:
            wikipage, line, context_string = i.split(":", 2)
            wikipage = unquote(wikipage[l:-5])
            if wikipage not in pages:
                results.append((wikipage, None, None))
                pages.add(wikipage)

            results_count[wikipage] += 1

            context_string = re.sub(r"({0})".format(self.search_string), r"<font color='red'>\1</font>", context_string, flags=re.IGNORECASE)
            results.append((wikipage, line, context_string))

        self.results_box.SetResults(results, results_count)

        self.results_box.SetItemCount(len(results))

        number_results = sum([results_count[i] for i in results_count])

        self.SetTitle("Found {0} matches (on {1} pages)".format(number_results, len(results_count)))

    def Search(self, search_string, data_dir, pre_search=""):
        #self.Refresh()

        search_cmd = os.path.join(data_dir, "".join([pre_search, "*.wiki"]))

        try:
            ret = subprocess.check_output('grep -ni "{0}" {1}'.format(search_string, search_cmd), shell=True)
        except:
            # No results
            wx.CallAfter(self.SetTitle,"No Results")
            return

        self.results = ret
        wx.CallAfter(self.LoadResults)

    def OnClose(self, evt=None):
        #self.Show(False)
        self.Destroy()




def Grep(pWiki, evt):

    search = GrepDialog(pWiki)
    search.Show()
