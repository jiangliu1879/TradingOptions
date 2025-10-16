import pandas as pd
from collections import defaultdict
from typing import Dict, List, Any
import csv


def process_options_data(csv_file_path: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    读取期权数据CSV文件，按股票代码和到期日分组，每个分组包含股票收盘价和期权数据列表
    
    Args:
        csv_file_path: CSV文件路径
        
    Returns:
        字典结构: {
            stock_code: {
                expiry_date: {
                    "stock_close_price": float,
                    "options": [
                        {strike_price: {"volume": {"put": int, "call": int}, "open_interest": {"put": int, "call": int}}},
                        ...
                    ]
                }
            }
        }
    """
    # 读取CSV数据
    df = pd.read_csv(csv_file_path)
    
    # 按stock_code和expiry_date分组，每个分组存储为字典，key为strike_price，value为{"put": volume, "call": volume}
    grouped_data = defaultdict(lambda: defaultdict(lambda: {}))
    
    for _, row in df.iterrows():
        stock_code = row['stock_code']
        expiry_date = row['expiry_date']
        option_type = row['type']
        strike_price = float(row['strike_price'])
        volume = int(row['volume'])
        open_interest = int(row['open_interest'])
        stock_close_price = float(row['stock_close_price'])
        
        # 初始化stock_code和expiry_date组（只设置一次stock_close_price）
        if "stock_close_price" not in grouped_data[stock_code][expiry_date]:
            grouped_data[stock_code][expiry_date] = {"stock_close_price": stock_close_price}
        
        # 如果该strike_price还没有记录，初始化
        if strike_price not in grouped_data[stock_code][expiry_date]:
            grouped_data[stock_code][expiry_date][strike_price] = {
                "volume": {"put": 0, "call": 0},
                "open_interest": {"put": 0, "call": 0}
            }
        
        # 更新对应类型的volume和open_interest
        grouped_data[stock_code][expiry_date][strike_price]["volume"][option_type] = volume
        grouped_data[stock_code][expiry_date][strike_price]["open_interest"][option_type] = open_interest
    
    # 转换为列表格式，保留stock_close_price
    result = {}
    for stock_code, stock_data in grouped_data.items():
        result[stock_code] = {}
        for expiry_date, strike_data in stock_data.items():
            # 按strike_price排序，排除stock_close_price
            sorted_strikes = sorted([k for k in strike_data.keys() if k != "stock_close_price"])
            result[stock_code][expiry_date] = {
                "stock_close_price": strike_data["stock_close_price"],
                "options": [{strike: strike_data[strike]} for strike in sorted_strikes]
            }
    
    return result


def calculate_max_pain(result, output_file):
    # 准备CSV数据
    csv_data = []
    
    print("期权数据按股票代码和到期日分组:")
    for stock_code, stock_data in result.items():
        print(f"\n股票代码: {stock_code}")
        for expiry_date, data in stock_data.items():
            print(f"  到期日: {expiry_date}")
            print(f"  股票收盘价: {data['stock_close_price']}")
            print(f"  期权数量: {len(data['options'])}")
            
            data_list = data['options']
            stock_close_price = data['stock_close_price']
        
            min_earn_volume = float('inf')
            min_earn_open_interest = float('inf')
            max_pain_price_volume = 0
            max_pain_price_open_interest = 0
            
            for i in range(len(data_list)):
                put_earn_volume = 0
                put_earn_open_interest = 0
                call_earn_volume = 0
                call_earn_open_interest = 0
                
                # 计算高于当前行权价的put期权收益
                for data_item in data_list[i + 1:]:
                    strike_price = list(data_item.keys())[0]
                    put_earn_volume += data_item[strike_price]['volume']['put']
                    put_earn_open_interest += data_item[strike_price]['open_interest']['put']
                
                # 计算低于当前行权价的call期权收益
                for data_item in data_list[:i]:
                    strike_price = list(data_item.keys())[0]
                    call_earn_volume += data_item[strike_price]['volume']['call']
                    call_earn_open_interest += data_item[strike_price]['open_interest']['call']
                
                current_strike_price = list(data_list[i].keys())[0]
                total_earn_volume = put_earn_volume + call_earn_volume
                total_earn_open_interest = put_earn_open_interest + call_earn_open_interest
                
                # 更新基于volume的最大痛点
                if total_earn_volume < min_earn_volume:
                    min_earn_volume = total_earn_volume
                    max_pain_price_volume = current_strike_price
                
                # 更新基于open_interest的最大痛点
                if total_earn_open_interest < min_earn_open_interest:
                    min_earn_open_interest = total_earn_open_interest
                    max_pain_price_open_interest = current_strike_price

            print(f"    基于Volume - 最小收益: {min_earn_volume}, 最大痛点价格: {max_pain_price_volume}")
            print(f"    基于Open Interest - 最小收益: {min_earn_open_interest}, 最大痛点价格: {max_pain_price_open_interest}")
            print(f"    股票收盘价: {stock_close_price}")
            print("    ----------------------------------------")
            
            # 添加到CSV数据
            csv_data.append({
                'stock_code': stock_code,
                'expiry_date': expiry_date,
                'stock_close_price': stock_close_price, 
                'max_pain_price_volume': max_pain_price_volume,
                'max_pain_price_open_interest': max_pain_price_open_interest
            })
    
    # 写入CSV文件
    if csv_data:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['stock_code', 'expiry_date', 'stock_close_price', 'max_pain_price_volume', 'max_pain_price_open_interest']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"\n最大痛点结果已保存到: {output_file}")
        print(f"共处理 {len(csv_data)} 个到期日的数据")


if __name__ == "__main__":
    csv_path = '/Users/zego/Codes/TradingOptions/data/options/spy_options_data.csv'
    result = process_options_data(csv_path)

    output_file = '/Users/zego/Codes/TradingOptions/data/result/spy_max_pain_results.csv'
    calculate_max_pain(result, output_file)

    # csv_path = '/Users/zego/Codes/TradingOptions/data/options/stock_options_data.csv'
    # result = process_options_data(csv_path)

    # output_file = '/Users/zego/Codes/TradingOptions/data/result/stock_max_pain_results.csv'
    # calculate_max_pain(result, output_file)
    
    

