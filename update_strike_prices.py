"""
更新 max_pain_results 表中的 volume_strike_price 和 open_interest_strike_price 字段

该脚本会：
1. 读取 max_pain_results 表中的所有数据
2. 对每条记录，根据 stock_code、expiry_date、update_time 重新计算最大痛点
3. 使用计算得到的 volume_strike_price 和 open_interest_strike_price 更新数据库
"""

import os
import sys
from datetime import date
from collections import defaultdict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.max_pain_result import MaxPainResult
from models.options_data import OptionsData
from utils.max_pain_calculator import MaxPainCalculator


def process_options_data_for_max_pain(stock_code: str, expiry_date: date, update_time: str):
    """
    处理期权数据用于计算最大痛点
    
    Args:
        stock_code: 股票代码
        expiry_date: 到期日期
        update_time: 更新时间
        
    Returns:
        list: 处理后的期权数据列表
    """
    try:
        # 通过三个条件精确查询期权数据
        options_records = OptionsData.get_options_data(
            stock_code=stock_code, 
            expiry_date=expiry_date,
            update_time=update_time
        )
        
        if not options_records:
            print(f"⚠️  未找到 {stock_code} 在 {expiry_date} {update_time} 的期权数据")
            return []
        
        # 按行权价分组数据
        grouped_data = {}
        for record in options_records:
            strike_price = float(record.strike_price)
            
            if strike_price not in grouped_data:
                grouped_data[strike_price] = {
                    "volume": {"put": 0, "call": 0},
                    "open_interest": {"put": 0, "call": 0}
                }
            
            # 更新对应类型的volume和open_interest
            if record.volume:
                grouped_data[strike_price]["volume"][record.type] = int(record.volume)
            if record.open_interest:
                grouped_data[strike_price]["open_interest"][record.type] = int(record.open_interest)
        
        # 转换为列表格式并按行权价排序
        sorted_strikes = sorted(grouped_data.keys())
        data_list = [{strike: grouped_data[strike]} for strike in sorted_strikes]
        
        return data_list
        
    except Exception as e:
        print(f"❌ 处理期权数据失败: {e}")
        import traceback
        print(traceback.format_exc())
        return []


def update_strike_prices():
    """更新 max_pain_results 表中的 strike price 字段"""
    print("=" * 60)
    print("🔄 开始更新 max_pain_results 表中的 strike price 字段")
    print("=" * 60)
    print()
    
    # 获取所有 max_pain_results 记录
    print("📊 读取 max_pain_results 表中的所有数据...")
    all_results = MaxPainResult.get_max_pain_results()
    
    if not all_results:
        print("⚠️  数据库中没有 max_pain_results 数据")
        return
    
    total_count = len(all_results)
    print(f"✅ 找到 {total_count} 条记录")
    print()
    
    # 统计信息
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    session = MaxPainResult.get_session()
    
    try:
        for idx, result in enumerate(all_results, 1):
            stock_code = result.stock_code
            expiry_date = result.expiry_date
            update_time = result.update_time
            
            print(f"[{idx}/{total_count}] 处理: {stock_code} | {expiry_date} | {update_time}")
            
            # 获取期权数据
            data_list = process_options_data_for_max_pain(stock_code, expiry_date, update_time)
            
            if not data_list:
                print(f"  ⚠️  跳过：没有找到期权数据")
                skipped_count += 1
                continue
            
            # 计算最大痛点
            max_pain_result = MaxPainCalculator.calculate_max_pain_from_options_data(data_list)
            
            if not max_pain_result:
                print(f"  ⚠️  跳过：计算失败")
                failed_count += 1
                continue
            
            # 获取计算得到的 strike price 值
            volume_strike_price = max_pain_result.get('volume_strike_price', 0)
            open_interest_strike_price = max_pain_result.get('open_interest_strike_price', 0)
            
            # 更新数据库记录
            try:
                # 查询当前记录
                record = (session.query(MaxPainResult)
                         .filter(MaxPainResult.id == result.id)
                         .first())
                
                if record:
                    record.volume_strike_price = volume_strike_price
                    record.open_interest_strike_price = open_interest_strike_price
                    session.commit()
                    
                    print(f"  ✅ 更新成功: volume_strike_price={volume_strike_price}, open_interest_strike_price={open_interest_strike_price}")
                    success_count += 1
                else:
                    print(f"  ⚠️  记录不存在")
                    failed_count += 1
                    
            except Exception as e:
                session.rollback()
                print(f"  ❌ 更新失败: {e}")
                failed_count += 1
                
    except Exception as e:
        session.rollback()
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        session.close()
    
    print()
    print("=" * 60)
    print("📊 更新统计:")
    print(f"  总记录数: {total_count}")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ⚠️  跳过: {skipped_count}")
    print(f"  ❌ 失败: {failed_count}")
    print("=" * 60)
    print("✅ 更新完成！")


if __name__ == "__main__":
    update_strike_prices()

