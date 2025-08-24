import time
from datetime import datetime, time as dtime
import pytz

from IBAPIApp import IBAPIApp
import utils
import config

def getUnfilledTickers(app, orders):
    unfilled = set()
    for order in orders:
        ticker = order["ticker"]
        orderId = app.tickerOrderIdDict.get(ticker)
        if orderId is None:
            unfilled.add(ticker)
            continue
        status = app.getOrderStatus(orderId)
        if status != "Filled":
            unfilled.add(ticker)
    return unfilled

def isWithinRetryWindow():
    ny_tz = pytz.timezone("America/New_York")
    now_ny = datetime.now(ny_tz).time()
    return dtime(15, 57) <= now_ny < dtime(16, 0)

def start(orders):
    cfg = config.read_config()
    host = cfg["host"]
    port = int(cfg["port"])
    clientId = int(cfg["client_id"])
    capital = float(cfg["capital"])
    risk = float(cfg["risk"])
    limitBuffer = float(cfg["limit_buffer"])

    if not isWithinRetryWindow():
        utils.log("Not within entry window, exiting...")
        return
    
    utils.log("Launching IB API application...")
    app = IBAPIApp(host, port, clientId)
    time.sleep(5)
    if app.nextOrderId == 0:
        utils.log("Failed to connect to IB API, exiting...")
        return

    tickerActionDict = {}

    for order in orders:
        ticker = order["ticker"]
        action = order["action"]
        triggerPrice = order["price"]
        tickerActionDict[ticker] = action
        contract = app.createContract(ticker)
        reqId = app.nextRequestID()
        app.tickerReqIdDict[ticker] = reqId
        app.reqData(reqId, contract)

        if not app.waitForData(ticker, action, timeout=10):
            utils.log(f"No OHLC data for {ticker}, skipping order.")
            continue

        bar = app.tickerData[reqId]
        entryPrice = bar.close
        if action == "LONG":
            entryPrice = app.tickerAsk.get(reqId, bar.close)
        elif action == "SHORT":
            entryPrice = app.tickerBid.get(reqId, bar.close)
        entryPrice = utils.getAcceptableEntry(bar.close, entryPrice)
        quantity = utils.calcQuantity(action, bar, entryPrice, limitBuffer, capital * risk)
        if quantity <= 0:
            utils.log(f"Invalid quantity for {ticker}, skipping order.")
            continue

        orderId = app.nextRequestID()
        app.tickerOrderIdDict[ticker] = orderId
        if action == "LONG":
            if bar.close > triggerPrice:
                limitPrice = entryPrice + limitBuffer
                app.sendLimitOrder(orderId, contract, "BUY", quantity, limitPrice)
                utils.log(f"Placed LONG limit order for {ticker}: qty={quantity}, price={limitPrice}")
            else:
                utils.log(f"Current price {bar.close} is below trigger price {triggerPrice} for LONG order on {ticker}, skipping.")
        elif action == "SHORT":
            if bar.close < triggerPrice:
                limitPrice = entryPrice - limitBuffer
                app.sendLimitOrder(orderId, contract, "SELL", quantity, limitPrice)
                utils.log(f"Placed SHORT limit order for {ticker}: qty={quantity}, price={limitPrice}")
            else:
                utils.log(f"Current price {bar.close} is above trigger price {triggerPrice} for SHORT order on {ticker}, skipping.")


    time.sleep(10)
    
    # Use the helper function to get unfilled tickers
    unfilledTickers = getUnfilledTickers(app, orders)
    utils.log(f"Unfilled tickers: {unfilledTickers}")
    while unfilledTickers and isWithinRetryWindow():
        for order in orders:
            ticker = order["ticker"]
            action = order["action"]
            if ticker not in unfilledTickers:
                continue
            orderId = app.tickerOrderIdDict.get(ticker)
            if orderId is None:
                continue

            contract = app.createContract(ticker)
            utils.log(f"Order for {ticker} not filled, requesting new data and replacing order...")

            # Request new bar data
            newReqId = app.nextRequestID()
            app.tickerReqIdDict[ticker] = newReqId
            app.reqData(newReqId, contract)

            if not app.waitForData(ticker, action, timeout=10):
                utils.log(f"No new OHLC data or Bid/Ask for {ticker}, skipping replace.")
                continue

            newBar = app.tickerData[newReqId]

            # Calculate filled quantity and capital used so far
            filledQty = app.orderFilledDict.get(orderId, 0)
            avgFillPrice = app.orderAvgFillPrice.get(orderId, 0)
            stopValue = newBar.low
            if action == "SHORT":
                stopValue = newBar.high
            
            dollarRisk = abs(avgFillPrice - stopValue) * filledQty

            # Calculate remaining bet size
            totalBetSize = capital * risk
            remainingBetSize = totalBetSize - dollarRisk
            if remainingBetSize <= 0:
                utils.log(f"No remaining risk for {ticker}, skipping replace.")
                continue


            entryPrice = newBar.close
            if action == "LONG":
                entryPrice = app.tickerAsk.get(newReqId, newBar.close)
            elif action == "SHORT":
                entryPrice = app.tickerBid.get(newReqId, newBar.close)
            entryPrice = utils.getAcceptableEntry(newBar.close, entryPrice)
            newQty = utils.calcQuantity(action, newBar, entryPrice, limitBuffer, remainingBetSize)
            if newQty <= 0:
                utils.log(f"No remaining quantity {newQty} for {ticker}, skipping replace.")
                continue

            status = app.getOrderStatus(orderId)
            if status == "Filled":
                utils.log(f"Order for {ticker} filled.")
                continue

            # Use the same orderId to replace the existing order
            if action == "LONG":
                if newBar.close > triggerPrice:
                    newLimitPrice = entryPrice + limitBuffer
                    app.sendLimitOrder(orderId, contract, "BUY", newQty, newLimitPrice)
                    utils.log(f"Replaced LONG limit order for {ticker}: qty={newQty}, price={newLimitPrice}")
                else:
                    utils.log(f"Current price {newBar.close} is below trigger price {triggerPrice} for LONG order on {ticker}, skipping.")
            elif action == "SHORT":
                if newBar.close < triggerPrice:
                    newLimitPrice = entryPrice - limitBuffer
                    app.sendLimitOrder(orderId, contract, "SELL", newQty, newLimitPrice)
                    utils.log(f"Replaced SHORT limit order for {ticker}: qty={newQty}, price={newLimitPrice}")
                else:
                    utils.log(f"Current price {newBar.close} is above trigger price {triggerPrice} for SHORT order on {ticker}, skipping.")

        time.sleep(10)
        unfilledTickers = getUnfilledTickers(app, orders)

    time.sleep(5)
    app.disconnect()
    utils.log("IB API Application stopped")


# orders = [
#      {
#           "ticker": "AAPL",
#           "action": "LONG",
#           "price": 150.00
#      },
#      {
#           "ticker": "GOOGL",
#           "action": "SHORT",
#           "price": 150.00
#      },
# ]

# start(orders)