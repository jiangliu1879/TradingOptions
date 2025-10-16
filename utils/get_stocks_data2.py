from datetime import datetime, date
from longport.openapi import QuoteContext, Config, Period, AdjustType
import pandas as pd
import os
import sys

# 添加项目根目录到路径，以便导入模型
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_stock_history_data(stock_code, file_path, start_date, end_date):
    config = Config.from_env()
    ctx = QuoteContext(config)

    # 获取历史K线数据
    resp = ctx.history_candlesticks_by_date(stock_code, Period.Min_180, AdjustType.NoAdjust, start_date, end_date)
    print(resp)

    # 将数据转换为DataFrame并保存到CSV文件
    if resp and len(resp) > 0:
        # 提取数据并转换为DataFrame
        data_list = []
        for candle in resp:
            data_list.append({
                'timestamp': candle.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume,
                'turnover': candle.turnover
            })
        
        df = pd.DataFrame(data_list)
        
        # 检查文件是否存在，决定是创建新文件还是追加数据
        if os.path.exists(file_path):
            # 文件存在，追加数据
            df.to_csv(file_path, mode='a', header=False, index=False)
            print(f"数据已追加到 {file_path}，共 {len(df)} 条记录")
        else:
            # 文件不存在，创建新文件
            df.to_csv(file_path, index=False)
            print(f"数据已保存到 {file_path}，共 {len(df)} 条记录")
        return True
    else:
        print("未获取到数据")
        return False

if __name__ == "__main__":
    # 演示新的数据库方法
    get_stock_history_data("SPY.US", "spy_data_180min.csv", date(2025, 9, 22), date(2025, 9, 22))