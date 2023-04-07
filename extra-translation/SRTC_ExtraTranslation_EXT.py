import json
import os
import socket
import threading
import tkinter
import sys
import tkinter.ttk as ttk
import flask
import requests

from modules.SRTC_Translator import STranslator

Supported_Languages: list[str] = ["English", "Korean", "Japanese", "Chinese (simplified)", "Chinese (traditional)",
                       "French", "Spanish", "Italian", "Russian", "Ukrainian", "German", "Arabic", "Thai",
                       "Tagalog", "Bahasa Malaysia", "Bahasa Indonesia", "Hindi", "Hebrew", "Turkish",
                       "Portuguese", "Croatian", "Dutch"]

sys.stdout = sys.stderr = open(os.devnull, 'w') # noconsole fix

# Constants
EXT_NAME = "Extra-Translation-V1"
HEARTBEAT_ENDPOINT = "/extension/heartbeat"
EXECUTE_ENDPOINT = "/extension/execute"

# Globals
srtc_ip = ""
srtc_port = 0
ext_ip = ""
ext_port = 0
extension_num = None
settings = None

Translator_Selection: ttk.Combobox = None
Source_Selection: ttk.Combobox = None
Target_Selection: ttk.Combobox = None
Target2_Selection: ttk.Combobox = None

Translator: STranslator = None

app = None
root = None
extension_num_label = None
log_box = None

def translate(recognized):
    try:
        to_send_message = ""
        if Source_Selection.current() != Target_Selection.current():
            log("[Info] Translating to Target 1...")
            translated = Translator.Translate(Translator.getRegisteredTranslators()[Translator_Selection.current()], recognized, Supported_Languages[Source_Selection.current()],
                                                Supported_Languages[Target_Selection.current()])
        else:
            translated = recognized

        if Supported_Languages[Target_Selection.current()] == "Japanese" and Romaji_Mode.get() == 1:
            translated = Translator.RomajiConvert(translated)

        log("[Info] Translated to Target 1: " + translated)
        to_send_message += translated

        if Target2_Selection.current() != 0:
            if Source_Selection.current() != Target2_Selection.current()-1:

                log('[Info] Translating to Target 2... ')
                translated = Translator.Translate(Translator.getRegisteredTranslators()[Translator_Selection.current()], recognized, Supported_Languages[Source_Selection.current()],
                                                    Supported_Languages[Target2_Selection.current()-1])  
            else:
                translated = recognized

            if Supported_Languages[Target2_Selection.current()-1] == "Japanese" and Romaji_Mode.get() == 1:
                translated = Translator.RomajiConvert(translated)
            log("[Info] Translated to Target 2: " + translated)
            to_send_message += " (" + translated + ")"
                

        if to_send_message != "":
            return to_send_message
        else:
            return recognized
    except Exception as e:
        print("[Error] " + e.with_traceback())
        return recognized


# Functions
def log(msg):
    if log_box is not None:
        log_box.config(state="normal")
        log_box.insert(tkinter.END, f"{msg}\n")
        log_box.see(tkinter.END)
        log_box.config(state="disabled")


def extension_heartbeat():
    global extension_num

    num = flask.request.args.get("num")
    if not num:
        return "Num is not exist", 400

    try:
        value = int(num)
    except ValueError:
        return "Num is not number", 400

    if value != extension_num:
        extension_num = value
        extension_num_label["text"] = str(extension_num)
        extension_num_label.update()

    return "OK", 200


def extension_execute():
    message = flask.request.args.get("message")
    return translate(message), 200


def get_remain_port(to_serve_ip: str):
    for port in range(10000, 65535):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex((to_serve_ip, port))
            if result != 0:
                return port


def get_settings():
    global srtc_ip, srtc_port, ext_ip, ext_port, to_filtering, settings

    with open("extension_settings.json", "r") as f:
        settings = json.load(f)
        srtc_ip = settings.get("srtc-ip") or "127.0.0.1"
        srtc_port = settings.get("srtc-port") or "9002"
        ext_ip = settings.get("extension-ip'") or "127.0.0.1"


def quit():
    if root is not None:
        root.destroy()
    os.kill(os.getpid(), 9)

def option_changed(*args):
  source_lang = Supported_Languages[Source_Selection.current()]
  target_lang = Supported_Languages[Target_Selection.current()]
  target2_lang = Supported_Languages[Target2_Selection.current()-1] if Target2_Selection.current() != 0 else "None"

  if not Translator.isLanguageSupported(Translator.getRegisteredTranslators()[Translator_Selection.current()], source_lang):
    print("[Error] This translator does not support " + source_lang + " language.")
    Translator_Selection.current(0)
  
  if not Translator.isLanguageSupported(Translator.getRegisteredTranslators()[Translator_Selection.current()], target_lang):
    print("[Error] This translator does not support " + target_lang + " language.")
    Translator_Selection.current(0)

  if target2_lang != "None" and not Translator.isLanguageSupported(Translator.getRegisteredTranslators()[Translator_Selection.current()], target2_lang):
    print("[Error] This translator does not support " + target2_lang + " language.")
    Translator_Selection.current(0)

def initialize():
    global app
    global srtc_ip
    global srtc_port
    global ext_ip
    global ext_port
    global extension_num
    global Translator

    get_settings()
    ext_port = get_remain_port(ext_ip)
    
    
    # initialize flask
    app = flask.Flask(__name__)
    app.add_url_rule(HEARTBEAT_ENDPOINT, "extension_heartbeat", extension_heartbeat, methods=["GET"])
    app.add_url_rule(EXECUTE_ENDPOINT, "extension_execute", extension_execute, methods=["GET"])
    threading.Thread(target=app.run, args=(ext_ip, ext_port)).start()
    
    
    # connect to main server
    try:
        connect_res = requests.get(f"http://{srtc_ip}:{srtc_port}/extension/register?name={EXT_NAME}&ip={ext_ip}&port={ext_port}")
        print(connect_res)
        if connect_res.status_code != 200:
            print("Failed to connect to main server")
            quit()
        extension_num = int(connect_res.text)

    except requests.exceptions.ConnectionError:
        print("Failed to connect to main server")
        quit()

    # initialize Translator
    Translator = STranslator(settings, log)


    # initialize tkinter
    main_window()


def main_window():
    global root
    global extension_num_label
    global log_box

    global Translator_Selection
    global Source_Selection
    global Target_Selection
    global Target2_Selection

    global Romaji_Mode

    root = tkinter.Tk()
    root.title("SRTC Extra Translation")
    root.geometry("400x500")
    root.resizable(False, False)

    # select box
    source_label = tkinter.Label(root, text="Source")
    Source_Selection = ttk.Combobox(root, height=5, values=Supported_Languages, state="readonly")

    target_label = tkinter.Label(root, text="Target")
    Target_Selection = ttk.Combobox(root, height=5, values=Supported_Languages, state="readonly")

    target2_label = tkinter.Label(root, text="Target2 -> ()")
    Target2_Selection = ttk.Combobox(root, height=5, values=["none"]+Supported_Languages, state="readonly")

    translator_label = tkinter.Label(root, text="Translator")
    Translator_Selection = ttk.Combobox(root, height=5, width=210, values=Translator.getRegisteredTranslators(), state="readonly")
    
    Romaji_Mode = tkinter.IntVar()
    romajiModeCheck = tkinter.Checkbutton(root, text="Romaji Mode (Ja)", variable=Romaji_Mode)

    Source_Selection.bind("<<ComboboxSelected>>", option_changed)
    Target_Selection.bind("<<ComboboxSelected>>", option_changed)
    Target2_Selection.bind("<<ComboboxSelected>>", option_changed)
    Translator_Selection.bind("<<ComboboxSelected>>", option_changed)

    Source_Selection.current(0)
    Target_Selection.current(1)
    Target2_Selection.current(0)
    Translator_Selection.current(0)

    
    # num panel
    num_panel = tkinter.Frame(root, relief="ridge", bd=2)
    num_panel.grid_columnconfigure(3, weight=1)
    num_panel.grid_rowconfigure(0, weight=1)

    num_panel.pack()

    # extension num label
    extension_num_label = tkinter.Label(num_panel, text="?")
    extension_num_label.grid(row=0, column=1, sticky="w")

    if extension_num != None:
        extension_num_label["text"] = str(extension_num)
        extension_num_label.update()

    # extension num change button (left)
    extension_num_change_button_left = tkinter.Button(num_panel, text="<", command=extension_num_change_button_left_click)
    extension_num_change_button_left.grid(row=0, column=0, sticky="e")
    # extension num change button (right)
    extension_num_change_button_right = tkinter.Button(num_panel, text=">", command=extension_num_change_button_right_click)
    extension_num_change_button_right.grid(row=0, column=2, sticky="w")

    title_label = tkinter.Label(root, text="OSC-SRTC Extra Translation Extension V1", font="Helvetica 12 bold")
    title_label.pack()

    source_label.pack()
    Source_Selection.pack()
    target_label.pack()
    Target_Selection.pack()
    target2_label.pack()
    Target2_Selection.pack()
    translator_label.pack()
    Translator_Selection.pack()
    romajiModeCheck.pack()
    
    #read only
    log_box = tkinter.Text(root, width=50, height=15)
    log_box.config(state="disabled")
    log_box.pack()

    root.protocol("WM_DELETE_WINDOW", quit)

    root.mainloop()

def extension_num_change_button_left_click():
    global extension_num
    global extension_num_label

    requests.get(f"http://{srtc_ip}:{srtc_port}/extension/forward?name={EXT_NAME}")
    
def extension_num_change_button_right_click():
    global extension_num
    global extension_num_label

    requests.get(f"http://{srtc_ip}:{srtc_port}/extension/backward?name={EXT_NAME}")
        

if __name__ == "__main__":
    initialize()