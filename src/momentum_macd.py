# Momentum algorithm based on MACD
from datetime import date, timedelta

import talib
import numpy as np
import pandas as pd

def initialize(context):
    # securities with prices > 100$ and market cap > 10bn$
    set_symbol_lookup_date('2015-01-01')
    context.symbols=symbols('AAPL', 'AAP',  'ABC',  'ACT', 'ADS', 'AGN','ALXN', 'AMG',  'AMGN', 'AMP',  'AMZN', 'ANTM', 'APD',  'AVB',  'AZO',  'BA',   'BCR',  'BDX',  'BIIB', 'BLK',  'BMRN', 'BXP',  'CB',   'CELG', 'CF',   'CHTR', 'CI',   'CLX',  'CMG',  'CMI',  'COST', 'CVS',  'CVX',  'CXO',  'DIS',  'ECL',  'EQIX', 'ESS',  'EW',   'FDX',  'FLT',  'GD',   'GILD', 'GMCR', 'GS',   'GWW',  'HBI',  'HD',   'HON',  'HSIC', 'HSY',  'HUM',  'IBM',  'ICE',  'IEP',  'ILMN', 'ISRG', 'IVV',  'KMB',  'KSU',  'LLL',  'LMT',  'LNKD', 'MCK',  'MHFI', 'MHK',  'MJN',  'MKL',  'MMM',  'MNST', 'MON',  'MPC',  'MTB',  'NEE',  'NFLX', 'NOC',  'NSC',  'ORLY', 'PANW', 'PCLN', 'PCP',  'PCYC', 'PH',   'PII',  'PLL',  'PPG',  'PSA',  'PX',   'PXD',  'REGN', 'RL',   'ROK',  'ROP',  'RTN',  'SBAC', 'SHW',  'SIAL', 'SJM',  'SLG',  'SPG',  'SRCL', 'SRE',  'STZ',  'TDG',  'TMO',  'TRV',  'TRW',  'TSLA', 'TWC',  'UHS',  'UNH',  'UNP',  'UPS',  'UTX',  'V',    'VNO',  'VRTX', 'WDC',  'WHR',  'WYNN', 'ZMH')
    # GOOG
    context.num_positions = 10
    context.hold_days = 4
    context.position_size = context.portfolio.cash/context.num_positions
    context.position_sell_dates = {}
    context.position_highs = {}
    context.date = None
    set_commission(commission.PerTrade(cost=0.03))
    set_slippage(slippage.VolumeShareSlippage(volume_limit=0.25, price_impact=0.1))

def handle_data(context, data):
    todays_date = get_datetime().date()
    if todays_date == context.date:
        return
    
    context.date = todays_date
    
    rebalance(context, data)
    record(num_positions=openPositions(context))
    record(leverage=context.account.leverage)
    
def rebalance(context,data):
    context.open_buys = 0
    prices = history(40, '1d', 'price')
    prices.dropna(axis=0)
    macd_data = prices.apply(MACD, fastperiod=12, slowperiod=20, signalperiod=3)
        
    # Sell some shares
    #for security,position in context.portfolio.positions.iteritems():
    for security in context.symbols:
        symbol = security.symbol
        
        position = context.portfolio.positions[security]
        if position.amount == 0:
            continue
        
        price = data[security].close_price
        trailing_limit = data[security].mavg(2)*(1 - 0.07)
        hard_limit = position.cost_basis*(1-0.07)
        
        if symbol in context.position_sell_dates:
            sell_date = context.position_sell_dates[symbol]
            if context.date >= sell_date:
                order_target(security, 0)
                log.info("Selling %s due to sell_date %s<=%s" % (symbol, sell_date, context.date))
                continue
        
        if symbol in macd_data and macd_data[symbol] < 0:
            order_target(security, 0)
            log.info("Selling %s due to MACD(%f) < 0" % (symbol, macd_data[symbol]))
            continue
        
        if price < trailing_limit:
            order_target(security, 0)
            log.info("Selling %s due to price(%f) < trailing stop limit(%f)" % (symbol, price, trailing_limit))
            continue
        
        if price < hard_limit:
            order_target(security, 0)
            log.info("Selling %s due to price(%f) < stop limit(%f)" % (symbol, price, hard_limit))
            continue
            
    for security,signal in stockSelection(context,macd_data):
        # go long
        if signal > 0 and canBuy(context,data,security):
            current_price = data[security].close_price
            number_of_shares = int(context.position_size/current_price)
            log.info("Buying %s (%f) due to MACD(%f) > 0" % (security.symbol, number_of_shares, signal))
            
            # Place the buy as limitOrder
            limit_price = current_price
            order(security, +number_of_shares, style=LimitOrder(limit_price))
            context.open_buys += 1
            sell_date = get_datetime().date() + timedelta(context.hold_days)
            context.position_sell_dates[security.symbol] = sell_date
    
def canBuy(context,data,security):
    free_cash = context.portfolio.cash
    price = data[security].close_price
    no_position = context.portfolio.positions[security].amount == 0
    open_positions = openPositions(context) + context.open_buys
    #log.info("can buy open=%f, free_cash=%f, no_position=%s" % (open_positions, cash, no_position))
    return (open_positions < context.num_positions) and (free_cash > price) and no_position

def openPositions(context):
    num = 0
    for security,position in context.portfolio.positions.iteritems():
        if position.amount != 0:
            num += 1
    return num

def stockSelection(context, macd_data):
    # calculate EPS growth
    stocks = []
    for security in context.symbols:
        if not security in macd_data:
            log.debug("No data for security %s" % (security))
            continue
        
        stocks.append((security, macd_data[security]))
        
    stocks.sort(key=lambda t: t[1])
    return stocks
        
def MACD(prices, fastperiod=12, slowperiod=26, signalperiod=9):
    '''
    Function to return the difference between the most recent 
    MACD value and MACD signal. Positive values are long
    position entry signals 

    optional args:
        fastperiod = 12
        slowperiod = 26
        signalperiod = 9

    Returns: macd - signal
    '''
    macd, signal, hist = talib.MACD(prices, 
                                    fastperiod=fastperiod, 
                                    slowperiod=slowperiod, 
                                    signalperiod=signalperiod)
    return macd[-1] - signal[-1]

  
