import json
import requests
from bs4 import BeautifulSoup
import threading
import tkinter as tk
import re

HELPTEXT="" \
"Hello! Welcome to MARSCT (MuZe's Arma Reforger Server Config Tool)!\n" \
"This is a way to help you do mods. It'll give you everything to put\n" \
'in the "mods":[] <---- area\n--------\n' \
"KEYBINDS\n" \
"--------\n" \
"(CTRL+HELP)/F1-Gives you this menu.\n" \
"(CTRL+Z)Undo-Undoes an action\n" \
"(CTRL+Y)Redo-Redoes an action\n" \
"(CTRL+SHIFT+D)Clear-Clears everything\n" \
"(CTRL+A)-Selects everything\n" \
"(CTRL+ml>GetMods-Gets a json of the mods\n" \
"(CTRL+ms)GetModsSize-Gets the total size of the mods\n" \
"(CTRL+mn)GetModNames-Gets the names of the mods in a list\n" 

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

def fetch_mod_info(item, seen_mods):
    global modcount
    if not item or item in seen_mods:
        return None
    
    seen_mods.add(item)
    itemnew = {"modId": item}

    if item == "":
        return None

    response = requests.get(f"https://reforger.armaplatform.com/workshop/{item}")
    soup = BeautifulSoup(response.text, "html.parser")

    version_element = None
    size_element = None
    for div in soup.select(".flex.items-center.justify-between.border-b"):
        dt = div.find("dt")
        if dt and dt.text.strip() == "Version":
            version_element = div.find("dd")
            break

    hrefs = [a['href'] for a in soup.find_all('a', href=True)]
    
    pattern = re.compile(r'/workshop/([A-F0-9]+)-')
    dependencies = {match.group(1) for href in hrefs if (match := pattern.search(href))}  

    for row in soup.select('div[class*="flex"][class*="justify-between"][class*="border-b"]'):  # looser selector
        dt = row.find("dt")
        dd = row.find("dd")
        if not dt or not dd:
            continue
        
        key_text = dt.get_text(strip=True).lower()
        value_text = dd.get_text(strip=True)
        
        if "version" in key_text and "size" not in key_text:
            version_element = value_text
        elif "size" in key_text and "size" in key_text:
            size_element = value_text

    itemnew["version"] = version_element if version_element else "Version not found"
    name_element = soup.select_one("h1.text-3xl.font-bold.uppercase")
    itemnew["name"] = name_element.text if name_element else "Name not found"
    itemnew["size"] = SizeConvert(size_element)
    itemnew["deps"] = dependencies

    modcount+=1
    updatemodcount()

    return itemnew  # Store mod info

def GetModStuff(Deps,seen):
    modlist = []

    for b in Deps:
            mod_info = fetch_mod_info(b,seen_mods=seen)

            if mod_info is None:
                continue

            fixedmod_info = {}
            for i,v in mod_info.items():
                if i != "deps":
                    fixedmod_info[i] = v
            modlist.append(fixedmod_info)

            deps_modlist,seen = GetModStuff(mod_info["deps"],seen)
            for v in deps_modlist:
                fixedmod_info2 = {}
                for k,d in v.items():
                    if k != "deps":
                        fixedmod_info2[k] = d
                modlist.append(fixedmod_info2)

    return modlist,seen

def GetModList(event=None):
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
    update_undo("Write",textbox.get(1.0,tk.END))
    get = textbox.get(1.0,tk.END).strip()
    try:
        modlist = json.loads(get)
        sum = 0
        for v in modlist:
            sum+=v["size"]

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
            sum+=v["size"]

        textbox.delete(1.0,tk.END)
        textbox.insert(1.0,f"{sum} GB")

def GetModNames(event=None):
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

def help(event=None):
    tl = tk.Toplevel(gui)
    tl.title("Help window")
    tl.configure(bg="#121212")          # or tl['bg'] = "#121212"

    label = tk.Label(
        tl,
        bg="#121212",                   # bg is preferred over background=
        fg="white",                     # standard lowercase
        text=HELPTEXT,
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
Buttons["Actions"]["Button1"] = tk.Button(Frame2, text="GetMods", command=GetModList, background="#121212", foreground="White")
Buttons["Actions"]["Button2"] = tk.Button(Frame2, text="GetModsSize", command=GetModsSize, background="#121212", foreground="White")
Buttons["Actions"]["Button3"] = tk.Button(Frame2, text="GetModNames", command=GetModNames, background="#121212", foreground="White")

Buttons["Utils"] = {}
Buttons["Utils"]["Button1"] = tk.Button(Frame2, text="Clear", command=clear, background="#3F0A0A", foreground="White")
Buttons["Utils"]["Button2"] = tk.Button(Frame2, text="Undo", command=undo, background="#121212", foreground="White")
Buttons["Utils"]["Button3"] = tk.Button(Frame2, text="Redo", command=redo, background="#121212", foreground="White")
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
    for u,b in enumerate(v.values()):
        b.grid(column=i,row=u)

Frame2.grid(column=0,row=0)
Nutton.grid(column=0,row=1)
Version.grid(column=0,row=2)
MDCount.grid(column=0,row=3)


gui.title("MARSCT")
gui.mainloop()