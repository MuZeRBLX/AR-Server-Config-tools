import json
import requests
from bs4 import BeautifulSoup
import threading
import tkinter as tk
import re

BUTROWS=4
undo_stack = []
verdig = "0.1.23"
global modcount
modcount=0

print(f"RUNNING MARSCT\nVERSION {verdig}")

def UpdateUndo():

    undo_stack.append(modslast.get(1.0, tk.END).strip())

def undo_action():
    if undo_stack:
        last_state = undo_stack.pop()  # Retrieve last saved state
        
        modslast.delete(1.0, tk.END)
        modslast.insert(tk.END, last_state)
    else:
        print("Nothing to undo!")

def SizeConvert(sizetext:str):
    text = sizetext.strip().upper()
    if text.endswith(" KB"):
        return round((float(sizetext.removesuffix(" KB"))/1000000),3)
    elif text.endswith(" MB"):
        return round((float(sizetext.removesuffix(" MB"))/1000),3)
    elif text.endswith(" GB"):
        return round(float(sizetext.removesuffix(" GB")),3)
    return None

def fetch_mod_info(item, mod_dict, seen_mods):
    global modcount
    if item in seen_mods:
        return 
    
    seen_mods.add(item)
    itemnew = {"modId": item}

    if item == "":
        return

    response = requests.get(f"https://reforger.armaplatform.com/workshop/{item}")
    soup = BeautifulSoup(response.text, "html.parser")

    version_element = None
    Size_element = None
    for div in soup.select(".flex.items-center.justify-between.border-b"):
        dt = div.find("dt")
        if dt and dt.text.strip() == "Version":
            version_element = div.find("dd")
            break

    hrefs = [a['href'] for a in soup.find_all('a', href=True)]
    
    pattern = re.compile(r'/workshop/([A-F0-9]+)-')
    dependencies = {match.group(1) for href in hrefs if (match := pattern.search(href))}  

    for row in soup.select(".flex.items-center.justify-between.border-b"):
        dt = row.find("dt")
        dd = row.find("dd")
        
        if not dt or not dd:
            continue
            
        key = dt.get_text(strip=True)
        value = dd.get_text(strip=True)
        
        if key == "Version":
            version_element = value
        elif key == "Version size":
            Size_element = SizeConvert(value)

    itemnew["version"] = version_element if version_element else "Version not found"
    name_element = soup.select_one("h1.text-3xl.font-bold.uppercase")
    itemnew["name"] = name_element.text if name_element else "Name not found"
    itemnew["size"] = Size_element

    mod_dict[item] = itemnew  # Store mod info
    
    modcount+=1
    updatemodsloaded()

    # Add dependencies as separate mods
    for dep in dependencies:
        fetch_mod_info(dep, mod_dict, seen_mods)


def Do():
    global modcount
    print("Getting Mods")
    modlistinp = modslast.get(1.0, tk.END).strip()
    try:
        y = json.loads(modslast.get(1.0, tk.END))
    except json.JSONDecodeError:

        modcount=0
        updatemodsloaded()

        UpdateUndo()
    
        modlist = modlistinp.split(",")

        mod_dict = {}
        seen_mods = set()

        def update_gui():
            sorted_mods = sorted(mod_dict.values(), key=lambda x: x["name"])  # Sort by mod name
            modslast.delete(1.0, tk.END)
            modslast.insert(tk.END, json.dumps(sorted_mods, indent=4))

        def fetch_and_store(item):
            fetch_mod_info(item.strip(), mod_dict, seen_mods)
            gui.after(100, update_gui) 

        for item in modlist:
            threading.Thread(target=fetch_and_store, args=(item,), daemon=True).start()
            
        return

    print("Error: Cannot Be JSON")
    return

def Do2():
    global modcount
    modlistinp = modslast.get(1.0, tk.END).strip()
    try:
        y = json.loads(modslast.get(1.0, tk.END))
        UpdateUndo()

        size = 0.0
        for x in y:
            size+=x["size"]
        modslast.delete(1.0, tk.END)
        modslast.insert(tk.END, f"{size} GB")

        return
    except json.JSONDecodeError:
        UpdateUndo()

        modcount=0
        updatemodsloaded()
    
        modlist = modlistinp.split(",")

        mod_dict = {}
        seen_mods = set()

        def update_gui():
            sorted_mods = sorted(mod_dict.values(), key=lambda x: x["name"])  # Sort by mod name

            size = 0.0

            for i in sorted_mods:
                size +=  round(i["size"],3)

            modslast.delete(1.0, tk.END)
            modslast.insert(tk.END, f"{size} GB")

        def fetch_and_store(item):
            fetch_mod_info(item.strip(), mod_dict, seen_mods)
            gui.after(100, update_gui) 

        for item in modlist:
            threading.Thread(target=fetch_and_store, args=(item,), daemon=True).start()
            
        return
    print("Wrong Format")
    return


def ConvertToIDs():
    List = []
    try:
        y = json.loads(modslast.get(1.0, tk.END))
    except json.JSONDecodeError:
        print("Error: Invalid JSON")
        return

    for item in y:
        List.append(item["modId"])

    UpdateUndo()

    modslast.delete(1.0, tk.END)
    modslast.insert(tk.END, ",".join(List))

def ConvertToNames():
    try:
        y = json.loads(modslast.get(1.0, tk.END))
    except json.JSONDecodeError:
        UpdateUndo()
        modlistinp = modslast.get(1.0, tk.END).strip()
        modlist = modlistinp.split(",")

        mod_dict = {}
        seen_mods = set()

        def update_gui():
            sorted_mods = sorted(mod_dict.values(), key=lambda x: x["name"])  # Sort by mod name

            fin = ""

            for i in sorted_mods:
                fin+=(i["name"]+"\n")

            modslast.delete(1.0, tk.END)
            modslast.insert(tk.END, f"{fin}")

        def fetch_and_store(item):
            fetch_mod_info(item.strip(), mod_dict, seen_mods)
            gui.after(100, update_gui) 

        for item in modlist:
            threading.Thread(target=fetch_and_store, args=(item,), daemon=True).start()
            
        return

    UpdateUndo()

    modslast.delete(1.0, tk.END)

    for item in y:
        modslast.insert(tk.END, f"{item['name']}\n")

def ConvertToGB():
    try:
        y = json.loads(modslast.get(1.0, tk.END))
    except json.JSONDecodeError:
        print("Error: Invalid JSON")
        return

    UpdateUndo()

    modslast.delete(1.0, tk.END)



    for item in y:
        modslast.insert(tk.END, f"{item['name']}")

def Clear():
    UpdateUndo()
    modslast.delete(1.0, tk.END)

def SelAll(event=None):
    modslast.tag_add("sel","1.0","end")
    modslast.mark_set(tk.INSERT,"end")
    modslast.see(tk.INSERT)
    return "break"
        
def UpdateMods():
    modlist = []
    try:
        mods = json.loads(modslast.get(1.0, tk.END))
    except json.JSONDecodeError:
        print("Error: Invalid JSON in modslast")
        return
    
    for v in mods:
        modlist.append(v["modId"].strip())

    mod_dict = {}
    seen_mods = set()
    lock = threading.Lock()

    def update_gui():
        sorted_mods = sorted(mod_dict.values(), key=lambda x: x["name"])  # Alphabetize mods
        UpdateUndo()
        modslast.delete(1.0, tk.END)
        with lock:
            modslast.insert(tk.END, json.dumps(sorted_mods, indent=4))

    def fetch_and_store(item):
        fetch_mod_info(item, mod_dict, seen_mods)
        gui.after(200, update_gui)

    for item in modlist:
        threading.Thread(target=fetch_and_store, args=(item,), daemon=True).start()

def updatemodsloaded():
    MDCount.config(text=f"Mods Loaded:{modcount}")

gui = tk.Tk()
gui.config(background="#121212")
Title = tk.Label(gui, text="MuZe's AR Server Config tools", background="#121212", foreground="White", font=("Arial", 40, "bold"), pady=20)
modslast = tk.Text(gui, background="#121212", foreground="White", font=("Arial", 12, "bold"), width=100, insertbackground="White",highlightthickness=2)
Frame = tk.Frame(gui, background="#121212",highlightbackground="White",highlightthickness=2,padx=100)
Version = tk.Label(Frame, text=f"--- Version {verdig} ---", background="#121212", foreground="White", pady=8, font=("Arial", 12, "bold"))
MDCount = tk.Label(Frame, text=f"Mods Loaded:0", background="#121212", foreground="White", pady=8, font=("Arial", 12, "bold"))
Frame2 = tk.Frame(Frame, background="#121212",highlightbackground="White",highlightthickness=0,padx=0)
enterbut = tk.Button(Frame2, text="GetModsSize", command=Do2, background="#121212", foreground="White")
enterbut5 = tk.Button(Frame2, text="GetMods", command=Do, background="#121212", foreground="White")
enterbut4 = tk.Button(Frame2, text="UpdateMods", command=UpdateMods, background="#121212", foreground="White")
enterbut2 = tk.Button(Frame2, text="GetModNames", command=ConvertToNames, background="#121212", foreground="White")
enterbut3 = tk.Button(Frame2, text="GetModIDs", command=ConvertToIDs, background="#121212", foreground="White")
enterbut7 = tk.Button(Frame2, text="SelectAll", command=SelAll, background="#121212", foreground="White")
enterbut6 = tk.Button(Frame2, text="Clear", command=Clear, background="#121212", foreground="White")
enterbut1 = tk.Button(Frame2, text="Undo", command=undo_action, background="#121212", foreground="White")

Title.pack()
modslast.pack()
Frame.pack()
Frame.grid_columnconfigure(1)
Frame.grid_rowconfigure(3)
col = int(len(Frame2.winfo_children())/BUTROWS)
Frame2.grid_columnconfigure(col+1)
Frame2.grid_rowconfigure(BUTROWS)

for i,v in enumerate(Frame2.winfo_children()):
    v.grid(row=i%BUTROWS,column=int(i/BUTROWS))

Frame2.grid(row=0)
Version.grid(row=1)
MDCount.grid(row=2)

modslast.bind("<Control-a>",SelAll)
modslast.bind("<Control-A>",SelAll)

gui.title = "Set"

gui.mainloop()