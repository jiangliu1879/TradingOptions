from datetime import date, datetime
from longport.openapi import QuoteContext, Config
import pandas as pd
import os
from longport.openapi import QuoteContext, Config, Period, AdjustType


config = Config.from_env()
ctx = QuoteContext(config)


def get_stock_close_price(stock_code, start_date, end_date):
    # 获取历史K线数据
    resp = ctx.history_candlesticks_by_date(stock_code, Period.Day, AdjustType.NoAdjust, start_date, end_date)
    return resp[-1].close

def get_options_quote(list_symbol):
    """获取期权实时行情"""
    try:
        resp = ctx.option_quote(list_symbol)
        return resp
    except Exception as e:
        print(f"Error getting options quote: {e}")
        return None

def get_options_chain(stock_code, expiry_date):
    """获取标的的期权链到期日期权标的列表"""
    try:     
        list_option_chain = ctx.option_chain_info_by_date(stock_code, expiry_date)
        print(list_option_chain)
        
        options_data = []
        for item in list_option_chain:
            # StrikePriceInfo对象应该使用属性访问，而不是字典访问
            option_info = {
                'strike_price': item.price,
                'call_symbol': item.call_symbol,
                'put_symbol': item.put_symbol
            }
            options_data.append(option_info)

        return options_data
        
    except Exception as e:
        print(f"Error getting options data: {e}")
        return None

def get_option_data(stock_code: str, expiry_date: date, option_type: str, list_symbol: list, update_time: date):
    list_strike_price = []
    list_volume = []
    list_turnover = []
    list_open_interest = []
    list_quote = get_options_quote(list_symbol)

    stock_close_price = get_stock_close_price(stock_code, update_time, update_time)

    list_data = []
    for quote in list_quote:
        list_data.append({
            'stock_code': stock_code,
            'expiry_date': expiry_date,
            'type': option_type,
            'strike_price': quote.strike_price,
            'volume': quote.volume,
            'turnover': quote.turnover,
            'open_interest': quote.open_interest,
            'update_time': update_time,
            'stock_close_price': stock_close_price,
            'last_done': quote.last_done,
            'prev_close': quote.prev_close,
            'open': quote.open,
            'high': quote.high,
            'low': quote.low,
            'implied_volatility': quote.implied_volatility
            })

    return list_data


def process_options_data(stock_code, expiry_date, update_time, file_name):
    """处理期权数据并保存到CSV"""
    try:
        # 获取期权链数据
        options_chain = get_options_chain(stock_code, expiry_date)
        if not options_chain:
            print("无法获取期权链数据")
            return
        
        # 收集所有期权代码
        call_symbols = []
        put_symbols = []
        for item in options_chain:
            if item['call_symbol']:
                call_symbols.append(item['call_symbol'])
            if item['put_symbol']:
                put_symbols.append(item['put_symbol'])

        call_option_data = get_option_data(stock_code, expiry_date, 'call', call_symbols, update_time)
        import time
        time.sleep(60)
        put_option_data = get_option_data(stock_code, expiry_date, 'put', put_symbols, update_time)

        filename = f"data/options/{file_name}.csv"

        # 检查文件是否存在，决定是否需要写入表头
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile: 
            # 2. 指定列名（字段名）
            fieldnames = call_option_data[0].keys()
            print(fieldnames)
            # 创建 DictWriter 对象
            import csv
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # 3. 如果文件不存在，写入表头（即列名）
            if not file_exists:
                writer.writeheader() 
            # 4. 写入所有行数据
            writer.writerows(call_option_data + put_option_data) 

    except Exception as e:
        print(f"Error processing options data: {e}")

if __name__ == "__main__":
    # list_stock_code = ["NVDA.US", "AAPL.US", "HIMS.US", "HOOD.US", "CRWV.US", "AMZN.US", "LMND.US", "FIG.US", "GOOG.US", "ORCL.US", "BE.US", "PLTR.US", "TSM.US"]
    # for stock_code in list_stock_code:
    #     print(f"{stock_code}")
    #     process_options_data(stock_code, date(2025, 10, 10), date(2025, 10, 10), "stock_options_data")

    list_stock_code = ["SPY.US"]
    for stock_code in list_stock_code:
        process_options_data(stock_code, date(2025, 10, 15), date(2025, 10, 15), "spy_options_data")

