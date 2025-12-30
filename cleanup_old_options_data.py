"""
清理 options_data 表中的旧数据

对于相同的 expiry_date，仅保留 update_time 为最新的数据，删除其他旧数据。
"""

import os
import sys
from datetime import date
from sqlalchemy import func, text
from collections import defaultdict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.options_data import OptionsData

def cleanup_old_options_data_optimized():
    """优化版本：使用 SQL 批量删除"""
    print("=" * 60)
    print("🔄 开始清理 options_data 表中的旧数据（优化版本）")
    print("=" * 60)
    print("规则：对于相同的 expiry_date，仅保留 update_time 为最新的数据")
    print()
    
    session = OptionsData.get_session()
    engine = OptionsData.get_engine()
    
    try:
        # 1. 获取所有不同的 expiry_date 和对应的最新 update_time
        print("📊 步骤 1: 查找每个 expiry_date 的最新 update_time...")
        
        # 使用 SQL 查询找到每个 expiry_date 的最新 update_time
        # 注意：update_time 是字符串格式 'YYYY-MM-DD HH:MM:SS'，可以直接用 MAX 比较
        query = text("""
            SELECT expiry_date, MAX(update_time) as latest_time, COUNT(*) as total_count
            FROM options_data
            GROUP BY expiry_date
            ORDER BY expiry_date
        """)
        
        result = session.execute(query)
        expiry_info = {}
        total_records_before = 0
        
        for row in result:
            expiry_date_value = row[0]
            latest_time = row[1]
            total_count = row[2]
            
            # expiry_date 可能是 date 对象或字符串
            if isinstance(expiry_date_value, str):
                try:
                    expiry_date = date.fromisoformat(expiry_date_value)
                except:
                    # 如果解析失败，尝试其他格式
                    expiry_date = expiry_date_value
            elif isinstance(expiry_date_value, date):
                expiry_date = expiry_date_value
            else:
                expiry_date = expiry_date_value
            
            expiry_info[expiry_date] = {
                'latest_time': latest_time,
                'total_count': total_count
            }
            total_records_before += total_count
            
            print(f"  {expiry_date}: 共 {total_count} 条记录, 最新时间: {latest_time}")
        
        print()
        print(f"📊 找到 {len(expiry_info)} 个不同的到期日期，总记录数: {total_records_before}")
        print()
        
        # 2. 删除旧数据
        print("📊 步骤 2: 删除旧数据...")
        total_deleted = 0
        
        for expiry_date, info in expiry_info.items():
            latest_time = info['latest_time']
            total_count = info['total_count']
            
            # 使用 SQL 删除该 expiry_date 中 update_time 不是最新的记录
            # 注意：SQLite 中日期比较需要确保格式一致
            delete_query = text("""
                DELETE FROM options_data
                WHERE expiry_date = :expiry_date
                AND update_time != :latest_time
            """)
            
            # 确保 expiry_date 格式正确（SQLite 可能存储为字符串或日期）
            if isinstance(expiry_date, date):
                expiry_date_str = expiry_date.isoformat()
            else:
                expiry_date_str = str(expiry_date)
            
            result = session.execute(
                delete_query,
                {'expiry_date': expiry_date_str, 'latest_time': latest_time}
            )
            
            deleted_count = result.rowcount
            session.commit()
            
            if deleted_count > 0:
                total_deleted += deleted_count
                print(f"  ✅ {expiry_date}: 删除了 {deleted_count} 条旧记录，保留 {total_count - deleted_count} 条")
            else:
                print(f"  ℹ️  {expiry_date}: 无需删除（已是最新）")
        
        print()
        print("=" * 60)
        print("📊 清理统计:")
        print(f"  处理的到期日期数: {len(expiry_info)}")
        print(f"  删除前总记录数: {total_records_before}")
        print(f"  删除的记录数: {total_deleted}")
        print(f"  保留的记录数: {total_records_before - total_deleted}")
        print("=" * 60)
        print("✅ 清理完成！")
        
    except Exception as e:
        session.rollback()
        print(f"❌ 清理过程中出错: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    # 使用优化版本
    cleanup_old_options_data_optimized()

