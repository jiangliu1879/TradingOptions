"""
从数据库计算最大痛点价格

这个脚本从options_data表中读取期权数据，按stock_code、expiry_date、update_time分组，
并计算每个分组的最大痛点价格。
"""

import os
import sys
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Any
import csv
from datetime import date

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.options_data import OptionsData
from models.max_pain_result import MaxPainResult


def get_options_data_from_db() -> pd.DataFrame:
    """
    从数据库获取所有期权数据
    
    Returns:
        DataFrame: 包含所有期权数据的DataFrame
    """
    print("📊 从数据库获取期权数据...")
    
    # 获取所有期权数据
    options_records = OptionsData.get_options_data()
    
    if not options_records:
        print("❌ 数据库中没有期权数据")
        return pd.DataFrame()
    
    # 转换为DataFrame
    data_list = []
    for record in options_records:
        data_list.append({
            'stock_code': record.stock_code,
            'expiry_date': record.expiry_date,
            'update_time': record.update_time,
            'symbol': record.symbol,
            'type': record.type,
            'strike_price': record.strike_price,
            'volume': record.volume,
            'open_interest': record.open_interest,
            'implied_volatility': record.implied_volatility,
            'contract_size': record.contract_size,
            'created_at': record.created_at
        })
    
    df = pd.DataFrame(data_list)
    print(f"✅ 成功获取 {len(df)} 条期权数据记录")
    
    return df


def process_options_data_from_db(df: pd.DataFrame) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
    """
    处理从数据库获取的期权数据，按stock_code、expiry_date、update_time分组
    
    Args:
        df: 从数据库获取的期权数据DataFrame
        
    Returns:
        字典结构: {
            stock_code: {
                expiry_date: {
                    update_time: {
                        "options": [
                            {strike_price: {"volume": {"put": int, "call": int}, "open_interest": {"put": int, "call": int}}},
                            ...
                        ]
                    }
                }
            }
        }
    """
    print("🔄 处理期权数据，按股票代码、到期日、更新时间分组...")
    
    # 按stock_code、expiry_date、update_time分组
    grouped_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {})))
    
    for _, row in df.iterrows():
        stock_code = row['stock_code']
        expiry_date = row['expiry_date']
        update_time = row['update_time']
        option_type = row['type']
        strike_price = float(row['strike_price'])
        volume = int(row['volume']) if pd.notna(row['volume']) else 0
        open_interest = int(row['open_interest']) if pd.notna(row['open_interest']) else 0
        
        # 如果该strike_price还没有记录，初始化
        if strike_price not in grouped_data[stock_code][expiry_date][update_time]:
            grouped_data[stock_code][expiry_date][update_time][strike_price] = {
                "volume": {"put": 0, "call": 0},
                "open_interest": {"put": 0, "call": 0}
            }
        
        # 更新对应类型的volume和open_interest
        grouped_data[stock_code][expiry_date][update_time][strike_price]["volume"][option_type] = volume
        grouped_data[stock_code][expiry_date][update_time][strike_price]["open_interest"][option_type] = open_interest
    
    # 转换为列表格式
    result = {}
    for stock_code, stock_data in grouped_data.items():
        result[stock_code] = {}
        for expiry_date, expiry_data in stock_data.items():
            result[stock_code][expiry_date] = {}
            for update_time, time_data in expiry_data.items():
                # 按strike_price排序
                sorted_strikes = sorted(time_data.keys())
                result[stock_code][expiry_date][update_time] = {
                    "options": [{strike: time_data[strike]} for strike in sorted_strikes]
                }
    
    print(f"✅ 数据分组完成，共 {len(result)} 个股票代码")
    return result


def calculate_volume_std_deviation(data_list: List[Dict], current_index: int) -> float:
    """
    计算当前行权价及其左右3档行权价的volume标准差
    
    Args:
        data_list: 期权数据列表
        current_index: 当前行权价的索引
        
    Returns:
        float: volume标准差
    """
    import statistics
    
    # 获取当前行权价及其左右3档的索引范围
    start_index = max(0, current_index - 3)
    end_index = min(len(data_list), current_index + 4)  # +4 因为要包含当前行权价
    
    volumes = []
    
    # 收集指定范围内的volume数据
    for i in range(start_index, end_index):
        strike_price = list(data_list[i].keys())[0]
        put_volume = data_list[i][strike_price]['volume']['put']
        call_volume = data_list[i][strike_price]['volume']['call']
        total_volume = put_volume + call_volume
        volumes.append(total_volume)
    
    # 计算标准差
    if len(volumes) > 1:
        return statistics.stdev(volumes)
    else:
        return 0.0


def calculate_max_pain_from_db(result: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]], output_file: str):
    """
    计算最大痛点价格并保存结果
    
    Args:
        result: 处理后的期权数据
        output_file: 输出CSV文件路径
    """
    print("🧮 开始计算最大痛点价格...")
    
    # 准备CSV数据
    csv_data = []
    
    print("\n期权数据按股票代码、到期日、更新时间分组:")
    for stock_code, stock_data in result.items():
        print(f"\n股票代码: {stock_code}")
        for expiry_date, expiry_data in stock_data.items():
            print(f"  到期日: {expiry_date}")
            for update_time, time_data in expiry_data.items():
                print(f"    更新时间: {update_time}")
                print(f"    期权数量: {len(time_data['options'])}")
                
                data_list = time_data['options']
                
                if not data_list:
                    print("      ⚠️  没有期权数据，跳过")
                    continue
                
                min_earn_volume = float('inf')
                min_earn_open_interest = float('inf')
                max_pain_price_volume = 0
                max_pain_price_open_interest = 0
                volume_std_deviation = 0
                max_pain_index = 0
                
                # 遍历每个行权价，计算在该价格到期时的期权卖方收益
                sum_volume = 0
                sum_open_interest = 0
                for i in range(len(data_list)):
                    put_earn_volume = 0
                    put_earn_open_interest = 0
                    call_earn_volume = 0
                    call_earn_open_interest = 0
                    
                    # 计算高于当前行权价的put期权收益
                    # 如果股价在put行权价以下，put期权买方盈利
                    for data_item in data_list[i + 1:]:
                        strike_price = list(data_item.keys())[0]
                        put_earn_volume += data_item[strike_price]['volume']['put']
                        put_earn_open_interest += data_item[strike_price]['open_interest']['put']
                        sum_volume += data_item[strike_price]['volume']['put']
                        sum_open_interest += data_item[strike_price]['open_interest']['put']
                    # 计算低于当前行权价的call期权收益
                    # 如果股价在call行权价以上，call期权买方盈利
                    for data_item in data_list[:i]:
                        strike_price = list(data_item.keys())[0]
                        call_earn_volume += data_item[strike_price]['volume']['call']
                        call_earn_open_interest += data_item[strike_price]['open_interest']['call']
                        sum_volume += data_item[strike_price]['volume']['call']
                        sum_open_interest += data_item[strike_price]['open_interest']['call']

                    current_strike_price = list(data_list[i].keys())[0]
                    total_earn_volume = put_earn_volume + call_earn_volume
                    total_earn_open_interest = put_earn_open_interest + call_earn_open_interest
                    
                    # 更新基于volume的最大痛点
                    if total_earn_volume < min_earn_volume:
                        min_earn_volume = total_earn_volume
                        max_pain_price_volume = current_strike_price
                        max_pain_index = i
                    
                    # 更新基于open_interest的最大痛点
                    if total_earn_open_interest < min_earn_open_interest:
                        min_earn_open_interest = total_earn_open_interest
                        max_pain_price_open_interest = current_strike_price

                # 计算最大痛点价格及其左右3档行权价的volume标准差
                volume_std_deviation = calculate_volume_std_deviation(data_list, max_pain_index)

                print(f"      基于Volume - 最小收益: {min_earn_volume:,.0f}, 最大痛点价格: ${max_pain_price_volume:.0f}")
                print(f"      基于Open Interest - 最小收益: {min_earn_open_interest:,.0f}, 最大痛点价格: ${max_pain_price_open_interest:.0f}")
                print(f"      Volume标准差: {volume_std_deviation:.2f}")
                print("      ----------------------------------------")
                
                # 添加到CSV数据
                csv_data.append({
                    'stock_code': stock_code,
                    'expiry_date': expiry_date,
                    'update_time': update_time,
                    'max_pain_price_volume': max_pain_price_volume,
                    'max_pain_price_open_interest': max_pain_price_open_interest,
                    'sum_volume': sum_volume,
                    'volume_std_deviation': volume_std_deviation,
                    'sum_open_interest': sum_open_interest
                })
    
    # 写入CSV文件
    if csv_data:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'stock_code', 
                'expiry_date', 
                'update_time',
                'max_pain_price_volume', 
                'max_pain_price_open_interest',
                'sum_volume',
                'volume_std_deviation',
                'sum_open_interest'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"\n✅ 最大痛点结果已保存到: {output_file}")
        print(f"📊 共处理 {len(csv_data)} 个数据分组")
        
        # 保存到数据库
        print("\n💾 保存最大痛点结果到数据库...")
        try:
            # 确保数据库表存在
            MaxPainResult.create_tables()
            
            # 保存数据到数据库
            saved_count = MaxPainResult.save_max_pain_results(csv_data)
            print(f"✅ 成功保存 {saved_count} 条记录到数据库")
            
        except Exception as e:
            print(f"❌ 保存到数据库时出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 显示统计信息
        if csv_data:
            print(f"\n📈 统计信息:")
            print(f"   - 涉及股票代码: {len(set([item['stock_code'] for item in csv_data]))}")
            print(f"   - 涉及到期日期: {len(set([item['expiry_date'] for item in csv_data]))}")
            print(f"   - 涉及更新时间: {len(set([item['update_time'] for item in csv_data]))}")
            
            # 显示最大痛点价格范围
            volume_prices = [item['max_pain_price_volume'] for item in csv_data]
            oi_prices = [item['max_pain_price_open_interest'] for item in csv_data]
            
            print(f"   - Volume最大痛点价格范围: ${min(volume_prices):.0f} - ${max(volume_prices):.0f}")
            print(f"   - Open Interest最大痛点价格范围: ${min(oi_prices):.0f} - ${max(oi_prices):.0f}")
    else:
        print("❌ 没有数据可以保存")


def main():
    """主函数"""
    print("🚀 开始从数据库计算最大痛点价格")
    print("=" * 60)
    
    try:
        # 1. 从数据库获取期权数据
        df = get_options_data_from_db()
        
        if df.empty:
            print("❌ 数据库中没有期权数据，请先运行数据获取脚本")
            return
        
        # 2. 处理数据分组
        result = process_options_data_from_db(df)
        
        # 3. 计算最大痛点价格
        output_file = '/Users/zego/Codes/TradingOptions/data/result/max_pain_results_from_db.csv'
        calculate_max_pain_from_db(result, output_file)
        
        print("\n🎉 最大痛点价格计算完成！")
        
    except Exception as e:
        print(f"❌ 计算过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
