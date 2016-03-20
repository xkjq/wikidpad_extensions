#######################################################################
# WikidMap - v0.4
# 
# Plugin that uses sigma.js to display a simple mindmap of wikipages
# directly related to the currently opened page.
#
# This is still a test release and as such some things will not
# work / may change in the future.
#
# Requries wxPython 2.9 or above (it needs a working html2 
# implementation)
#
#######################################################################
import os

import wx
import wx.html2

import json

from collections import defaultdict

import random

from lib.pwiki.StringOps import flexibleUrlUnquote

WIKIDPAD_PLUGIN = (("MenuFunctions",1),)


def describeMenuItems(wiki):
    return ((mindMap, "Display WikidMap'\tCtrl-Shift-M", 
                            "Display a map of interlinking pages"),)


class DrawFrame(wx.Frame):
    """
    A frame used for the mindmap

    """
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        self.CreateStatusBar()

        # Add the html2 element
        self.html = wx.html2.WebView.New(self)

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.html, 1, wx.EXPAND)
        self.SetSizer(self.box)

        try:
            self.Bind(wx.html2.EVT_WEB_VIEW_NAVIGATING, self.OnPageNavigation, 
                    self.html)

        #    self.Bind(wx.html2.EVT_WEB_VIEW_LOADED, self.OnPageLoaded, 
        #            self.html)
        # wxPython 2.9.5 renames the webview part
        except AttributeError:
            self.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self.OnPageNavigation, 
                    self.html)

        #    self.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.OnPageLoaded, 
        #            self.html)

        tb = self.CreateToolBar()

        depth_text = wx.StaticText(tb, -1, "Search Depth")#, (30, 50), (60, -1))
        
        depthCtrl = wx.SpinButton(tb, -1, (50, 0), (50, 20))
        depthCtrl.SetRange(1, 50)
        depthCtrl.SetValue(3)

        self.depth_control = depthCtrl


        tb.AddControl(depth_text)
        tb.AddControl(depthCtrl)

        tb.AddSeparator()

        truncate_depth_text = wx.StaticText(tb, -1, "Trucate Depth")#, (30, 50), (60, -1))
        
        truncate_depthCtrl = wx.SpinButton(tb, -1, (50, 0), (50, 20))
        truncate_depthCtrl.SetRange(2, 50)
        truncate_depthCtrl.SetValue(2)

        self.truncate_depth_control = truncate_depthCtrl

        tb.AddControl(truncate_depth_text)
        tb.AddControl(truncate_depthCtrl)

        tb.AddSeparator()

        truncate_number_text = wx.StaticText(tb, -1, "Trucate Number")#, (30, 50), (60, -1))
        
        truncate_numberCtrl = wx.SpinButton(tb, -1, (50, 0), (50, 20))
        truncate_numberCtrl.SetRange(1, 50)
        truncate_numberCtrl.SetValue(8)

        self.truncate_number_control = truncate_numberCtrl

        tb.AddControl(truncate_number_text)
        tb.AddControl(truncate_numberCtrl)
        #StopButton.Bind(wx.EVT_BUTTON, self.PauseLoading)

        RefreshButton = wx.Button(tb, wx.ID_ANY, u"Refresh")
        tb.AddControl(RefreshButton)
        RefreshButton.Bind(wx.EVT_BUTTON, self.BuildData)

        ReloadButton = wx.Button(tb, wx.ID_ANY, u"Reload")
        tb.AddControl(ReloadButton)
        ReloadButton.Bind(wx.EVT_BUTTON, self.LoadRelations)

        StartForceButton = wx.Button(tb, wx.ID_ANY, u"StartForce")
        tb.AddControl(StartForceButton)
        StartForceButton.Bind(wx.EVT_BUTTON, self.StartForce)

        StopForceButton = wx.Button(tb, wx.ID_ANY, u"StopForce")
        tb.AddControl(StopForceButton)
        StopForceButton.Bind(wx.EVT_BUTTON, self.StopForce)

        tb.Realize()

        return None


    def SetPWiki(self, pWiki):
        self.pWiki = pWiki


    def LoadRelations(self, evt=None):
        editor = self.pWiki.getActiveEditor()

        # getAllRelations probably doesn't exist
        try:
            relations = editor.getMainControl().getWikiData().getAllRelations()
        except:
            print dir(editor.getMainControl().getWikiData().connWrap)
            relations = editor.getMainControl().getWikiData().wikiData.connWrap.execSqlQuery(
                "select word, relation from wikirelations")

        # Create an dict of words and the relations

        self.children = defaultdict(set)
        self.parents = defaultdict(set)

        for source, target in relations:
            self.children[source].add(target)
            self.parents[target].add(source)


        self.BuildData()


    def BuildData(self, evt=None):

        nodes = list()

        links = list()

        nodes_to_make = set()

        # Search for nodes from active page

        search_depth = self.depth_control.GetValue()

        active_nodes = {}
        additional_nodes = set()
        nodes_to_process = set([self.start_page])

        nodes_fully_searched = set()
        nodes_truncated = set()

        children = self.children
        parents = self.parents

        truncate_node_depth = self.truncate_depth_control.GetValue()
        truncate_node_no = self.truncate_number_control.GetValue()


        d = 0
        n = 0

        while d < search_depth:
            d = d + 1

            for page in nodes_to_process:
                if page in active_nodes:
                    continue

                active_nodes[page] = {
                    "id" : page,
                    "label" : page,
                    "x" : random.randint(1, 10),
                    "y" : random.randint(1, 10),
                    "size" : 3,
                }


                # Find all children and parents
                c = children[page]
                p = parents[page]

                if d > 1 and d >= truncate_node_depth and len(c) >= truncate_node_no:
                    active_nodes[page]["color"] = "black"
                    nodes_truncated.add(page)
                    continue
                else:
                    nodes_to_process = nodes_to_process.union(c)
                    nodes_to_process = nodes_to_process.union(p)
                    nodes_fully_searched.add(page)

                for i in c:
                    n = n + 1
                    links.append({
                        "id" : n,
                        "source" : page,
                        "target" : i,
                        })
                    additional_nodes.add(page)
                    additional_nodes.add(i)

        # Create links from truncated nodes

        for page in nodes_truncated:
            c = children[page]
            for i in c:
                # If our target has been created add a link
                if i in nodes_to_process or i in additional_nodes:
                    n = n + 1
                    links.append({
                        "id" : n,
                        "source" : page,
                        "target" : i,
                        })
                    additional_nodes.add(page)
                    additional_nodes.add(i)

        #nodes_to_create = active_nodes.union(additional_nodes)
        for page in additional_nodes:
            if page not in active_nodes:
                active_nodes[page] = {
                    "id" : page,
                    "label" : page,
                    "x" : random.randint(1, 10),
                    "y" : random.randint(1, 10),
                    "size" : 3,
                }

        active_nodes[self.start_page]["color"] = "blue"

        orphan_nodes = nodes_fully_searched.union(nodes_truncated)

        for n in active_nodes:
            if n not in (orphan_nodes):
                active_nodes[n]["color"] = "grey"
            nodes.append(active_nodes[n])

        d = { "nodes" : nodes, "edges" : links }
        j = json.dumps(d, sort_keys=True, indent=4, separators=(',', ': '))
        #print(j)

        with open(os.path.join("user_extensions", "map", "data.js"), "w") as f:
            f.write("g = {0}".format(j))

        #self.html.Reload(wx.html2.WEBVIEW_RELOAD_NO_CACHE)

        self.SetStatusText("Map from page [{0}] loaded. Search depth [{1}], Trucate depth [{2}], Trucate no. [{3}]".format(self.start_page, search_depth, truncate_node_depth, truncate_node_no))

        #wx.CallAfter(self.html.RunScript,"setTimeout(function(){document.location.reload(true);}, 100);")


# This is pulled direct from WikiHtmlView2
    def OnPageNavigation(self, evt):
        # TODO: make extendable - for plugins + VI mode
        uri = flexibleUrlUnquote(evt.GetURL())

        if uri.endswith("map.html"):
            return

        self.html.RunScript(r"""event_str = false;""")


        leader = "http://internaljump/"

        if uri.startswith(leader):
            page = uri[len(leader):]
            self.pWiki.openWikiPage(page)
            self.start_page = page
            self.BuildData()
            evt.Veto()
            return

        # This can lead to an event being vetoed multiple times
        # (which should not be an issue)
        r = False
        for split_uri in uri.split("//PROXY_EVENT_SEPERATOR//"):
            event_return = self.HandleProxyEvent(evt, split_uri)
            if event_return:
                r = True

        if r:
            return 



    # Not used (at present)
    def HandleProxyEvent(self, evt, uri):
        """
        Helper to handle custom events

        @param evt: The wxPython navigation event
        @param uri: The PROXY_EVENT uri 

        @rtype: bool
        @return: True if the event has been vetoed and the link
                    should not be activated.
        """

#        if uri.endswith("PROXY_EVENT//JQUERY_LOADED"):
#            self.OnJqueryLoaded()
#            evt.Veto()
#            return True
        if "PROXY_EVENT//MOUSE_CLICK" in uri:
            if not uri.endswith("KEEP_FOCUS"):
                self.presenter.makeCurrent()
            evt.Veto()
            return True
        elif "PROXY_EVENT//MOUSE_RIGHT_CLICK" in uri:
            self.OnContextMenu()
            evt.Veto()
            return True
        elif "PROXY_EVENT//MOUSE_MIDDLE_CLICK" in uri:
            ctrl = uri.split("PROXY_EVENT//MOUSE_MIDDLE_CLICK/")[1]

            if ctrl == "TRUE":
                ctrlDown = True
            else:
                ctrlDown = False

            self.OnMiddleDown(controlDown=ctrlDown)
            evt.Veto()
            return True
        # Check if it is a link hover event
        elif "PROXY_EVENT//HOVER_START/" in uri:
            link = uri.split("PROXY_EVENT//HOVER_START/")[1]
            self.contextHref = link
            self.updateStatus(link)
            evt.Veto()
            return True
        elif "PROXY_EVENT//HOVER_END/" in uri:
            self.contextHref = None
            self.updateStatus(None)
            evt.Veto()
            return True

        return False


    def SetCurrentPage(self, page):
        self.start_page = page


    def StartForce(self, evt):
        self.html.RunScript("s.startForceAtlas2({worker: false, barnesHutOptimize: false});")

    def StopForce(self, evt):
        self.html.RunScript("s.stopForceAtlas2();")

    def DrawMindmap(self, start_page=None):
        print u"Building mindmap"

        if start_page is None:
            self.SetCurrentPage(self.pWiki.getCurrentWikiWord())
        else:
            self.start_page = start_page

        self.LoadRelations()

        wx.CallAfter(self.html.LoadURL,"file:{0}".format(os.path.join(self.pWiki.wikiAppDir, "user_extensions", "map", "map.html")))

        #self.html.RunScript(" setTimeout(function(){document.location.reload(true);}, 100);")

        #self.html.Reload(wx.html2.WEBVIEW_RELOAD_NO_CACHE)


    def CheckIsWikiWord(self, node):
        node.Page_Exists = self.pWiki.getWikiDocument().isDefinedWikiLinkTerm(node.Name)



def mindMap(pwiki, evt):
    #mapApp = wx.App(False)
    m = DrawFrame(None, -1, u"WikidMap", wx.DefaultPosition, (700,700) )
    m.Show()
    m.SetPWiki(pwiki)
    m.DrawMindmap()
