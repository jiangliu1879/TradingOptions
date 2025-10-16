from datetime import date, datetime
from longport.openapi import QuoteContext, Config
import pandas as pd
import os
import sys
from longport.openapi import QuoteContext, Config, Period, AdjustType
from collections import defaultdict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.max_pain_calculator import MaxPainCalculator
from models.stock_max_pain_result import StockMaxPainResult


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


def calculate_and_save_max_pain(stock_code: str, expiry_date: date, call_option_data: list, put_option_data: list, stock_close_price: float):
    """
    计算最大痛点并保存到数据库
    
    Args:
        stock_code: 股票代码
        expiry_date: 到期日期
        call_option_data: call期权数据列表
        put_option_data: put期权数据列表
        stock_close_price: 股票收盘价
    """
    try:
        # 合并call和put期权数据
        all_option_data = call_option_data + put_option_data
        
        # 按行权价分组期权数据
        grouped_data = defaultdict(lambda: {"volume": {"put": 0, "call": 0}, "open_interest": {"put": 0, "call": 0}})
        
        for option in all_option_data:
            strike_price = option['strike_price']
            option_type = option['type']
            volume = option['volume']
            open_interest = option['open_interest']
            
            grouped_data[strike_price]["volume"][option_type] = volume
            grouped_data[strike_price]["open_interest"][option_type] = open_interest
        
        # 转换为MaxPainCalculator需要的格式
        data_list = []
        for strike_price in sorted(grouped_data.keys()):
            data_list.append({strike_price: grouped_data[strike_price]})
        
        if not data_list:
            print(f"⚠️ 没有期权数据可用于计算最大痛点")
            return
        
        # 使用MaxPainCalculator计算最大痛点
        max_pain_result = MaxPainCalculator.calculate_max_pain_from_options_data(data_list, include_volume_std=True)
        
        # 准备数据库数据
        db_data = {
            'stock_code': stock_code,
            'expiry_date': expiry_date,
            'stock_close_price': stock_close_price,
            'max_pain_price_volume': max_pain_result['max_pain_price_volume'],
            'max_pain_price_open_interest': max_pain_result['max_pain_price_open_interest'],
            'sum_volume': max_pain_result['sum_volume'],
            'volume_std_deviation': max_pain_result['volume_std_deviation'],
            'sum_open_interest': max_pain_result['sum_open_interest']
        }
        
        # 确保数据库表存在
        StockMaxPainResult.create_tables()
        
        # 保存到数据库
        saved_count = StockMaxPainResult.save_stock_max_pain_results([db_data])
        
        print(f"✅ {stock_code} - {expiry_date} 最大痛点计算完成:")
        print(f"   基于Volume: ${max_pain_result['max_pain_price_volume']:.0f}")
        print(f"   基于Open Interest: ${max_pain_result['max_pain_price_open_interest']:.0f}")
        print(f"   股票收盘价: ${stock_close_price:.2f}")
        print(f"   总成交量: {max_pain_result['sum_volume']:,}")
        print(f"   总持仓量: {max_pain_result['sum_open_interest']:,}")
        print(f"   Volume标准差: {max_pain_result['volume_std_deviation']:.2f}")
        print(f"   保存状态: {'成功' if saved_count > 0 else '已存在'}")
        
    except Exception as e:
        print(f"❌ 计算最大痛点失败: {e}")
        import traceback
        traceback.print_exc()


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
        put_option_data = get_option_data(stock_code, expiry_date, 'put', put_symbols, update_time)

        # 获取股票收盘价（用于max pain计算）
        stock_close_price = get_stock_close_price(stock_code, update_time, update_time)

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

        # 计算并保存最大痛点到数据库
        print(f"\n🧮 开始计算 {stock_code} - {expiry_date} 的最大痛点...")
        calculate_and_save_max_pain(stock_code, expiry_date, call_option_data, put_option_data, stock_close_price) 

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

