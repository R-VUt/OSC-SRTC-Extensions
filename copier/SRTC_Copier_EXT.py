import json
import os
import socket
import threading
import tkinter
from tkinter import IntVar
import sys

#clipboard
import pyperclip

import flask
import requests

sys.stdout = sys.stderr = open(os.devnull, 'w') # noconsole fix

# Constants
EXT_NAME = "Copier-V1"
HEARTBEAT_ENDPOINT = "/extension/heartbeat"
EXECUTE_ENDPOINT = "/extension/execute"

# Globals
srtc_ip = ""
srtc_port = 0
ext_ip = ""
ext_port = 0
extension_num = None
settings = None
is_blocking = None

app = None
root = None
extension_num_label = None
log_box = None


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

    if not message:
        return message, 200
    
    pyperclip.copy(message)
    log(f"Copied: {message}")

    if is_blocking != None and is_blocking.get() == 1:
        log("Blocking")
        return "{Sended-Already}", 200
    
    return message, 200


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

def initialize():
    global app
    global srtc_ip
    global srtc_port
    global ext_ip
    global ext_port
    global extension_num

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


    # initialize tkinter
    main_window()


def main_window():
    global root
    global extension_num_label
    global log_box
    global is_blocking_switch
    global is_blocking


    root = tkinter.Tk()
    
    is_blocking = IntVar()
    root.title("SRTC Copier")
    root.geometry("400x300")
    root.resizable(False, False)

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

    title_label = tkinter.Label(root, text="OSC-SRTC Copier Extension V1", font="Helvetica 12 bold")
    title_label.pack()

    #read only
    log_box = tkinter.Text(root, width=50, height=15)
    log_box.config(state="disabled")
    log_box.pack()

    #toggle_is_blocking
    is_blocking_switch = tkinter.Checkbutton(root, text="block after this", variable=is_blocking)
    is_blocking_switch.pack()

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