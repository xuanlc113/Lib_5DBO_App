## Requirements

- Windows (the GUI and audio features use `tkinter` and `winsound`)
- Python 3.10 or newer
- Google Chrome
- Interactive Brokers Trader Workstation (TWS) or IB Gateway, with its API socket enabled
- IB API
- The [Page Plain Text Chrome extension](https://chromewebstore.google.com/detail/page-plain-text/bephhamcfencdbjmlinkpapidliffpdg?hl=en-US)

## Installation

1. Install the Python packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Modify the `config.ini` according to your own requirements.

   ```ini
   max_capital <=== maximum capital usage, overrides fallback capital
   fallback_capital <=== capital to use if failed to retrieve from ibkr
   risk = <=== account risk per trade, 0.01 = 1%
   bet_multiplier <=== any additional risk, 1.1 * 1% = 1.1%
   limit_buffer <=== limit order points over bid/ask for entry
   url <=== discord eod channel url
   ```

3. In TWS, enable socket clients under **Global Configuration → API → Settings**. Confirm that socket clients are permitted and that the socket port matches `config.ini`. Use paper trading while setting up and validating the connection.
4. Sign in to Discord in Chrome, open the channel whose URL is in `config.ini`, and ensure the Page Plain Text extension is available.
5. Run the `python liberty.py` from Command prompt

   Alternatively, a desktop shortcut of `gui.pyw` can be created for convenience; In the shortcut's properties, set **Start in** directory to the project directory because logs and `alarm.wav` use relative paths.

## Usage

1. Start TWS or IB Gateway and log in to the account you intend to use.
2. The Mouse automation clicks near the top of the screen, so just check that that area is empty to avoid unintentional side effects
3. Start LibertyApp, review the settings with the gear button, then click **Start**. The app reads the channel, processes signals, connects to the IB API, and places orders during its configured end-of-day entry window.
4. Click **Stop** to request that the running process stop and silence the alarm. Check the app window and the daily log under `logs/` for connection and order status.
