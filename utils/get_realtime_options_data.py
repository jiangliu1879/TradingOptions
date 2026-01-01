from datetime import date, datetime
import pytz
from longport.openapi import QuoteContext, Config
import pandas as pd
import os
import sys
from longport.openapi import QuoteContext, Config, Period, AdjustType

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.options_data import OptionsData


config = Config.from_env()
ctx = QuoteContext(config)

def get_eastern_time():
    """获取美东当前时间"""
    # 美东时区
    eastern = pytz.timezone('US/Eastern')
    # 获取当前UTC时间并转换为美东时间
    utc_now = datetime.now(pytz.UTC)
    eastern_time = utc_now.astimezone(eastern)
    return eastern_time

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

def get_stock_realtime_price(stock_code):
    """获取股票实时行情"""
    try: 
        resp = ctx.quote([stock_code])
        for item in resp:
            if item.symbol == stock_code:
                return item.last_done
        return None
    except Exception as e:
        print(f"Error getting stock realtime price: {e}")
        return None

def get_option_data(stock_code: str, expiry_date: date, option_type: str, list_symbol: list, update_time: str):
    list_strike_price = []
    list_volume = []
    list_turnover = []
    list_open_interest = []
    list_quote = get_options_quote(list_symbol)

    list_data = []
    for quote in list_quote:
        list_data.append({
            'stock_code': stock_code,
            'expiry_date': expiry_date,
            'symbol': quote.symbol,
            'update_time': update_time,
            'type': option_type,
            'strike_price': float(quote.strike_price) if quote.strike_price else 0.0,
            'volume': int(quote.volume) if quote.volume else 0,
            'turnover': float(quote.turnover) if quote.turnover else 0.0,
            'open_interest': int(quote.open_interest) if quote.open_interest else 0,
            'implied_volatility': float(quote.implied_volatility) if quote.implied_volatility else 0.0,
            'contract_size': int(quote.contract_size) if quote.contract_size else 100
            })

    return list_data


def process_options_data(stock_code, expiry_date, update_time, save_to_database: bool = True):
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
        
        print(f"处理完成：{len(call_option_data)} 个看涨期权，{len(put_option_data)} 个看跌期权")

        # 合并所有期权数据
        all_options_data = call_option_data + put_option_data
        
        # 保存到数据库
        if save_to_database:
            saved_count = OptionsData.save_options_data(all_options_data)
            print(f"数据库保存完成：{saved_count} 条记录")

        return all_options_data
        
    except Exception as e:
        print(f"处理期权数据时出错: {e}")
        return

if __name__ == "__main__":
    # 获取并显示美东当前时间
    # eastern_time = get_eastern_time()
    # update_time = eastern_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # process_options_data("SPY.US", date(2025, 10, 14), update_time)

    stock_price = get_stock_realtime_price("VIX.US")
    print(stock_price)

