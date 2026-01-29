Events = [
    "getmodsjson",
    "getmodsnames",
    "getmodsids",
    "getmodssize",
    "buttonpress",
    "undo",
    "redo",
    "clear",
    "loaded"
    ]

class PluginApi:
    def __init__(self, app, context):
        self.app = app
        self.context = context  # pass things like listb, errors, bg, fg, etc.
        self._event_handlers = {}
        self.buttons = []

        for v in Events:
            self._event_handlers[v] = []

    def AddKeybind(self,key,caller:callable):
        self.trigger_event("Keybind",caller)

    def ClearText(self):
        self.trigger_event("clear")

    def GetModData(self,modid,seen_mods={}):
        self.trigger_event("get_mod",item=modid,seen_mods=seen_mods)

    def SetText(self,text):
        self.trigger_event("settextbox",text=text)

    def add_button(self,category,name,text,caller:callable,buttoncolor="#121212"):
        def Call():
            self.trigger_event("buttonpress")
            caller()
        self.buttons.append({"category":category,"name":name,"text":text,"callable":Call,"color":buttoncolor})

    def register_event(self, event_name:str, caller:callable):
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = [caller]
        else:
            self._event_handlers[event_name].append(caller)
    
    def is_event(self,event_name):
        if event_name in self._event_handlers:
            if len(self._event_handlers[event_name])<1:
                return False
        else:
            return False
        return True

    def trigger_event(self,event_name,**kwargs):
        if event_name in self._event_handlers:
            for v in self._event_handlers[event_name]:
                return v(**kwargs)
        else:
            print(f"No Event To Trigger Named {event_name}")
            return None