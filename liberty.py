import re
import pyautogui
import pyperclip
import time
import subprocess
import random
from AutoTWS import start
import utils
import config
import traceback

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
	
	pyautogui.hotkey('shift', 'pageup')
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

def _extract_section(text, header_pattern):
	match = re.search(header_pattern, text, re.IGNORECASE)
	if not match:
		return ""
	start = match.end()
	next_match = re.search(r'ls\s+v3\s+breakout|ls\s+pullbacks', text[start:], re.IGNORECASE)
	end = start + next_match.start() if next_match else len(text)
	return text[start:end]

def _parse_bo_signals(text):
	if not text:
		return []
	ticker_re = re.compile(r'\$([A-Z]+)', re.IGNORECASE)
	price_re = re.compile(r'\$(\d+(?:\.\d+)?)')
	direction_re = re.compile(r'\b(LONG|SHORT)\b', re.IGNORECASE)
	ticker_matches = list(ticker_re.finditer(text))
	results = {}
	for i, tm in enumerate(ticker_matches):
		ticker = tm.group(1).upper()
		chunk_end = ticker_matches[i + 1].start() if i + 1 < len(ticker_matches) else len(text)
		chunk = text[tm.end():chunk_end]
		price_match = price_re.search(chunk)
		direction_match = direction_re.search(chunk)
		if price_match and direction_match:
			results[ticker] = {
				"ticker": ticker,
				"type": "BO",
				"action": direction_match.group(1).upper(),
				"price": float(price_match.group(1)),
			}
	return list(results.values())

def _parse_pb_signals(text):
	if not text:
		return []
	ticker_re = re.compile(r'\$([A-Z]+)', re.IGNORECASE)
	results = {}
	for line in text.splitlines():
		tm = ticker_re.search(line)
		if not tm:
			continue
		ticker = tm.group(1).upper()
		if re.search(r'\bweekly\b', line, re.IGNORECASE):
			results[ticker] = {"ticker": ticker, "type": "PB_weekly"}
		elif re.search(r'\bdaily\b', line, re.IGNORECASE):
			results[ticker] = {"ticker": ticker, "type": "PB_daily"}
	return list(results.values())

def parse_trade_signals(text):
	bo_text = _extract_section(text, r'ls\s+v3\s+breakout')
	pb_text = _extract_section(text, r'ls\s+pullbacks')
	return _parse_bo_signals(bo_text) + _parse_pb_signals(pb_text)

def order_and_cap_signals(signals):
	pb_weekly = [s for s in signals if s["type"] == "PB_weekly"][:2]
	bo = [s for s in signals if s["type"] == "BO"][:5]
	pb_daily = [s for s in signals if s["type"] == "PB_daily"][:2]
	return pb_weekly + bo + pb_daily

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
	utils.wait_until_ny(55, stop_event=stop_event)
	if stop_event and stop_event.is_set():
		utils.log("app stopped")
		return
	
	utils.log("begin processing")

	try:
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

		orders = order_and_cap_signals(orders)

		if len(orders) > 0:
			start(orders)
	except Exception as e:
		utils.log(f"ERROR: {e}")
		utils.log(traceback.format_exc())
		utils.alarm()

	utils.log("app stopped")

# cfg = config.read_config()
# url = cfg.get("url")
# text = getDiscordChatEOD(url)
# print(text)
# text= """
# ls v3 breakoUts
# 1) $BXMT (Blackstone Mortgage Trust) - If closing below $13.53 SHORT

# ls pullbacks

# $SD - Daily
# $DEE - Weekly
# """
# orders = parse_trade_signals(text)
# print(orders)

