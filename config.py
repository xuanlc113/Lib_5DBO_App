import configparser
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

def read_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    cfg = config['DEFAULT'] if 'DEFAULT' in config else {}
    return {
        "host": cfg.get("host", "127.0.0.1"),
        "port": int(cfg.get("port", "7496")),
        "client_id": int(cfg.get("client_id", "10")),
        "max_capital": float(cfg.get("max_capital", "50000")),
        "fallback_capital": float(cfg.get("fallback_capital", "50000")),
        "risk": float(cfg.get("risk", "0.01")),
        "bet_multiplier": float(cfg.get("bet_multiplier", "1.0")),
        "limit_buffer": float(cfg.get("limit_buffer", "0.02")),
        "half_day": cfg.get("half_day", "false").lower() == "true",
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