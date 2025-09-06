import MetaTrader5 as mt5
import pandas as pd
import time
import talib as ta
import numpy as np


account_id = 159584904  
password = "rAI@#12345"  # Replace with your actual password
server = "Exness-MT5Real20"  # Replace with your broker's server name
path = r'C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe'

# Initialize connection to the terminal
if not mt5.initialize(path= path, login=account_id, password=password, server=server):
    print("Initialization failed, error code:", mt5.last_error())
    quit()

# Confirm login
account_info = mt5.account_info()
if account_info is None:
    print("Failed to retrieve account info, error code:", mt5.last_error())
else:
    print("Logged in successfully to account #", account_info.login)




def get_data_only_close_high_low_open(symbol = "EURUSD",
                                       timeframe = mt5.TIMEFRAME_H4,
                                         last = 250):
   

    # Get data
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, last)  # Get the last 100 candles

    # Shutdown connection to MetaTrader 5

    # Convert to pandas DataFrame
    history = pd.DataFrame(rates)
   
    

    #if 'time' not in history.columns:
        #history['time'] = [bar['time'] for bar in rates]  # if rates is a lis
    # Convert time in seconds into datetime
    history['time'] = pd.to_datetime(history['time'], unit='s')
    history.set_index('time', inplace=True)
    history = history[['open','high', 'low', 'close']]

    return history



def add_multiframe_condition(symbol = 'EURUSD', timeframe = mt5.TIMEFRAME_M15,
                              timeframe_higher = mt5.TIMEFRAME_H4,
                            sh_window = 25,
                            eh_window = 8,
                             last = 250 ):
    
    df = get_data_only_close_high_low_open(symbol = symbol,
                                            timeframe = timeframe,
                                              last = last)
    df_higher = get_data_only_close_high_low_open(symbol = symbol, 
                                                  timeframe = timeframe_higher,
                                                    last = last)

    

    df_higher['fast'] = ta.EMA(df_higher['close'],timeperiod=eh_window)
    df_higher['slow'] = ta.SMA(df_higher['close'], timeperiod=sh_window)
    df_higher['trend'] = np.where(df_higher['fast'] > df_higher['slow'], 1, -1)

    df = pd.merge_asof(df.sort_index(), 
                       df_higher[['trend']].sort_index(),
                       left_index=True, right_index=True,
                       direction='backward')
    
    return df



def signals_rsi_ema_ma_trend( 
        symbol = 'EURUSD', timeframe = mt5.TIMEFRAME_M15,
                timeframe_higher = mt5.TIMEFRAME_H4,
                sh_window = 25,
                eh_window = 8,
                rsi_window = 14,
                rsi_oversold_para = 30,
                rsi_overbought_para = 70,
                ema_window = 8,
                sma_window =20,                
                rsi_active_overbought = 55,
                rsi_active_oversold = 45, 
                last = 250             
                ):
    
    



    df = add_multiframe_condition(symbol=symbol, timeframe=timeframe,
                                  timeframe_higher=timeframe_higher,
                                  sh_window=sh_window,
                                  eh_window=eh_window,
                                  last = last)

    close = df['close'].to_numpy()
    trend = df['trend'].to_numpy()
   
    rsi = ta.RSI(close, timeperiod = rsi_window) 
    ema = ta.EMA(close, timeperiod = ema_window)
    sma = ta.SMA(close, timeperiod = sma_window)

    # initiate empty signal numpy array
    signal = np.zeros(len(close))
    

    # condition for confirmation
    ema_sma_long = ema >= sma
    ema_sma_short = ema < sma
    oversold_condition = rsi <= rsi_oversold_para
    overbought_condition = rsi >= rsi_overbought_para



    # placeholder for rsi overbought/sold value track until thresold
    in_long = False
    in_short = False

    
    # looping through for generating signal
    for i in range(len(close)):
        if not in_long and oversold_condition[i] and trend[i] == 1:
            in_long = True
            
            if ema_sma_long[i]:
                signal[i] = 1
                in_long = False                
                continue

        elif in_long:
            if ema_sma_long[i] and trend[i] == 1:
                signal[i] = 1
                in_long = False                
                continue

            elif rsi[i] >= rsi_active_oversold:
                in_long = False                
                continue


        if not in_short and overbought_condition[i] and trend[i] == -1:
            in_short = True
            
            if ema_sma_short[i] :
                signal[i] = -1
                in_short = False                
                continue

        elif in_short:
            if  ema_sma_short[i] and trend[i] == -1:
                signal[i] = -1
                in_short = False                
                continue

            elif rsi[i] <= rsi_active_overbought:
                in_short = False                
                continue    

    # returning last candle signals
    if signal[-1] == 1:
        return 'buy'
    elif signal[-1] == -1:
        return 'sell'
    else:
        return 'hold'
    

# placing order
    
def place_order(order_type, lot = .1,  deviation = 300, 
                symbol = "XAUUSD", pips_loss = 300,
                pips_profit = 500):

    point = mt5.symbol_info(symbol).point
    price = mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid

    if order_type == mt5.ORDER_TYPE_BUY:        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": price - (pips_loss * point),
            "tp": price +  (pips_profit * point),
            "deviation": deviation,
            "magic": 123456,
            "comment": "AutoTrade adx_rsi",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
    else:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": price + (pips_loss * point),
            "tp": price - (pips_profit * point),
            "deviation": deviation,
            "magic": 123456,
            "comment": "AutoTrade MA Crossover",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
    result = mt5.order_send(request)
    print("Order result:", result)


# closing order in reverse condition 
def close_position(position):
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY,
        "position": position.ticket,
        "price": mt5.symbol_info_tick(position.symbol).ask if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(position.symbol).bid,
        "deviation": 10,
        "magic": 123456,
        "comment": "Close position",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(close_request)
    print("Close position result:", result)


# live trading func for single symbol

def live_trading(symbol = 'EURUSD', 
        timeframe = mt5.TIMEFRAME_M15,                
        timeframe_higher = mt5.TIMEFRAME_H4,
        sh_window = 25,
        eh_window = 8,
        rsi_window = 14,
        rsi_oversold_para = 30,
        rsi_overbought_para = 70,
        ema_window = 8,
        sma_window =20,                
        rsi_active_overbought = 55,
        rsi_active_oversold = 45,  
        lot = 1.00, 
        pips_loss = 5170,
        pips_profit = 10350,
        last = 250
        ):
    


    
    


    signal = signals_rsi_ema_ma_trend( 
        symbol = symbol, 
        timeframe = timeframe,                
        timeframe_higher = timeframe_higher,
        sh_window = sh_window,
        eh_window = eh_window,
        rsi_window = rsi_window,
        rsi_oversold_para = rsi_oversold_para,
        rsi_overbought_para = rsi_overbought_para,
        ema_window = ema_window,
        sma_window =sma_window,                
        rsi_active_overbought = rsi_active_overbought,
        rsi_active_oversold = rsi_active_oversold, 
        last = last,               
                )
    
    if signal == 'hold':
        pass
        #print(f"No trading signal for {symbol}")
        
    
    else:
        positions = mt5.positions_get(symbol=symbol)
        
        try:
            if positions == ():
                if signal == 'buy':
                    print('placing buy order')
                    place_order(order_type=mt5.ORDER_TYPE_BUY, lot = lot, symbol=symbol, pips_loss=pips_loss, pips_profit=pips_profit)

                elif signal == 'sell':
                    print('placing sell order')
                    place_order(order_type=mt5.ORDER_TYPE_SELL, lot = lot, symbol=symbol, pips_loss=pips_loss, pips_profit=pips_profit)
                
                    
                    

            elif positions[-1].type == 0 and signal == 'sell':
                close_position(positions[-1])
                place_order(order_type=mt5.ORDER_TYPE_SELL, lot = lot, symbol=symbol, pips_loss=pips_loss, pips_profit=pips_profit)
            elif positions[-1].type == 1 and signal == 'buy':
                close_position(positions[-1])
                place_order(order_type=mt5.ORDER_TYPE_BUY, lot=lot, symbol=symbol, pips_loss=pips_loss, pips_profit=pips_profit)
            else:
                pass
            
        except Exception as e:
            print(f"Error: {e}")
        print(f'Current signal for {symbol}:', signal)   
        


# multiple asset, same strategy, not complete
def multi_live_trading(sym_matrix):
    while True:
        for i in sym_matrix:
           
            

            live_trading(symbol=i['symbol'], 
                         timeframe=i['timeframe'], 
                         timeframe_higher= i['timeframe_higher'], 
                         sh_window= i['sh_window'],
                         eh_window=i['eh_window'],
                         rsi_overbought_para=i['rsi_overbought_para'],
                         rsi_oversold_para=i['rsi_oversold_para'],
                         ema_window=i['ema_window'],
                         sma_window=i['sma_window'],
                         rsi_active_oversold=i['rsi_active_oversold'],
                         rsi_active_overbought=i['rsi_active_overbought'],
                         lot = i['lot'],
                         pips_loss = i['pips_loss'],
                         pips_profit = i['pips_profit'])
        
        time.sleep(60)


if __name__ == "__main__":
    
    

    symbol_matrix = [{'symbol': "XAUUSDc" , 'timeframe':mt5.TIMEFRAME_M2,
                      'timeframe_higher': mt5.TIMEFRAME_M10,
                      'sh_window':20,
                      'eh_window':8, 'rsi_window':14,
                       'rsi_overbought_para':55,
                      'rsi_oversold_para':45, 'ema_window': 10,
                      'sma_window': 20, 'rsi_active_overbought': 35,
                      'rsi_active_oversold': 65,
                      'lot' : .04,
                      'pips_loss': 5170, 'pips_profit': 9500},

                      {'symbol': "USDJPYc" , 'timeframe':mt5.TIMEFRAME_M1,
                      'timeframe_higher': mt5.TIMEFRAME_M15,
                      'sh_window':25,
                      'eh_window':8, 'rsi_window':14,
                      'rsi_overbought_para':60,
                      'rsi_oversold_para':40, 'ema_window': 10,
                      'sma_window': 20, 'rsi_active_overbought': 45,
                      'rsi_active_oversold':55,
                      'lot' : .15,
                      'pips_loss': 120, 'pips_profit': 280},

                     
                      ]




    live = True
    
   

    if live == True:
        try:
            multi_live_trading(symbol_matrix)
        except KeyboardInterrupt:
            print("Live trading loop interrupted.")
        finally:
            mt5.shutdown()
    else:
        mt5.shutdown()