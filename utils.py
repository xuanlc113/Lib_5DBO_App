from datetime import datetime
import os
from ibapi.wrapper import BarData

log_callback = None

def calcQuantity(direction: str, bar: BarData, entryPrice: float, limitBuffer: float, betSize: float):
    if direction == "LONG":
        entry = entryPrice + limitBuffer
        stop = bar.low
        riskPerShare = entry - stop
    elif direction == "SHORT":
        entry = entryPrice - limitBuffer
        stop = bar.high
        riskPerShare = stop - entry
    else:
        return 0

    if riskPerShare <= 0:
        return 0

    return int(round(betSize / riskPerShare))

def getAcceptableEntry(close: float, bidask: float, spread: float = 0.01):
    percent_diff = abs(bidask - close) / abs(close)
    if percent_diff > spread:
        return close
    return bidask

def set_log_callback(callback):
    global log_callback
    log_callback = callback

def log(msg, filename=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    if log_callback:
        log_callback(log_line)
    # Use current date for log file name if not provided
    if filename is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        filename = os.path.join(log_dir, f"log-{date_str}.out")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")