import json
import requests
from bs4 import BeautifulSoup
import threading
import tkinter as tk
import tkinter.tix as tix
import re
from .PluginAPI.PluginAPI import PluginApi
import importlib
import os
import traceback

import tkinter as tk

class ToolTip:
    def __init__(self, widget, text="", delay_ms=600):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms          # hover delay in milliseconds
        self.tip_window = None
        self.after_id = None              # to cancel the delayed show

        # Bind events
        self.widget.bind("<Enter>", self._schedule_show)
        self.widget.bind("<Leave>", self._cancel_and_hide)
        self.widget.bind("<ButtonPress>", self._cancel_and_hide)  # hide immediately on click

    def _schedule_show(self, event=None):
        """Schedule tooltip to appear after delay"""
        self._cancel()  # cancel any previous pending show
        if not self.text:
            return
        self.after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self):
        """Actually display the tooltip"""
        self.after_id = None
        if self.tip_window:  # already shown
            return

        # Position: a bit right and below the widget
        x = self.widget.winfo_rootx() + 28
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)          # no title bar / borders
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)    # stay on top (optional)

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "10", "normal"), padx=6, pady=4)
        label.pack()

    def _cancel_and_hide(self, event=None):
        """Cancel pending show and hide existing tooltip"""
        self._cancel()
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def _cancel(self):
        """Cancel any scheduled tooltip appearance"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
            

context = {"HelpMSG": """Hello! Welcome to MARSCT (MuZe's Arma Reforger Server Config Tool)!
This is a way to help you do mods. It'll give you everything to put
in the "mods":[] <---- area
--------
KEYBINDS
--------
(Ctrl + F1) or (Ctrl + Help) - Gives you this menu.
(Ctrl + Z) - Undo - Undoes an action
(Ctrl + Y) - Redo - Redoes an action
(Ctrl + Shift + D) - Clear - Clears everything
(Ctrl + A) - Selects everything
(Ctrl + M, L) - GetMods - Gets a JSON of the mods
(Ctrl + M, S) - GetModsSize - Gets the total size of the mods
(Ctrl + M, N) - GetModNames - Gets the names of the mods in a list
"""}

PluginApi = PluginApi(PluginApi,context=context)
def load_plugins(api, plugin_dir="plugins"):
    for filename in os.listdir(plugin_dir):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue

        path = os.path.join(plugin_dir, filename)
        module_name = f"plugin_{filename[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "setup"):
                module.setup(api)
                print(f"[PLUGIN] Loaded {filename}")
            else:
                print(f"[PLUGIN] {filename} has no setup()")

        except Exception:
            print(f"[PLUGIN] Failed to load {filename}")
            traceback.print_exc()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.join(BASE_DIR, "plugins")

load_plugins(PluginApi,plugin_dir=PLUGIN_DIR)



BUTTONROWS=4
undo_stack = []
redo_stack = []
verdig = "0.1.23"
global modcount
modcount=0

class UndoFuncts:

    def Write(data):
        update_redo("Write",textbox.get(1.0,tk.END))
        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,data)
    
    
    def ReWrite(data):
        update_undo("Write",textbox.get(1.0,tk.END))
        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,data)

UndoActions = {"Write":UndoFuncts.Write}
RedoActions = {"Write":UndoFuncts.ReWrite}

def undo(event=None):
    try:
        info = undo_stack.pop(-1)
        UndoActions[info[0]](info[1])
        
    except:
        print("Error Undoing")
    return "break"

def redo(event=None):
    try:
        info = redo_stack.pop(-1)
        RedoActions[info[0]](info[1])
        
    except:
        print("Error Redoing")
    return "break"

def update_undo(act,data):
    undo_stack.append([act,data])

def update_redo(act,data):
    redo_stack.append([act,data])

print(f"RUNNING MARSCT\nVERSION {verdig}")

def SizeConvert(sizetext:str):
    text = sizetext.strip().upper()
    if text.endswith(" KB"):
        return round((float(sizetext.removesuffix(" KB"))/1000000),3)
    elif text.endswith(" MB"):
        return round((float(sizetext.removesuffix(" MB"))/1000),3)
    elif text.endswith(" GB"):
        return round(float(sizetext.removesuffix(" GB")),3)
    return None

import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
plugin_api_dir = os.path.join(script_dir, "PluginAPI")

# Add both possible locations
sys.path.insert(0, script_dir)
sys.path.insert(0, plugin_api_dir)

try:
    from fetchmods import fetch_mod_info as c_fetch_mod_info
    print("[SUCCESS] Loaded C module fetchmods.so")
except ImportError as e:
    print(f"[WARNING] Failed to load fetchmods.so: {e}")
    print(f"  sys.path includes: {sys.path}")
    print(f"  Looking in: {script_dir} and {plugin_api_dir}")
    c_fetch_mod_info = None

def fetch_mod_info(item, seen_mods):
    global modcount
    
    if not item or item in seen_mods:
        return None
    
    if item == "":
        return None
    
    print(f"[DEBUG] Fetching mod {item} ...")

    # ────────────────────────────────────────────────────────────────
    #  Use the fast C version if available
    # ────────────────────────────────────────────────────────────────
    if c_fetch_mod_info is not None:
        # C function expects list of seen mods (not set)
        print(f"[DEBUG] → Using C version for {item}")
        seen_list = list(seen_mods)
        result = c_fetch_mod_info(item, seen_list)
        
        if result is None:
            print(f"[DEBUG] C returned None for {item}")
            return None
        print(f"[DEBUG] C returned: {result}")

        modcount += 1
        updatemodcount()
        
        return result
    
    
    # ────────────────────────────────────────────────────────────────
    #  Fallback: your original slow Python version
    # ────────────────────────────────────────────────────────────────
    else:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        itemnew = {"modId": item}
        
        try:
            response = requests.get(f"https://reforger.armaplatform.com/workshop/{item}", timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"Request failed for {item}: {e}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        version_element = None
        size_element = None
        
        # First attempt – exact selector for Version
        for div in soup.select(".flex.items-center.justify-between.border-b"):
            dt = div.find("dt")
            if dt and dt.text.strip() == "Version":
                version_element = div.find("dd")
                break
        
        # Dependencies from links
        hrefs = [a['href'] for a in soup.find_all('a', href=True)]
        pattern = re.compile(r'/workshop/([A-F0-9]+)-')
        dependencies = {match.group(1) for href in hrefs if (match := pattern.search(href))}
        
        # Looser selector for version & size
        for row in soup.select('div[class*="flex"][class*="justify-between"][class*="border-b"]'):
            dt = row.find("dt")
            dd = row.find("dd")
            if not dt or not dd:
                continue
            key_text = dt.get_text(strip=True).lower()
            value_text = dd.get_text(strip=True)
            
            if "version" in key_text and "size" not in key_text:
                version_element = value_text
            elif "size" in key_text:
                size_element = value_text
        
        itemnew["version"] = version_element if version_element else "Version not found"
        
        name_element = soup.select_one("h1.text-3xl.font-bold.uppercase")
        itemnew["name"] = name_element.text.strip() if name_element else "Name not found"
        
        itemnew["size"] = SizeConvert(size_element)
        itemnew["deps"] = dependencies
        
        modcount += 1
        updatemodcount()
        
        return itemnew

def GetModStuff(Deps, seen):
    modlist = []
    seen_mods = seen.copy()  # avoid mutating caller's set during recursion
    
    for b in Deps:
        mod_info = fetch_mod_info(b, seen_mods)
        if mod_info is None:
            continue
        
        # Deduplicate: skip if already seen (and add now)
        if mod_info["modId"] in [m["modId"] for m in modlist]:
            continue
        
        fixedmod_info = {k: v for k, v in mod_info.items() if k != "deps"}
        modlist.append(fixedmod_info)
        
        # Add to seen **after** adding to list
        seen_mods.add(mod_info["modId"])
        
        # Recurse on dependencies
        deps_modlist, seen_mods = GetModStuff(mod_info["deps"], seen_mods)
        for v in deps_modlist:
            # Also deduplicate deps
            if v["modId"] not in [m["modId"] for m in modlist]:
                modlist.append(v)
    
    return modlist, seen_mods

def GetModList(event=None):
    if PluginApi.is_event("getmodsjson"):
        PluginApi.trigger_event("getmodsjson")
        return
    update_undo("Write",textbox.get(1.0,tk.END))
    get = textbox.get(1.0,tk.END).strip()
    try:
        modlist = json.loads(get)
        seen = set()
        modlistbef = []
        for v in modlist:
            modlistbef.append(v["modId"])

        modlist,seen = GetModStuff(modlistbef,seen)

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,json.dumps(modlist,indent=4))
    except json.JSONDecodeError:
        seen = set()
        modlist = []
        modlistbef = get.split(",")

        modlist,seen = GetModStuff(modlistbef,seen)

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,json.dumps(modlist,indent=4))

def GetModsSize(event=None):
    if PluginApi.is_event("getmodssize"):
        PluginApi.trigger_event("getmodssize")
        return
    update_undo("Write",textbox.get(1.0,tk.END))
    get = textbox.get(1.0,tk.END).strip()
    try:
        modlist = json.loads(get)
        sum = 0
        for v in modlist:
            sum+=float(v["size"])

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,f"{sum} GB")

        return
    except json.JSONDecodeError:
        seen = set()
        modlist = []
        modlistbef = get.split(",")

        modlist,seen = GetModStuff(modlistbef,seen)

        sum = 0
        for v in modlist:
            sum+=float(v["size"])

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,f"{sum} GB")

def GetModNames(event=None):
    if PluginApi.is_event("getmodsnames"):
        PluginApi.trigger_event("getmodsnames")
        return
    update_undo("Write",textbox.get(1.0,tk.END))
    get = textbox.get(1.0,tk.END).strip()
    try:
        modlist = json.loads(get)
        sum = ""
        for v in modlist:
            sum+=f"{v['name']}\n"

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,f"{sum}")

        return
    except json.JSONDecodeError:
        seen = set()
        modlist = []
        modlistbef = get.split(",")

        modlist,seen = GetModStuff(modlistbef,seen)

        sum = ""
        for v in modlist:
            sum+=f"{v['name']}\n"

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,f"{sum}")

def GetModIds(event=None):
    if PluginApi.is_event("getmodsjson"):
        PluginApi.trigger_event("getmodsids")
        return
    update_undo("Write",textbox.get(1.0,tk.END))
    get = textbox.get(1.0,tk.END).strip()
    try:
        modlist = json.loads(get)
        sum = ""
        for v in modlist:
            sum+=f"{v['modId']},"

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,f"{sum}")

        return
    except json.JSONDecodeError:
        seen = set()
        modlist = []
        modlistbef = get.split(",")

        modlist,seen = GetModStuff(modlistbef,seen)

        sum = ""
        for v in modlist:
            sum+=f"{v['modId']},"

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,f"{sum}")


def selall(event=None):
    textbox.tag_add("sel","1.0","end")
    textbox.mark_set(tk.INSERT,"end")
    textbox.see(tk.INSERT)
    return "break"

def updatemodcount():
    MDCount.config(text=f"Mods Loaded:{modcount}")

def clear(event=None):
    update_undo("Write",textbox.get(1.0,tk.END))
    textbox.delete(1.0,tk.END)
    return "break"

def settb(text):
    clear()
    textbox.insert(1.0,text)

PluginApi.register_event("clear",clear)
PluginApi.register_event("settextbox",settb)

def help(event=None):
    tl = tk.Toplevel(gui)
    tl.title("Help window")
    tl.configure(bg="#121212")          # or tl['bg'] = "#121212"

    label = tk.Label(
        tl,
        bg="#121212",                   # bg is preferred over background=
        fg="white",                     # standard lowercase
        text=context["HelpMSG"],
        justify="left",
        wraplength=680,                 # wrap long lines
        padx=16,
        pady=16,
        font=("Consolas", 10)           # or "TkDefaultFont", "Arial", etc.
    )
    label.pack(expand=True, fill="both")

    # Optional — nicer window behavior
    tl.geometry("720x480")
    tl.transient(gui)                   # child of main window

    return "break"

gui = tk.Tk()
gui.config(background="#121212")
Title = tk.Label(gui, text="MuZe's AR Server Config tools", background="#121212", foreground="White", font=("Arial", 40, "bold"), pady=20)
textbox = tk.Text(gui, background="#121212", foreground="White", font=("Arial", 12, "bold"), width=100, insertbackground="White",highlightthickness=2)
Frame = tk.Frame(gui, background="#121212",highlightbackground="White",highlightthickness=2,padx=100)
Version = tk.Label(Frame, text=f"--- Version {verdig} ---", background="#121212", foreground="White", pady=4, font=("Arial", 12, "bold"))
MDCount = tk.Label(Frame, text=f"Mods Loaded:0", background="#121212", foreground="White", pady=4, font=("Arial", 12, "bold"))
Frame2 = tk.Frame(Frame, background="#121212",highlightbackground="White",highlightthickness=0,pady=5)

Buttons = {}

Buttons["Actions"] = {}
Buttons["Actions"]["getmodsjson"] = tk.Button(Frame2, text="GetMods", command=GetModList, background="#121212", foreground="White")
Buttons["Actions"]["getmodssize"] = tk.Button(Frame2, text="GetModsSize", command=GetModsSize, background="#121212", foreground="White")
Buttons["Actions"]["getmodsnames"] = tk.Button(Frame2, text="GetModNames", command=GetModNames, background="#121212", foreground="White")
Buttons["Actions"]["getmodsids"] = tk.Button(Frame2, text="GetModIds", command=GetModIds, background="#121212", foreground="White")

Buttons["Utils"] = {}
Buttons["Utils"]["clear"] = tk.Button(Frame2, text="Clear", command=clear, background="#3F0A0A", foreground="White")
Buttons["Utils"]["undo"] = tk.Button(Frame2, text="Undo", command=undo, background="#121212", foreground="White")
Buttons["Utils"]["redo"] = tk.Button(Frame2, text="Redo", command=redo, background="#121212", foreground="White")
for button in PluginApi.buttons:
    cat = button["category"]
    text = button["text"]
    Call = button["callable"]
    color = button["color"]
    name = button["name"]
    if not Buttons[cat]:
        Buttons[cat] = {}
    Buttons[cat][name] = tk.Button(Frame2, text=text, command=Call, background=color, foreground="White")


Nutton = tk.Button(Frame, text="Help me", command=help, background="#121212", foreground="White")

textbox.bind("<Control-Z>",undo)
textbox.bind("<Control-z>",undo)
textbox.bind("<Control-Y>",redo)
textbox.bind("<Control-y>",redo)
textbox.bind("<Control-A>",selall)
textbox.bind("<Control-a>",selall)
textbox.bind("<Control-D>",clear)
textbox.bind("<Control-m><l>",GetModList)
textbox.bind("<Control-m><s>",GetModsSize)
textbox.bind("<Control-m><n>",GetModNames)
textbox.bind("<Control-h><e><l><p>",help)
textbox.bind("<F1>",help)
BUTTONROWS = max([len(x) for x in Buttons])
Frame2.rowconfigure(BUTTONROWS)
Frame2.columnconfigure(len(Buttons))

Frame.rowconfigure(4)
Frame.columnconfigure(1)

Title.pack()
textbox.pack()
Frame.pack()

for i,v in enumerate(Buttons.values()):
    for u,(d,b) in enumerate(v.items()):
        ToolTip(b,d)
        b.grid(column=i,row=u)

Frame2.grid(column=0,row=0)
Nutton.grid(column=0,row=1)
Version.grid(column=0,row=2)
MDCount.grid(column=0,row=3)


gui.title("MARSCT")
gui.mainloop()