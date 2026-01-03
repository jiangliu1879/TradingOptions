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
from models.max_pain_result2 import MaxPainResult2      
from utils.max_pain_calculator import MaxPainCalculator
import pandas as pd
from collections import defaultdict
import statistics


class OptionsDataCollector:
    """期权数据收集器类"""
    
    def __init__(self, stock_code: str = "NVDA.US", expiry_date: Optional[date] = None):
        """
        初始化数据收集器
        
        Args:
            stock_code: 股票代码
            expiry_date: 到期日期，如果为None则使用默认日期
        """
        self.stock_code = stock_code
        self.expiry_date = expiry_date
          # 设置日志
        self.setup_logging()

    def setup_logging(self):
        """设置日志配置"""
        # 创建logs目录
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 配置日志
        log_file = os.path.join(log_dir, f'options_data_collector_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def collect_data(self):
        """收集期权数据并计算最大痛点"""

        max_pain_result = None
        try:
            self.logger.info(f"开始收集 {self.stock_code} 期权数据...")
            
            # 获取美东当前时间
            eastern_time = get_eastern_time()
            update_time = eastern_time.strftime('%Y-%m-%d %H:%M:%S')
            
            self.logger.info(f"数据收集时间: {update_time}")

            stock_price = get_stock_realtime_price(self.stock_code)
            
            # 处理期权数据
            result = process_options_data(self.stock_code, self.expiry_date, update_time, stock_price, save_to_database=False)
            
            if result:
                self.logger.info(f"✅ 成功收集 {len(result)} 条期权数据")
                
                # 计算最大痛点并保存到数据库
                self.logger.info(f"🧮 开始计算最大痛点...")
                max_pain_result = self.calculate_max_pain_for_current_data(
                    self.stock_code, self.expiry_date, update_time, result
                )
                
                if max_pain_result:
                    max_pain_result['stock_price'] = stock_price
                    self.save_max_pain_result(max_pain_result)
                    self.logger.info(f"✅ 最大痛点计算和保存完成")
                else:
                    self.logger.warning(f"⚠️ 最大痛点计算失败")
            else:
                self.logger.warning(f"⚠️ 数据收集返回空结果")
        except Exception as e:
            self.logger.error(f"❌ 数据收集失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            return max_pain_result
    
    def process_options_data_for_max_pain(self, stock_code: str, expiry_date: date, update_time: str, all_options_data: list):
        """
        处理期权数据用于计算最大痛点
        
        Args:
            stock_code: 股票代码
            expiry_date: 到期日期
            update_time: 更新时间
            all_options_data: 所有期权数据
            
        Returns:
            list: 处理后的期权数据列表
        """
        try:
            # 通过三个条件精确查询期权数据
            options_records = all_options_data
            
            if not options_records:
                self.logger.warning(f"⚠️ 没有期权数据可用于计算最大痛点")
                return []
            
            # 按行权价分组数据
            grouped_data = {}
            for record in options_records:
                strike_price = float(record["strike_price"])
                
                if strike_price not in grouped_data:
                    grouped_data[strike_price] = {
                        "volume": {"put": 0, "call": 0},
                        "open_interest": {"put": 0, "call": 0}
                    }
                
                # 更新对应类型的volume和open_interest
                if record["volume"]:
                    grouped_data[strike_price]["volume"][record["type"]] = int(record["volume"])
                if record["open_interest"]:
                    grouped_data[strike_price]["open_interest"][record["type"]] = int(record["open_interest"])
            
            # 转换为列表格式并按行权价排序
            sorted_strikes = sorted(grouped_data.keys())
            data_list = [{strike: grouped_data[strike]} for strike in sorted_strikes]
            
            return data_list
            
        except Exception as e:
            self.logger.error(f"❌ 处理期权数据用于计算最大痛点失败: {e}")
            return []
    
    def calculate_max_pain_for_current_data(self, stock_code: str, expiry_date: date, update_time: str, all_options_data: list):
        """
        计算当前数据的最大痛点
        
        Args:
            stock_code: 股票代码
            expiry_date: 到期日期
            update_time: 更新时间
            all_options_data: 所有期权数据
            
        Returns:
            dict: 最大痛点计算结果
        """
        try:
            self.logger.info(f"🧮 开始计算 {stock_code} 的最大痛点...")
            
            # 获取期权数据
            data_list = self.process_options_data_for_max_pain(stock_code, expiry_date, update_time, all_options_data)
            
            if not data_list:
                self.logger.warning(f"⚠️ 没有期权数据可用于计算最大痛点")
                return None
            
            # 使用新的MaxPainCalculator工具类
            result = MaxPainCalculator.calculate_max_pain_with_metadata(
                stock_code=stock_code,
                expiry_date=expiry_date,
                update_time=update_time,
                data_list=data_list
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
            MaxPainResult2.create_tables()
            
            # 保存数据到数据库
            saved_count = MaxPainResult2.save_max_pain_results2([result])
            
            if saved_count > 0:
                self.logger.info(f"✅ 最大痛点结果已保存到数据库")
            else:
                self.logger.warning(f"⚠️ 最大痛点结果可能已存在，跳过保存")
                
        except Exception as e:
            self.logger.error(f"❌ 保存最大痛点结果失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

def trade_options():
    put_symbol = "NVDA260102P190000.US"

    from decimal import Decimal
    from longport.openapi import TradeContext, Config, OrderType, OrderSide, TimeInForceType

    # Load configuration from environment variables
    config = Config.from_env()

    # Create a context for trade APIs
    ctx = TradeContext(config)

    resp = ctx.submit_order(
        put_symbol,
        OrderType.MO,
        OrderSide.Sell,
        Decimal(1),
        TimeInForceType.Day
    )


if __name__ == "__main__":
    stock_code = "NVDA.US"
    # list_expiry_date = [date(2026, 1, 2), date(2026, 1, 9), date(2026, 1, 16), date(2026, 1, 23), date(2026, 1, 30)]
    list_expiry_date = [date(2026, 1, 30)]
    for expiry_date in list_expiry_date:
        collector = OptionsDataCollector(stock_code, expiry_date)
        max_pain_result = collector.collect_data()