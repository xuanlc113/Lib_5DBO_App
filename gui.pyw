import tkinter as tk
import threading
import winsound
from liberty import startLiberty
import config
import utils

stop_liberty_flag = threading.Event()
liberty_thread = None

def log_message(msg):
    log_text.config(state='normal')
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    log_text.config(state='disabled')
    
utils.set_log_callback(log_message)

def on_button_click():
    global liberty_thread
    stop_liberty_flag.clear()
    liberty_thread = threading.Thread(target=startLiberty, kwargs={'stop_event': stop_liberty_flag}, daemon=True)
    liberty_thread.start()

def on_stop_button_click():
    winsound.PlaySound(None, winsound.SND_PURGE)
    stop_liberty_flag.set()

def open_settings():
    load_settings()  # Always load latest config when opening
    settings_frame.place(relx=1.0, rely=0, anchor='ne', relheight=1.0, width=250)

def close_settings():
    settings_frame.place_forget()

def save_settings():
    new_settings = {
        "host": host_entry.get(),
        "port": port_entry.get(),
        "client_id": client_id_entry.get(),
        "max_capital": max_capital_entry.get(),
        "fallback_capital": fallback_capital_entry.get(),
        "risk": risk_entry.get(),
        "bet_multiplier": bet_multiplier_entry.get(),
        "limit_buffer": limit_buffer_entry.get(),
        "url": url_entry.get(),
    }
    updated = config.save_settings(new_settings)
    if updated:
        log_message("Settings saved.")
    else:
        log_message("No changes to save.")
    close_settings()

def load_settings():
    cfg = config.read_config()
    host_entry.delete(0, tk.END)
    host_entry.insert(0, cfg.get('host', ''))
    port_entry.delete(0, tk.END)
    port_entry.insert(0, str(cfg.get('port', '')))
    client_id_entry.delete(0, tk.END)
    client_id_entry.insert(0, str(cfg.get('client_id', '')))
    max_capital_entry.delete(0, tk.END)
    max_capital_entry.insert(0, str(cfg.get('max_capital', '')))
    fallback_capital_entry.delete(0, tk.END)
    fallback_capital_entry.insert(0, str(cfg.get('fallback_capital', '')))
    risk_entry.delete(0, tk.END)
    risk_entry.insert(0, str(cfg.get('risk', '')))
    bet_multiplier_entry.delete(0, tk.END)
    bet_multiplier_entry.insert(0, str(cfg.get('bet_multiplier', '')))
    limit_buffer_entry.delete(0, tk.END)
    limit_buffer_entry.insert(0, str(cfg.get('limit_buffer', '')))
    url_entry.delete(0, tk.END)
    url_entry.insert(0, cfg.get('url', ''))

root = tk.Tk()
root.title("EOD API")
root.geometry("800x450")  # Make window taller for more fields

main_frame = tk.Frame(root)
main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

button_frame = tk.Frame(main_frame)
button_frame.pack(padx=20, pady=10)

button = tk.Button(button_frame, text="Start", command=on_button_click)
button.pack(side=tk.LEFT, padx=(0, 10))

stop_button = tk.Button(button_frame, text="Stop", command=on_stop_button_click)
stop_button.pack(side=tk.LEFT)

log_text = tk.Text(main_frame, height=10, state='disabled')
log_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

# Settings logo button at top right
def get_gear_unicode():
    # Unicode gear/cog: U+2699
    return "\u2699"

settings_logo_btn = tk.Button(
    root,
    text=get_gear_unicode(),
    font=("Arial", 18),
    command=open_settings,
    bd=0,
    relief=tk.FLAT,
    bg="#f0f0f0",
    activebackground="#e0e0e0"
)
settings_logo_btn.place(relx=1.0, y=0, anchor='ne', width=40, height=40)

settings_frame = tk.Frame(root, bd=2, relief=tk.GROOVE, bg="#f0f0f0")

def add_setting_row(parent, label_text, entry_widget, row):
    label = tk.Label(parent, text=label_text, bg="#f0f0f0", width=12, anchor='w')
    label.grid(row=row, column=0, sticky='w', padx=(5, 5), pady=2)
    entry_widget.grid(row=row, column=1, sticky='ew', padx=(0, 5), pady=2)
    parent.grid_columnconfigure(1, weight=1)

host_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Host:", host_entry, 0)

port_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Port:", port_entry, 1)

client_id_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Client ID:", client_id_entry, 2)

max_capital_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Max Capital:", max_capital_entry, 3)

fallback_capital_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Fallback Capital:", fallback_capital_entry, 4)

risk_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Risk:", risk_entry, 5)

bet_multiplier_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Bet Mult:", bet_multiplier_entry, 6)

limit_buffer_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "Limit Buffer:", limit_buffer_entry, 7)

url_entry = tk.Entry(settings_frame)
add_setting_row(settings_frame, "URL:", url_entry, 8)

save_btn = tk.Button(settings_frame, text="Save", command=save_settings)
close_btn = tk.Button(settings_frame, text="Close", command=close_settings)

save_btn.grid(row=9, column=0, padx=5, pady=10, sticky='e')
close_btn.grid(row=9, column=1, padx=5, pady=10, sticky='w')


# Hide settings frame at start
settings_frame.place_forget()

# Load settings on startup
load_settings()

root.mainloop()
