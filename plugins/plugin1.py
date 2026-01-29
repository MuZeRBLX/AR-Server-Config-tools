
mod = {
    "name":"Hi"
}

def setup(api):
    def Hi():
        print("Hi!")
        api.ClearText()
        api.SetText("Hello!")
    def on_load():
        print(f"{mod["name"]} Has loaded!")
    api.register_event("loaded",on_load)