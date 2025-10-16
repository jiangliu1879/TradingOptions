"""
期权数据查询脚本

这个脚本演示如何查询和分析期权数据库中的数据。
"""

import os
import sys
from datetime import date

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.options_data import OptionsData

def query_options_analysis():
    """查询和分析期权数据"""
    print("🔍 期权数据分析")
    print("=" * 50)
    
    # 1. 获取所有股票代码
    print("📊 可用的股票代码:")
    stock_codes = OptionsData.get_stock_codes()
    for code in stock_codes:
        print(f"   - {code}")
    print()
    
    # 2. 获取所有到期日期
    print("📅 可用的到期日期:")
    expiry_dates = OptionsData.get_expiry_dates()
    for exp_date in expiry_dates:
        print(f"   - {exp_date}")
    print()
    
    # 3. 获取SPY的最新期权数据（前10条）
    print("📈 SPY最新期权数据 (前10条):")
    latest_options = OptionsData.get_latest_options_data("SPY.US")
    for i, option in enumerate(latest_options[:10]):
        print(f"   {i+1:2d}. {option.symbol} | {option.type.upper()} | Strike: ${option.strike_price:.0f} | OI: {option.open_interest:,} | IV: {option.implied_volatility:.3f}")
    print()
    
    # 4. 获取看涨期权数据
    print("📈 SPY看涨期权数据 (前5条):")
    call_options = OptionsData.get_options_data(stock_code="SPY.US", option_type="call", limit=5)
    for i, option in enumerate(call_options):
        print(f"   {i+1:2d}. {option.symbol} | Strike: ${option.strike_price:.0f} | OI: {option.open_interest:,} | IV: {option.implied_volatility:.3f}")
    print()
    
    # 5. 获取看跌期权数据
    print("📉 SPY看跌期权数据 (前5条):")
    put_options = OptionsData.get_options_data(stock_code="SPY.US", option_type="put", limit=5)
    for i, option in enumerate(put_options):
        print(f"   {i+1:2d}. {option.symbol} | Strike: ${option.strike_price:.0f} | OI: {option.open_interest:,} | IV: {option.implied_volatility:.3f}")
    print()
    
    # 6. 获取行权价范围
    if expiry_dates:
        print("💰 SPY行权价范围分析:")
        strike_range = OptionsData.get_strike_price_range("SPY.US", expiry_dates[0])
        if strike_range:
            print(f"   - 最低行权价: ${strike_range['min_strike']:.0f}")
            print(f"   - 最高行权价: ${strike_range['max_strike']:.0f}")
            print(f"   - 行权价区间: ${strike_range['strike_range']:.0f}")
            print(f"   - 期权合约总数: {strike_range['records_count']:,}")
        print()
    
    # 7. 统计信息
    print("📊 数据统计:")
    total_options = OptionsData.get_options_data(stock_code="SPY.US")
    call_count = len([opt for opt in total_options if opt.type == "call"])
    put_count = len([opt for opt in total_options if opt.type == "put"])
    
    print(f"   - 总期权合约数: {len(total_options):,}")
    print(f"   - 看涨期权数: {call_count:,}")
    print(f"   - 看跌期权数: {put_count:,}")
    print(f"   - 看涨/看跌比例: {call_count/put_count:.2f}")
    
    # 计算总持仓量
    total_open_interest = sum([opt.open_interest for opt in total_options if opt.open_interest])
    print(f"   - 总持仓量: {total_open_interest:,}")

if __name__ == "__main__":
    query_options_analysis()
