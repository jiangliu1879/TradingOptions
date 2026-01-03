"""
调整 NVDA.US 的股价数据（1:10 拆股调整）

将 2024-06-10 到 2024-12-31 期间的 close 数据除以 10
"""

import os
import sys
from datetime import date

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.stock_data import StockData

def adjust_stock_split(stock_code, start_date, end_date, split_ratio):
    """调整 NVDA.US 的拆股数据"""
    # 先检查是否存在 NAVDA.US（可能是拼写错误），否则使用 NVDA.US
    session = StockData.get_session()
    try:
        # 查询指定日期范围内的数据
        records = session.query(StockData).filter(
            StockData.stock_code == stock_code,
            StockData.timestamp >= start_date,
            StockData.timestamp <= end_date
        ).all()
        
        count = len(records)
        
        if count == 0:
            print(f"未找到 {stock_code} 在 {start_date} 到 {end_date} 期间的数据")
            return 0
        
        print(f"找到 {count} 条 {stock_code} 的记录，准备调整...")
        
        # 更新每条记录的 close 价格（除以10）
        updated_count = 0
        for record in records:
            old_close = record.close
            new_close = old_close * split_ratio
            
            # 同时调整 open, high, low 价格（保持一致性）
            record.open = record.open * split_ratio
            record.high = record.high * split_ratio
            record.low = record.low * split_ratio
            record.close = new_close
            
            updated_count += 1
            print(f"  {record.timestamp}: ${old_close:.2f} -> ${new_close:.2f}")
        
        session.commit()
        print(f"\n✅ 成功调整 {stock_code} 的 {updated_count} 条记录")
        print(f"   调整范围: {start_date} 到 {end_date}")
        print(f"   调整比例: 1:10 (价格除以10)")
        return updated_count
        
    except Exception as e:
        session.rollback()
        print(f"❌ 调整 {stock_code} 数据时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0
    finally:
        session.close()

if __name__ == "__main__":
    print("🔄 开始调整 NVDA.US/NAVDA.US 的拆股数据...")
    print("=" * 60)
    stock_code = "AAPL.US"
    start_date = "2000-12-29"
    end_date = "2000-12-31"
    split_ratio = 2
    updated_count = adjust_stock_split(stock_code, start_date, end_date, split_ratio)
    print(f"调整操作完成，共更新 {updated_count} 条记录")
