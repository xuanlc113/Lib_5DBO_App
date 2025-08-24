import configparser
import os

CONFIG_FILE = "config.ini"

def read_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    cfg = config['DEFAULT'] if 'DEFAULT' in config else {}
    return {
        "host": cfg.get("host", ""),
        "port": int(cfg.get("port", "7496")),
        "client_id": int(cfg.get("client_id", "10")),
        "capital": float(cfg.get("capital", "50000")),
        "risk": float(cfg.get("risk", "0.01")),
        "limit_buffer": float(cfg.get("limit_buffer", "0.02")),
        "url": cfg.get("url", ""),
    }

def save_settings(new_settings):
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    if 'DEFAULT' not in config:
        config['DEFAULT'] = {}

    updated = False
    for key, value in new_settings.items():
        prev_value = config['DEFAULT'].get(key, '')
        # Convert both to string for comparison
        if str(value) != str(prev_value):
            config['DEFAULT'][key] = str(value)
            updated = True

    if updated:
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        return True
    return False