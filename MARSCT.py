import json
import requests
from bs4 import BeautifulSoup
import threading
import tkinter as tk
import re

undo_stack = []

def UpdateUndo():

    undo_stack.append(modslast.get(1.0, tk.END).strip())

def undo_action():
    if undo_stack:
        last_state = undo_stack.pop()  # Retrieve last saved state
        
        modslast.delete(1.0, tk.END)
        modslast.insert(tk.END, last_state)
    else:
        print("Nothing to undo!")


verdig = "0.0.5"

def fetch_mod_info(item, mod_dict, seen_mods):
    if item in seen_mods:
        return 

    seen_mods.add(item)
    itemnew = {"modId": item}

    response = requests.get(f"https://reforger.armaplatform.com/workshop/{item}")
    soup = BeautifulSoup(response.text, "html.parser")

    version_element = None
    for div in soup.select(".flex.items-center.justify-between.border-b"):
        dt = div.find("dt")
        if dt and dt.text.strip() == "Version":
            version_element = div.find("dd")
            break

    hrefs = [a['href'] for a in soup.find_all('a', href=True)]
    
    pattern = re.compile(r'/workshop/([A-F0-9]+)-')
    dependencies = {match.group(1) for href in hrefs if (match := pattern.search(href))}  
    
    itemnew["version"] = version_element.text.strip() if version_element else "Version not found"
    name_element = soup.select_one("h1.text-3xl.font-bold.uppercase")
    itemnew["name"] = name_element.text.strip() if name_element else "Name not found"

    mod_dict[item] = itemnew  # Store mod info
    
    # Add dependencies as separate mods
    for dep in dependencies:
        fetch_mod_info(dep, mod_dict, seen_mods)


def Do():
    modlistinp = modslast.get(1.0, tk.END).strip()
    try:
        y = json.loads(modslast.get(1.0, tk.END))
    except json.JSONDecodeError:
    
        modlist = modlistinp.split(",")

        mod_dict = {}
        seen_mods = set()

        def update_gui():
            UpdateUndo()
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
        print("Error: Invalid JSON")
        return

    UpdateUndo()

    modslast.delete(1.0, tk.END)

    for item in y:
        modslast.insert(tk.END, f"{item['name']}\n")
        
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

gui = tk.Tk()
gui.config(background="#121212")
Title = tk.Label(gui, text="MuZe's AR Server Config tools", background="#121212", foreground="White", font=("Arial", 40, "bold"), pady=20)
modslast = tk.Text(gui, background="#121212", foreground="White", font=("Arial", 12, "bold"), width=100, insertbackground="White",highlightthickness=2)
Frame = tk.Frame(gui, background="#121212",highlightbackground="White",highlightthickness=2,padx=100)
enterbut = tk.Button(Frame, text="GetMods", command=Do, background="#121212", foreground="White")
enterbut4 = tk.Button(Frame, text="UpdateMods", command=UpdateMods, background="#121212", foreground="White")
enterbut2 = tk.Button(Frame, text="GetModNames", command=ConvertToNames, background="#121212", foreground="White")
enterbut3 = tk.Button(Frame, text="GetModIDs", command=ConvertToIDs, background="#121212", foreground="White")
enterbut3 = tk.Button(Frame, text="Undo", command=undo_action, background="#121212", foreground="White")

Version = tk.Label(Frame, text=f"--- Version {verdig} ---", background="#121212", foreground="White", pady=8, font=("Arial", 12, "bold"))

Title.pack()
modslast.pack()
Frame.pack()
for i in Frame.winfo_children():
    i.pack()

gui.title = "Set"

gui.mainloop()
