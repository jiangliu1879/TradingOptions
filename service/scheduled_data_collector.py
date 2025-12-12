"""
定时期权数据收集器

这个脚本可以按设定的时间间隔自动收集期权数据，支持多种调度模式。
"""

import os
import sys
import time
import schedule
import threading
from datetime import datetime, date
import signal
import logging
from typing import Optional

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.get_realtime_options_data import process_options_data, get_eastern_time, get_stock_realtime_price
from models.options_data import OptionsData
from models.max_pain_result import MaxPainResult
from utils.max_pain_calculator import MaxPainCalculator
import pandas as pd
from collections import defaultdict
import statistics


class ScheduledDataCollector:
    """定时数据收集器类"""
    
    def __init__(self, stock_code: str = "SPY.US", expiry_date: Optional[date] = None):
        """
        初始化数据收集器
        
        Args:
            stock_code: 股票代码
            expiry_date: 到期日期，如果为None则使用默认日期
        """
        self.stock_code = stock_code
        self.expiry_date = expiry_date or date(2025, 10, 13)
        self.is_running = False
        self.collection_count = 0
        self.error_count = 0
        
        # 设置日志
        self.setup_logging()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """设置日志配置"""
        # 创建logs目录
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 配置日志
        log_file = os.path.join(log_dir, f'data_collector_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """信号处理器，用于优雅退出"""
        self.logger.info(f"接收到信号 {signum}，正在停止数据收集...")
        self.stop()
    
    def collect_data(self):
        """收集期权数据并计算最大痛点"""
        try:
            self.logger.info(f"开始收集 {self.stock_code} 期权数据...")
            
            # 获取美东当前时间
            eastern_time = get_eastern_time()
            update_time = eastern_time.strftime('%Y-%m-%d %H:%M:%S')
            
            self.logger.info(f"数据收集时间: {update_time}")

            stock_price = get_stock_realtime_price(self.stock_code)
            
            # 处理期权数据
            result = process_options_data(self.stock_code, self.expiry_date, update_time)
            
            if result:
                self.collection_count += 1
                self.logger.info(f"✅ 成功收集 {len(result)} 条期权数据 (第 {self.collection_count} 次)")
                
                # 记录数据库统计信息
                self.log_database_stats()
                
                # 计算最大痛点并保存到数据库
                self.logger.info(f"🧮 开始计算最大痛点...")
                max_pain_result = self.calculate_max_pain_for_current_data(
                    self.stock_code, self.expiry_date, update_time
                )
                
                if max_pain_result:
                    max_pain_result['stock_price'] = stock_price
                    self.save_max_pain_result(max_pain_result)
                    self.logger.info(f"✅ 最大痛点计算和保存完成")
                else:
                    self.logger.warning(f"⚠️ 最大痛点计算失败")
                
            else:
                self.error_count += 1
                self.logger.warning(f"⚠️ 数据收集返回空结果 (错误次数: {self.error_count})")
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"❌ 数据收集失败: {e} (错误次数: {self.error_count})")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def log_database_stats(self):
        """记录数据库统计信息"""
        try:
            # 获取最新数据统计
            latest_options = OptionsData.get_latest_options_data(self.stock_code, self.expiry_date)
            
            if latest_options:
                call_count = len([opt for opt in latest_options if opt.type == 'call'])
                put_count = len([opt for opt in latest_options if opt.type == 'put'])
                total_oi = sum([opt.open_interest for opt in latest_options if opt.open_interest])
                
                self.logger.info(f"📊 数据库统计 - 看涨: {call_count}, 看跌: {put_count}, 总持仓: {total_oi:,}")
            
            # 获取总记录数
            all_options = OptionsData.get_options_data(stock_code=self.stock_code)
            self.logger.info(f"📈 数据库中 {self.stock_code} 总记录数: {len(all_options)}")
            
        except Exception as e:
            self.logger.error(f"❌ 获取数据库统计信息失败: {e}")
    
    def process_options_data_for_max_pain(self, stock_code: str, expiry_date: date, update_time: str):
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
                self.logger.warning(f"⚠️ 未找到 {stock_code} 在 {expiry_date} {update_time} 的期权数据")
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
            self.logger.error(f"❌ 处理期权数据失败: {e}")
            return []
    
    def calculate_max_pain_for_current_data(self, stock_code: str, expiry_date: date, update_time: str):
        """
        计算当前数据的最大痛点
        
        Args:
            stock_code: 股票代码
            expiry_date: 到期日期
            update_time: 更新时间
            
        Returns:
            dict: 最大痛点计算结果
        """
        try:
            self.logger.info(f"🧮 开始计算 {stock_code} 的最大痛点...")
            
            # 获取期权数据
            data_list = self.process_options_data_for_max_pain(stock_code, expiry_date, update_time)
            
            if not data_list:
                self.logger.warning(f"⚠️ 没有期权数据可用于计算最大痛点")
                return None
            
            # 使用新的MaxPainCalculator工具类
            result = MaxPainCalculator.calculate_max_pain_with_metadata(
                stock_code=stock_code,
                expiry_date=expiry_date,
                update_time=update_time,
                data_list=data_list,
                include_volume_std=True
            )
            
            if result:
                self.logger.info(f"✅ 最大痛点计算完成 - Volume: ${result['max_pain_price_volume']:.0f}, Open Interest: ${result['max_pain_price_open_interest']:.0f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 计算最大痛点失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def save_max_pain_result(self, result: dict):
        """
        保存最大痛点结果到数据库
        
        Args:
            result: 最大痛点计算结果
        """
        try:
            # 确保数据库表存在
            MaxPainResult.create_tables()
            
            # 保存数据到数据库
            saved_count = MaxPainResult.save_max_pain_results([result])
            
            if saved_count > 0:
                self.logger.info(f"✅ 最大痛点结果已保存到数据库")
            else:
                self.logger.warning(f"⚠️ 最大痛点结果可能已存在，跳过保存")
                
        except Exception as e:
            self.logger.error(f"❌ 保存最大痛点结果失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def start_market_hours(self, interval_minutes: int = 15):
        """在交易时间内按间隔收集数据"""
        self.logger.info(f"🕐 启动定时收集器 - 交易时间内每 {interval_minutes} 分钟收集一次")
        self.logger.info(f"📊 目标股票: {self.stock_code}")
        self.logger.info(f"📅 到期日期: {self.expiry_date}")
        
        # 交易时间: 美东时间 9:30 - 16:00
        schedule.every(interval_minutes).minutes.do(self.collect_data_if_market_open)
        self.run_scheduler()
    
    def is_market_open(self) -> bool:
        """检查是否在交易时间内"""
        try:
            eastern_time = get_eastern_time()
            current_time = eastern_time.time()
            
            # 交易时间: 9:30 AM - 4:00 PM (美东时间)
            market_open = eastern_time.replace(hour=9, minute=30, second=0).time()
            # 交易结束时间: 16:15 (美东时间), 多出 15 分钟是为了获取收盘时的数据
            market_close = eastern_time.replace(hour=16, minute=15, second=0).time()
            
            # 检查是否为工作日 (周一到周五)
            weekday = eastern_time.weekday()  # 0=Monday, 6=Sunday
            
            return (weekday < 5 and market_open <= current_time <= market_close)
            
        except Exception as e:
            self.logger.error(f"❌ 检查交易时间失败: {e}")
            return False
    
    def collect_data_if_market_open(self):
        """仅在交易时间内收集数据"""
        if self.is_market_open():
            self.collect_data()
        else:
            eastern_time = get_eastern_time()
            self.logger.info(f"⏰ 当前时间 {eastern_time.strftime('%H:%M:%S')} 不在交易时间内，跳过数据收集")
    
    def run_scheduler(self):
        """运行调度器"""
        self.is_running = True
        
        # 立即执行一次
        self.logger.info("🚀 立即执行第一次数据收集...")
        self.collect_data()
        
        self.logger.info("⏰ 调度器已启动，按 Ctrl+C 停止...")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("👋 接收到键盘中断信号")
        finally:
            self.stop()
    
    def stop(self):
        """停止数据收集器"""
        self.is_running = False
        schedule.clear()
        
        self.logger.info("🛑 数据收集器已停止")
        self.logger.info(f"📊 总计收集次数: {self.collection_count}")
        self.logger.info(f"❌ 总错误次数: {self.error_count}")
        
        if self.collection_count > 0:
            success_rate = (self.collection_count / (self.collection_count + self.error_count)) * 100
            self.logger.info(f"✅ 成功率: {success_rate:.1f}%")


def main(stock_code: str = "SPY.US"):
    """主函数"""
    print("🚀 期权数据定时收集器")
    print("=" * 60)
    
    # 获取当前美东日期
    eastern_time = get_eastern_time()
    expiry_date = eastern_time.date()
    
    # 创建收集器实例
    collector = ScheduledDataCollector(stock_code, expiry_date)
    
    try:
        collector.start_market_hours(10)
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        collector.stop()

if __name__ == "__main__":
    main()
