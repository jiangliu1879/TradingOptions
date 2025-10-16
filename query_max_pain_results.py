"""
Query Max Pain Results from Database

This script demonstrates how to query max pain results from the database.
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.max_pain_result import MaxPainResult

def main():
    """主函数"""
    print("🚀 查询最大痛点结果数据库")
    print("=" * 50)
    
    try:
        # 1. 获取所有股票代码
        print("📊 获取所有股票代码:")
        stock_codes = MaxPainResult.get_stock_codes()
        print(f"   {stock_codes}")
        print()
        
        # 2. 获取所有到期日期
        print("📅 获取所有到期日期:")
        expiry_dates = MaxPainResult.get_expiry_dates()
        print(f"   {expiry_dates}")
        print()
        
        # 3. 查询最新的最大痛点结果
        if stock_codes:
            latest_results = MaxPainResult.get_latest_max_pain_results(stock_codes[0])
            print(f"📈 {stock_codes[0]} 的最新最大痛点结果:")
            for result in latest_results:
                print(f"   - 到期日: {result.expiry_date}")
                print(f"   - 更新时间: {result.update_time}")
                print(f"   - Volume最大痛点: ${result.max_pain_price_volume:.0f}")
                print(f"   - Open Interest最大痛点: ${result.max_pain_price_open_interest:.0f}")
                print(f"   - Volume方差: {result.volume_variance:.2f}")
                print(f"   - 总Volume: {result.sum_volume:,}")
                print(f"   - 总Open Interest: {result.sum_open_interest:,}")
                print()
        
        # 4. 查询所有结果（限制10条）
        print("📊 最近10条最大痛点结果:")
        all_results = MaxPainResult.get_max_pain_results(limit=10)
        for i, result in enumerate(all_results, 1):
            print(f"   {i}. {result.stock_code} - {result.expiry_date} - {result.update_time}")
            print(f"      Volume最大痛点: ${result.max_pain_price_volume:.0f}, Open Interest最大痛点: ${result.max_pain_price_open_interest:.0f}")
            print(f"      Volume方差: {result.volume_variance:.2f}")
        
        print(f"\n✅ 查询完成！共找到 {len(all_results)} 条记录")
        
    except Exception as e:
        print(f"❌ 查询过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
