from __future__ import annotations

import time

from IBAPIApp import IBAPIApp
from domain import BOSignal, PBSignal, OrderType, SignalType
import utils
import order_utils
import config


def launchTWSAPI(host, port, clientId):
    for attempt in range(3):
        utils.log("Launching IB API application...")
        app = IBAPIApp(host, port, clientId)
        time.sleep(5)
        if not app.isConnected():
            utils.log("Failed to connect to IB API, exiting...")
        else:
            utils.log("IB API Application Launched.")
            utils.log("Making dummy call for historical data connection...")
            bars = app.fetchHistoricalBars("AAPL", 1, "D", timeout=10)
            bar = bars[-1] if bars else None
            price = app.fetchMarketPrice("AAPL", "LONG", timeout=10) if bar is not None else None
            if bar is None or price is None:
                utils.log("No OHLC data for dummy AAPL call")
            else:
                utils.log("IB API historical data connection successful.")
                return app

        if attempt < 2:
            utils.log(f"Retrying... (attempt {attempt + 2}/3)")
            time.sleep(3)

    return None


def getCapital(app, fallbackCapital, maxCapital):
    accountCapital = app.fetchAccountCapital()
    if accountCapital is not None:
        utils.log(f"Account capital (NetLiquidation): ${accountCapital:.2f}, max capital allowed: ${maxCapital:.2f}")
        config.save_settings({"fallback_capital": round(accountCapital, 2)})
        capital = min(accountCapital, maxCapital)
        utils.log(f"Using capital: ${capital:.2f}")
        return capital
    utils.log(f"Could not retrieve account capital, using fallback capital: ${fallbackCapital:.2f}")
    return fallbackCapital


def handleSignalDetails(app, orders) -> list[BOSignal | PBSignal] | None:
    signals = []
    for order in orders:
        ticker = order["ticker"]
        signal_type_str = order["type"]

        bars = app.fetchHistoricalBars(ticker, 1, "D", timeout=10)
        bar = bars[-1] if bars else None
        if bar is None:
            utils.log(f"No historical bar for {ticker}, aborting.")
            return None

        if signal_type_str == "BO":
            action = order["action"]
            stop = bar.low if action == "LONG" else bar.high
            signals.append(BOSignal(
                ticker=ticker,
                bar=bar,
                action=action,
                price=order["price"],
                stop=stop,
            ))
        elif signal_type_str in ("PB_daily", "PB_weekly"):
            signal_type = SignalType.PB_DAILY if signal_type_str == "PB_daily" else SignalType.PB_WEEKLY
            interval = "D" if signal_type == SignalType.PB_DAILY else "W"
            atr = app.fetchATR(ticker, period=20, interval=interval)
            if atr is None:
                utils.log(f"No ATR for {ticker}, aborting.")
                return None
            signals.append(PBSignal(
                ticker=ticker,
                bar=bar,
                atr=atr,
                signal_type=signal_type,
            ))

    return signals


def getRetrySignals(app, signals: list[BOSignal | PBSignal]) -> list[BOSignal | PBSignal]:
    unfilledTickers = []
    for signal in signals:
        order_info = app.getOrderInfo(signal.ticker)
        if order_info is None:
            unfilledTickers.append(signal)
            continue
        if order_info.order_type == OrderType.STP_LMT:
            continue
        if order_info.status != "Filled":
            unfilledTickers.append(signal)
    return unfilledTickers


def handleBOSignal(app, signal: BOSignal, betSize, limitBuffer):
    ticker = signal.ticker
    action = signal.action
    trigger_price = signal.price

    order_info = app.getOrderInfo(ticker)
    bet_size = betSize

    if order_info is not None:
        if order_info.status == "Filled":
            return
        risk_per_share = abs(order_info.avg_fill_price - signal.stop)
        cumulative_risk = app.accumulateFilledRisk(ticker, risk_per_share)
        bet_size = betSize - cumulative_risk
        if bet_size <= 0:
            utils.log(f"No remaining risk for {ticker}, skipping.")
            return

    market_price = app.fetchMarketPrice(ticker, action, timeout=10)
    if market_price is None:
        utils.log(f"No bid/ask for {ticker}, skipping order.")
        return

    is_past = order_utils.is_past_trigger(action, signal.bar.close, trigger_price)
    if order_info is not None and not is_past:
        utils.log(f"Current price {signal.bar.close} not past trigger {trigger_price} for {action} on {ticker}, skipping.")
        return

    ref_price = order_utils.getAcceptableEntry(signal.bar.close, market_price, action) if is_past else trigger_price
    risk = order_utils.calc_bo_risk(action, signal.bar, ref_price, limitBuffer)
    quantity = order_utils.calcQuantity(bet_size, risk)
    if quantity <= 0:
        utils.log(f"Invalid quantity for {ticker}, skipping order.")
        return
    limit_price = order_utils.calc_limit_price(action, ref_price, limitBuffer)
    if is_past:
        app.sendLimitOrder(ticker, action, quantity, limit_price, OrderType.LMT)
        action_word = "Replaced" if order_info is not None else "Placed"
        utils.log(f"{action_word} {action} limit order for {ticker}: qty={quantity}, price={limit_price}")
    else:
        app.sendStopLimitOrder(ticker, action, quantity, ref_price, limit_price, OrderType.STP_LMT)
        utils.log(f"Placed {action} stop limit order for {ticker}: qty={quantity}, stopPrice={ref_price}, limitPrice={limit_price}")


def handlePBSignal(app, signal: PBSignal, betSize, limitBuffer):
    ticker = signal.ticker

    order_info = app.getOrderInfo(ticker)
    bet_size = betSize

    if order_info is not None:
        if order_info.status == "Filled":
            return
        cumulative_risk = app.accumulateFilledRisk(ticker, signal.atr)
        bet_size = betSize - cumulative_risk
        if bet_size <= 0:
            utils.log(f"No remaining risk for {ticker}, skipping replace.")
            return

    market_price = app.fetchMarketPrice(ticker, "LONG", timeout=10)
    if market_price is None:
        utils.log(f"No bid/ask for {ticker}, skipping order.")
        return

    quantity = order_utils.calcQuantity(bet_size, signal.atr)
    if quantity <= 0:
        utils.log(f"Invalid quantity for {ticker}, skipping order.")
        return
    entry_price = order_utils.getAcceptableEntry(signal.bar.close, market_price, "LONG")
    limit_price = order_utils.calc_limit_price("LONG", entry_price, limitBuffer)
    app.sendLimitOrder(ticker, "LONG", quantity, limit_price, OrderType.LMT)
    action_word = "Replaced" if order_info is not None else "Placed"
    utils.log(f"{action_word} PB limit order for {ticker}: qty={quantity}, price={limit_price}, atr={signal.atr:.4f}")


def start(orders):
    cfg = config.read_config()
    host = cfg["host"]
    port = int(cfg["port"])
    clientId = int(cfg["client_id"])
    maxCapital = float(cfg["max_capital"])
    fallbackCapital = float(cfg["fallback_capital"])
    risk = float(cfg["risk"])
    limitBuffer = float(cfg["limit_buffer"])
    betMultiplier = float(cfg.get("bet_multiplier", 1.0))

    if not utils.isWithinRetryWindow(): # last 10 minutes
        utils.log("Not within entry window, exiting...")
        utils.alarm()
        return

    app = launchTWSAPI(host, port, clientId)
    if not app:
        utils.log("Failed to launch IB API application after 3 attempts, exiting...")
        utils.alarm()
        return

    capital = getCapital(app, fallbackCapital, maxCapital)
    betSize = capital * risk * betMultiplier
    utils.log(f"Using bet size: ${betSize:.2f}")

    signals = handleSignalDetails(app, orders)
    if signals is None:
        utils.log("Failed to fetch signal details, exiting...")
        utils.alarm()
        return

    utils.wait_until_ny(57, second=45)
    utils.log("placing orders...")

    for signal in signals:
        if isinstance(signal, BOSignal):
            handleBOSignal(app, signal, betSize, limitBuffer)
        elif isinstance(signal, PBSignal):
            handlePBSignal(app, signal, betSize, limitBuffer)

    time.sleep(10)

    retrySignals = getRetrySignals(app, signals)
    utils.log(f"Unfilled tickers: {[s.ticker for s in retrySignals]}")

    while retrySignals and utils.isWithinRetryWindow():
        for signal in retrySignals:
            order_info = app.getOrderInfo(signal.ticker)
            if order_info is not None:
                if not app.cancelOrderForTicker(signal.ticker):
                    continue
            if isinstance(signal, BOSignal):
                handleBOSignal(app, signal, betSize, limitBuffer)
            elif isinstance(signal, PBSignal):
                handlePBSignal(app, signal, betSize, limitBuffer)
        time.sleep(10)
        retrySignals = getRetrySignals(app, signals)

    utils.log("Cancelling remaining active orders...")
    for signal in retrySignals:
        order_info = app.getOrderInfo(signal.ticker)
        if order_info is not None:
            utils.log(f"Cancelling order for {signal.ticker}")
            app.cancelOrderForTicker(signal.ticker)
    utils.log(f"Unfilled tickers: {[s.ticker for s in retrySignals]}")

    time.sleep(5)
    app.disconnect()
    utils.log("IB API Application stopped\n")
