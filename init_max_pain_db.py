"""
Initialize Max Pain Results Database Table

This script creates the max_pain_results table in the database.
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.max_pain_result import MaxPainResult

def main():
    """主函数"""
    print("🚀 初始化最大痛点结果数据库表")
    print("=" * 50)
    
    try:
        # 创建数据库表
        MaxPainResult.create_tables()
        
        print("\n✅ 数据库表初始化完成！")
        
    except Exception as e:
        print(f"❌ 初始化过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
