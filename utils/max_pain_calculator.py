"""
Max Pain Calculator Utility

This module provides a reusable utility class for calculating max pain from options data.
Max pain is the price at which the maximum number of options contracts would expire worthless,
causing maximum pain to option holders.

The calculator supports both volume-based and open interest-based max pain calculations,
along with volume standard deviation analysis around the max pain price.
"""

import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import date


class MaxPainCalculator:
    """
    A utility class for calculating max pain from options data.
    
    Max pain calculation works by:
    1. For each strike price, calculate the total volume/open interest that would expire worthless
    2. The strike price with the minimum total expiring volume/open interest is the max pain price
    """
    
    @staticmethod
    def calculate_max_pain_from_options_data(
        data_list: List[Dict[str, Dict[str, Dict[str, int]]]], 
        include_volume_std: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate max pain from a list of options data.
        
        Args:
            data_list: List of option data dictionaries in format:
                      [{strike_price: {"volume": {"put": int, "call": int}, 
                                     "open_interest": {"put": int, "call": int}}}, ...]
            include_volume_std: Whether to calculate volume standard deviation
            
        Returns:
            Dict containing max pain calculation results:
            {
                'max_pain_price_volume': float,
                'max_pain_price_open_interest': float,
                'sum_volume': int,
                'sum_open_interest': int,
                'volume_std_deviation': float (if include_volume_std=True),
                'max_pain_index': int,
                'min_earn_volume': float,
                'min_earn_open_interest': float
            }
        """
        if not data_list:
            return {
                'max_pain_price_volume': 0,
                'max_pain_price_open_interest': 0,
                'sum_volume': 0,
                'sum_open_interest': 0,
                'volume_std_deviation': 0.0,
                'max_pain_index': 0,
                'min_earn_volume': float('inf'),
                'min_earn_open_interest': float('inf')
            }
        
        min_earn_volume = float('inf')
        min_earn_open_interest = float('inf')
        max_pain_price_volume = 0
        max_pain_price_open_interest = 0
        max_pain_index = 0
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
                max_pain_index = i
            
            # 更新基于open_interest的最大痛点
            if total_earn_open_interest < min_earn_open_interest:
                min_earn_open_interest = total_earn_open_interest
                max_pain_price_open_interest = current_strike_price

        # 计算最大痛点价格及其左右3档行权价的volume标准差
        volume_std_deviation = 0.0
        if include_volume_std:
            volume_std_deviation = MaxPainCalculator.calculate_volume_std_deviation(data_list, max_pain_index)

        return {
            'max_pain_price_volume': max_pain_price_volume,
            'max_pain_price_open_interest': max_pain_price_open_interest,
            'sum_volume': sum_volume,
            'sum_open_interest': sum_open_interest,
            'volume_std_deviation': volume_std_deviation,
            'max_pain_index': max_pain_index,
            'min_earn_volume': min_earn_volume,
            'min_earn_open_interest': min_earn_open_interest
        }
    
    @staticmethod
    def calculate_volume_std_deviation(data_list: List[Dict], current_index: int) -> float:
        """
        计算当前行权价及其左右3档行权价的volume标准差
        
        Args:
            data_list: 期权数据列表
            current_index: 当前行权价的索引
            
        Returns:
            float: volume标准差
        """
        # 获取当前行权价及其左右3档的索引范围
        start_index = max(0, current_index - 3)
        end_index = min(len(data_list), current_index + 4)  # +4 因为要包含当前行权价
        
        volumes = []
        
        # 收集指定范围内的volume数据
        for i in range(start_index, end_index):
            strike_price = list(data_list[i].keys())[0]
            put_volume = data_list[i][strike_price]['volume']['put']
            call_volume = data_list[i][strike_price]['volume']['call']
            total_volume = put_volume + call_volume
            volumes.append(total_volume)
        
        # 计算标准差
        if len(volumes) > 1:
            import numpy as np
            return np.round(statistics.stdev(volumes), 2)
        else:
            return 0.0
    
    @staticmethod
    def calculate_max_pain_with_metadata(
        stock_code: str,
        expiry_date: date,
        update_time: str,
        data_list: List[Dict[str, Dict[str, Dict[str, int]]]],
        include_volume_std: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate max pain with additional metadata for database storage.
        
        Args:
            stock_code: Stock symbol (e.g., 'SPY.US')
            expiry_date: Option expiry date
            update_time: Data update timestamp
            data_list: List of option data dictionaries
            include_volume_std: Whether to calculate volume standard deviation
            
        Returns:
            Dict containing max pain results with metadata, or None if no data
        """
        if not data_list:
            return None
            
        # Calculate max pain
        max_pain_result = MaxPainCalculator.calculate_max_pain_from_options_data(
            data_list, include_volume_std
        )
        
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
            f"(min earn: {result['min_earn_volume']:,.0f})\n"
            f"  Open Interest-based: ${result['max_pain_price_open_interest']:.0f} "
            f"(min earn: {result['min_earn_open_interest']:,.0f})\n"
            f"  Total Volume: {result['sum_volume']:,}\n"
            f"  Total Open Interest: {result['sum_open_interest']:,}\n"
            f"  Volume Std Dev: {result['volume_std_deviation']:.2f}"
        )


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


def calculate_volume_std_deviation(data_list: List[Dict], current_index: int) -> float:
    """
    Convenience function for calculating volume standard deviation.
    
    Args:
        data_list: List of option data dictionaries
        current_index: Current strike price index
        
    Returns:
        Volume standard deviation
    """
    return MaxPainCalculator.calculate_volume_std_deviation(data_list, current_index)
