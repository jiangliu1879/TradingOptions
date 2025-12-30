"""
Max Pain Calculator Utility

This module provides a reusable utility class for calculating max pain from options data.
Max pain is the price at which the maximum number of options contracts would expire worthless,
causing maximum pain to option holders.

The calculator supports both volume-based and open interest-based max pain calculations,
along with volume standard deviation analysis around the max pain price.
"""

import os
import sys
# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import date
from collections import defaultdict
from models.options_data import OptionsData



class MaxPainCalculator:
    """
    A utility class for calculating max pain from options data.
    
    Max pain calculation works by:
    1. For each strike price, calculate the total volume/open interest that would expire worthless
    2. The strike price with the minimum total expiring volume/open interest is the max pain price
    """
    
    @staticmethod
    def calculate_max_pain_from_options_data(
        data_list: List[Dict[str, Dict[str, Dict[str, int]]]]
    ) -> Dict[str, Any]:
        """
        Calculate max pain from a list of options data.
        
        Args:
            data_list: List of option data dictionaries in format:
                      [{strike_price: {"volume": {"put": int, "call": int}, 
                                     "open_interest": {"put": int, "call": int}}}, ...]
        Returns:
            Dict containing max pain calculation results:
            {
                'max_pain_price_volume': float,
                'max_pain_price_open_interest': float,
                'sum_volume': int,
                'sum_open_interest': int
            }
        """
        if not data_list:
            return {
                'max_pain_price_volume': 0,
                'max_pain_price_open_interest': 0,
                'sum_volume': 0,
                'sum_open_interest': 0
            }
        
        min_earn_volume = float('inf')
        min_earn_open_interest = float('inf')
        max_pain_price_volume = 0
        max_pain_price_open_interest = 0
        max_pain_index_volume = 0
        max_pain_index_open_interest = 0
        sum_volume = 0
        sum_open_interest = 0
        
        # 遍历每个行权价，计算在该价格到期时的期权卖方收益
        for i in range(len(data_list)):
            put_earn_volume = 0
            put_earn_open_interest = 0
            call_earn_volume = 0
            call_earn_open_interest = 0
            
            # 计算高于当前行权价的put期权收益
            # 如果股价在put行权价以下，put期权买方盈利，卖方亏损
            for data_item in data_list[i + 1:]:
                strike_price = list(data_item.keys())[0]
                put_earn_volume += data_item[strike_price]['volume']['put']
                put_earn_open_interest += data_item[strike_price]['open_interest']['put']
                sum_volume += data_item[strike_price]['volume']['put']
                sum_open_interest += data_item[strike_price]['open_interest']['put']
            
            # 计算低于当前行权价的call期权收益
            # 如果股价在call行权价以上，call期权买方盈利，卖方亏损
            for data_item in data_list[:i]:
                strike_price = list(data_item.keys())[0]
                call_earn_volume += data_item[strike_price]['volume']['call']
                call_earn_open_interest += data_item[strike_price]['open_interest']['call']
                sum_volume += data_item[strike_price]['volume']['call']
                sum_open_interest += data_item[strike_price]['open_interest']['call']

            current_strike_price = list(data_list[i].keys())[0]
            total_earn_volume = put_earn_volume + call_earn_volume
            total_earn_open_interest = put_earn_open_interest + call_earn_open_interest
            
            # 更新基于volume的最大痛点
            if total_earn_volume < min_earn_volume:
                min_earn_volume = total_earn_volume
                max_pain_price_volume = current_strike_price
                max_pain_index_volume = i
            
            # 更新基于open_interest的最大痛点
            if total_earn_open_interest < min_earn_open_interest:
                min_earn_open_interest = total_earn_open_interest
                max_pain_price_open_interest = current_strike_price
                max_pain_index_open_interest = i
                
        volume_strike_price = data_list[max_pain_index_volume][max_pain_price_volume]['volume']['put'] + data_list[max_pain_index_volume][max_pain_price_volume]['volume']['call']
        open_interest_strike_price = data_list[max_pain_index_open_interest][max_pain_price_open_interest]['open_interest']['put'] + data_list[max_pain_index_open_interest][max_pain_price_open_interest]['open_interest']['call']

        return {
            'max_pain_price_volume': max_pain_price_volume,
            'max_pain_price_open_interest': max_pain_price_open_interest,
            'sum_volume': sum_volume,
            'sum_open_interest': sum_open_interest,
            'volume_strike_price': volume_strike_price,
            'open_interest_strike_price': open_interest_strike_price
        }
    
    @staticmethod
    def calculate_max_pain_with_metadata(
        stock_code: str,
        expiry_date: date,
        update_time: str,
        data_list: List[Dict[str, Dict[str, Dict[str, int]]]]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate max pain with additional metadata for database storage.
        
        Args:
            stock_code: Stock symbol (e.g., 'SPY.US')
            expiry_date: Option expiry date
            update_time: Data update timestamp
            data_list: List of option data dictionaries
            
        Returns:
            Dict containing max pain results with metadata, or None if no data
        """
        if not data_list:
            return None
            
        # Calculate max pain
        max_pain_result = MaxPainCalculator.calculate_max_pain_from_options_data(data_list)
        
        # Add metadata
        result = {
            'stock_code': stock_code,
            'expiry_date': expiry_date,
            'update_time': update_time,
            **max_pain_result
        }
        
        return result
    
    @staticmethod
    def format_max_pain_result(result: Dict[str, Any]) -> str:
        """
        Format max pain calculation result for logging/display.
        
        Args:
            result: Max pain calculation result
            
        Returns:
            Formatted string representation
        """
        return (
            f"Max Pain Results:\n"
            f"  Volume-based: ${result['max_pain_price_volume']:.0f} "
            f"  Open Interest-based: ${result['max_pain_price_open_interest']:.0f} "
            f"  Total Volume: {result['sum_volume']:,}\n"
            f"  Total Open Interest: {result['sum_open_interest']:,}\n"
        )

    @staticmethod
    def calculate_max_pain2(data_list: list):
        sum_volume = 0
        sum_open_interest = 0
        for item in items:
            print(item.type, item.strike_price, item.volume, item.open_interest)
        #     sum_volume += item.volume
        #     sum_open_interest += item.open_interest
        # print(f"sum_volume: {sum_volume}, sum_open_interest: {sum_open_interest}")
        print("===============================\n\n")
        # min_earn_volume = float('inf')
        # min_earn_open_interest = float('inf')
        # max_pain_price_volume = 0
        # max_pain_price_open_interest = 0
        # max_pain_index = 0
        # sum_volume = 0
        # sum_open_interest = 0
        
        # # 遍历每个行权价，计算在该价格到期时的期权卖方收益
        # for i in range(len(data_list)):
        #     put_earn_volume = 0
        #     put_earn_open_interest = 0
        #     call_earn_volume = 0
        #     call_earn_open_interest = 0
            
        #     # 计算高于当前行权价的put期权收益
        #     # 如果股价在put行权价以下，put期权买方盈利，卖方亏损
        #     for data_item in data_list[i + 1:]:
        #         strike_price = list(data_item.keys())[0]
        #         put_earn_volume += data_item[strike_price]['volume']['put']
        #         put_earn_open_interest += data_item[strike_price]['open_interest']['put']
        #         sum_volume += data_item[strike_price]['volume']['put']
        #         sum_open_interest += data_item[strike_price]['open_interest']['put']
            
        #     # 计算低于当前行权价的call期权收益
        #     # 如果股价在call行权价以上，call期权买方盈利，卖方亏损
        #     for data_item in data_list[:i]:
        #         strike_price = list(data_item.keys())[0]
        #         call_earn_volume += data_item[strike_price]['volume']['call']
        #         call_earn_open_interest += data_item[strike_price]['open_interest']['call']
        #         sum_volume += data_item[strike_price]['volume']['call']
        #         sum_open_interest += data_item[strike_price]['open_interest']['call']

        #     current_strike_price = list(data_list[i].keys())[0]
        #     total_earn_volume = put_earn_volume + call_earn_volume
        #     total_earn_open_interest = put_earn_open_interest + call_earn_open_interest
            
        #     # 更新基于volume的最大痛点
        #     if total_earn_volume < min_earn_volume:
        #         min_earn_volume = total_earn_volume
        #         max_pain_price_volume = current_strike_price
        #         max_pain_index = i
            
        #     # 更新基于open_interest的最大痛点
        #     if total_earn_open_interest < min_earn_open_interest:
        #         min_earn_open_interest = total_earn_open_interest
        #         max_pain_price_open_interest = current_strike_price

        # return {
        #     'max_pain_price_volume': max_pain_price_volume,
        #     'max_pain_price_open_interest': max_pain_price_open_interest,
        #     'sum_volume': sum_volume,
        #     'sum_open_interest': sum_open_interest
        # }


# Convenience functions for backward compatibility
def calculate_max_pain_from_data(data_list: List[Dict[str, Dict[str, Dict[str, int]]]]) -> Dict[str, Any]:
    """
    Convenience function for calculating max pain from options data.
    
    Args:
        data_list: List of option data dictionaries
        
    Returns:
        Dict containing max pain calculation results
    """
    return MaxPainCalculator.calculate_max_pain_from_options_data(data_list)


if __name__ == "__main__":
    stock_code = "SPY.US"
    expiry_date = date(2025, 12, 12)
    data_list = OptionsData.get_options_data(stock_code, expiry_date)
    
    # 按照update_time分组
    grouped_by_time = defaultdict(list)
    for data_item in data_list:
        grouped_by_time[data_item.update_time].append(data_item)
    
    # 每组数据按照strike_price从小到大排序
    for update_time in grouped_by_time:
        grouped_by_time[update_time].sort(key=lambda x: x.strike_price)
    
    print(f"数据总数: {len(data_list)}")
    print(f"按update_time分组后的组数: {len(grouped_by_time)}")
    for update_time, items in sorted(grouped_by_time.items()):
        MaxPainCalculator.calculate_max_pain2(items)
