from datetime import datetime, time as dtime
import os
import time
import pytz
import winsound
import pythoncom
from pycaw.pycaw import AudioUtilities
import config

log_callback = None


def set_log_callback(callback):
    global log_callback
    log_callback = callback


def log(msg, filename=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    if log_callback:
        log_callback(log_line)
    if filename is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        filename = os.path.join(log_dir, f"log-{date_str}.out")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def getNowDateString():
    return datetime.now().strftime("%B %#d, %Y")


def alarm():
    pythoncom.CoInitialize()
    device = AudioUtilities.GetSpeakers()
    volume = device.EndpointVolume
    volume.SetMasterVolumeLevel(-8.0, None)
    winsound.PlaySound("alarm.wav", winsound.SND_LOOP | winsound.SND_ASYNC)


def isWithinRetryWindow():
    half_day = config.read_config()["half_day"]
    ny_tz = pytz.timezone("America/New_York")
    now_ny = datetime.now(ny_tz).time()
    if half_day:
        return dtime(12, 50) <= now_ny < dtime(12, 59, 35)
    return dtime(15, 50) <= now_ny < dtime(15, 59, 35)


def wait_until_ny(minute, second=0, stop_event=None):
    half_day = config.read_config()["half_day"]
    target_hour = 12 if half_day else 15
    log(f"Waiting for {target_hour}:{minute:02d}...")
    ny_tz = pytz.timezone('America/New_York')
    while True:
        if stop_event and stop_event.is_set():
            return
        now_ny = datetime.now(ny_tz)
        if now_ny.hour == target_hour and now_ny.minute >= minute and now_ny.second >= second:
            break
        time.sleep(1)
