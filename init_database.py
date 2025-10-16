"""
Database Initialization Script

This script creates all database tables for the TradingOptions application.
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.stock_data import StockData
from models.options_data import OptionsData

def init_database():
    """Initialize database tables"""
    print("🚀 开始初始化数据库...")
    print("=" * 50)
    
    try:
        # 创建股票数据表
        print("📊 创建股票数据表...")
        StockData.create_tables()
        
        # 创建期权数据表
        print("📈 创建期权数据表...")
        OptionsData.create_tables()
        
        print("\n✅ 数据库初始化完成！")
        print("📋 已创建的表:")
        print("   - stock_data (股票数据表)")
        print("   - options_data (期权数据表)")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    init_database()
