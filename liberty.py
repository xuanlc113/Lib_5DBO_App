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

# def getLibertyEOD(url):
# 	subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe", url])
# 	time.sleep(20 + random.uniform(1, 2))
	
# 	# pyautogui.hotkey('win', 'printscreen')
# 	pyautogui.click(x=1216, y=970)
# 	time.sleep(20 + random.uniform(1, 2))
      
# 	# for i in range(3):
# 	# 	pyautogui.click(x=1216, y=970)
# 	# 	time.sleep(2)
# 	# 	pyautogui.hotkey('win', 'printscreen')
# 	# 	time.sleep(1)
          
# 	# time.sleep(5)
# 	pyautogui.hotkey('ctrl', 'a')
# 	time.sleep(1)
# 	pyautogui.hotkey('ctrl', 'c')
# 	time.sleep(1)

# 	html = pyperclip.paste()
	
# 	pyautogui.click(x=1888, y=23)
# 	# os.system('taskkill /IM chrome.exe /F')
# 	return html

def getLibertyChatEOD(url):
	si = subprocess.STARTUPINFO()
	si.dwFlags = subprocess.STARTF_USESHOWWINDOW
	si.wShowWindow = 3   # MAXIMIZE WINDOW
	subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe", url], startupinfo=si)
	time.sleep(30 + random.uniform(1, 2))
	pyautogui.hotkey('win', 'printscreen')
	time.sleep(2)
	
	pyautogui.click(x=1365, y=900)
	time.sleep(2)
	
	pyautogui.press('home')
	time.sleep(20)
	pyautogui.hotkey('win', 'printscreen')
	time.sleep(2)
	pyautogui.scroll(500)
	time.sleep(20)
	pyautogui.hotkey('win', 'printscreen')
	time.sleep(2)

	pyautogui.hotkey('ctrl', 'a')
	time.sleep(2)

	pyautogui.hotkey('ctrl', 'c')
	time.sleep(2)
    
	html = pyperclip.paste()
	time.sleep(2)
	pyautogui.hotkey('win', 'printscreen')
	time.sleep(2)
    
	pyautogui.click(x=1888, y=23) # Close Chrome
	time.sleep(2)
    
	clean_text = html.encode('ascii', 'ignore').decode('ascii')

	utils.log(clean_text)
      
	parts = clean_text.split('\r\nToday\r\n')
      
	if len(parts) < 2:
		return ""

	return parts[-1]
	

def parse_trade_signals(text):
	regexPattern = r"\d+\)\s*\$([A-Z]+)[^$]*\$(\d+(?:\.\d+)?)\s+(LONG|SHORT)"
	pattern = re.compile(regexPattern, re.IGNORECASE)
	results = []
	for match in pattern.finditer(text):
		ticker = match.group(1).upper()
		entry_price = float(match.group(2))
		direction = match.group(3).upper()
		# Adjust risk per share to current trading price
		results.append({
			"ticker": ticker,
			"action": direction,
			"price": entry_price,
		})
	return results

def wait_EOD(stop_event=None):
    utils.log("Waiting for 15:55...")
    ny_tz = pytz.timezone('America/New_York')
    while True:
        if stop_event and stop_event.is_set():
            return
        now_ny = datetime.datetime.now(ny_tz)
        if now_ny.hour == 15 and now_ny.minute >= 54:
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

	unlockScreen()
	
	url = cfg.get("url")
	text = getLibertyChatEOD(url)
	utils.log(text)
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

# print(getcursor())