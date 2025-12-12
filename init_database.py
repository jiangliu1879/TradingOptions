"""
数据库初始化脚本

根据models目录下的3个model创建sqlite数据库和数据表
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
import os

# 导入所有模型以确保它们被注册到Base.metadata
from models.stock_data import StockData, Base as StockBase
from models.options_data import OptionsData, Base as OptionsBase
from models.max_pain_result import MaxPainResult, Base as MaxPainBase

def get_database_url():
    """获取数据库URL"""
    db_path = os.getenv('DATABASE_URL', 'sqlite:///us_market_data.db')
    return db_path

def create_all_tables():
    """创建所有数据库表"""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)
    
    print("=" * 60)
    print("🚀 开始创建数据库表...")
    print("=" * 60)
    print(f"📁 数据库路径: {database_url}")
    print()
    
    # 由于每个model都有自己的Base，我们需要分别创建表
    # 但实际上它们都使用相同的数据库，所以我们需要确保使用同一个Base
    
    # 方法1: 使用每个model的create_tables方法
    print("📊 创建 stock_data 表...")
    StockData.create_tables()
    
    print("📊 创建 options_data 表...")
    OptionsData.create_tables()
    
    print("📊 创建 max_pain_results 表...")
    MaxPainResult.create_tables()
    
    print()
    print("=" * 60)
    print("✅ 所有数据库表创建完成！")
    print("=" * 60)
    
    # 验证表是否创建成功
    print("\n📋 验证已创建的表:")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        tables = [row[0] for row in result]
        for table in tables:
            print(f"   ✓ {table}")
    
    print("\n✅ 数据库初始化完成！")

if __name__ == "__main__":
    create_all_tables()

