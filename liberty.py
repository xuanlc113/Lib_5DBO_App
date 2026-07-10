import re
import pyautogui
import pyperclip
import time
import subprocess
import random
import datetime
import pytz
from AutoTWS import start
import utils
import config

def getDiscordChatEOD(url):
	si = subprocess.STARTUPINFO()
	si.dwFlags = subprocess.STARTF_USESHOWWINDOW
	si.wShowWindow = 3   # MAXIMIZE WINDOW
	subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe", "--new-window", url], startupinfo=si)
	time.sleep(30 + random.uniform(1, 2))
	pyautogui.hotkey('win', 'up')  # Maximize the new window, sometimes window opens halfscreen if another window is already open
	time.sleep(2)
	pyautogui.hotkey('win', 'printscreen')
	time.sleep(2)
	
	pyautogui.click(x=1030, y=1030)
	time.sleep(2)
	
	pyautogui.hotkey('ctrl', 'pageup')
	time.sleep(20)
	pyautogui.hotkey('win', 'printscreen')
	time.sleep(5)

	pyautogui.hotkey('ctrl', 'shift', '3')
	time.sleep(5)
	
	html = pyperclip.paste()
	time.sleep(5)
	
	pyautogui.click(x=1888, y=23) # Close Chrome
	time.sleep(2)
	
	clean_text = html.encode('ascii', 'ignore').decode('ascii')

	utils.log(clean_text)
	
	now_date_str = utils.getNowDateString()
	parts = clean_text.split(f'\r\n{now_date_str}\r\n')
	  
	if len(parts) < 2:
		return ""

	return parts[-1]

def parse_trade_signals(text):
	regexPattern = r"\d+\)\s*\$([A-Z]+)[^$]*\$(\d+(?:\.\d+)?)\s+(LONG|SHORT)"
	pattern = re.compile(regexPattern, re.IGNORECASE)
	results_dict = {}
	for match in pattern.finditer(text):
		ticker = match.group(1).upper()
		entry_price = float(match.group(2))
		direction = match.group(3).upper()
		results_dict[ticker] = {
			"ticker": ticker,
			"action": direction,
			"price": entry_price,
		}
	return list(results_dict.values())

def wait_EOD(stop_event=None):
    half_day = config.read_config()["half_day"]
    target_hour = 12 if half_day else 15
    utils.log(f"Waiting for {target_hour}:55...")
    ny_tz = pytz.timezone('America/New_York')
    while True:
        if stop_event and stop_event.is_set():
            return
        now_ny = datetime.datetime.now(ny_tz)
        if now_ny.hour == target_hour and now_ny.minute >= 55:
            utils.log(f"EOD: {now_ny.hour}:{now_ny.minute}")
            break
        else:
            time.sleep(1)

def unlockScreen():
	pyautogui.click(x=1000, y=50)
	time.sleep(10)

def getcursor():
	time.sleep(3)
	x, y = pyautogui.position()
	print(f"Cursor position: ({x}, {y})")

def startLiberty(stop_event=None):
	cfg = config.read_config()

	utils.log("app started")
	wait_EOD(stop_event=stop_event)
	if stop_event and stop_event.is_set():
		utils.log("app stopped")
		return
	
	utils.log("begin processing")

	# total autogui time takes ~100s --> start at 15:55:00 to finish by 15:56:40
	unlockScreen()
	
	url = cfg.get("url")
	text = getDiscordChatEOD(url)
	utils.log(text)
	if text == "":
		utils.log("No text retrieved from Discord, exiting...")
		utils.alarm()
	orders = parse_trade_signals(text)
	utils.log(orders)

	# if len(orders) == 0:
	# 	utils.log("using llm parser...")
	# 	llmOut = llm.query_llm(text) // some empty string gives a huge list of tickers; dangerous
	# 	print(llmOut)
	# 	orders = parse_trade_signals(llmOut)
	# 	utils.log(orders)

	orders = orders[:5]

	if len(orders) > 0:
		start(orders)

	utils.log("app stopped")

# cfg = config.read_config()
# url = cfg.get("url")
# text = getDiscordChatEOD(url)
# print(text)
# orders = parse_trade_signals(text)
# print(orders)