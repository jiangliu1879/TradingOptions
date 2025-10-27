"""
SPY 期权数据分析工具

此脚本读取 spy_options_data.csv 中的数据，分析每个交易日的最大痛点价格，
并计算新的偏离程度指标来衡量 max pain price 的 Volume 与周围 strike price 的偏离程度。
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from collections import defaultdict
import os
import sys
from typing import Dict, List, Tuple, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.max_pain_calculator import MaxPainCalculator


def load_spy_options_data(csv_path: str) -> pd.DataFrame:
    """
    加载 SPY 期权数据
    
    Args:
        csv_path: CSV 文件路径
        
    Returns:
        pd.DataFrame: 期权数据
    """
    try:
        print(f"📂 正在加载数据: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # 转换日期格式
        df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        df['update_time'] = pd.to_datetime(df['update_time'])
        
        # 按 update_time 排序
        df = df.sort_values('update_time')
        
        print(f"✅ 成功加载 {len(df)} 条记录")
        print(f"📅 数据时间范围: {df['update_time'].min()} 到 {df['update_time'].max()}")
        
        return df
        
    except Exception as e:
        print(f"❌ 加载数据失败: {e}")
        raise


def group_options_by_date_and_strike(df: pd.DataFrame) -> Dict[str, Dict[float, Dict[str, Any]]]:
    """
    按交易日期和行权价分组期权数据
    
    Args:
        df: 期权数据DataFrame
        
    Returns:
        Dict: 分组后的数据结构
        {
            'YYYY-MM-DD': {
                strike_price: {
                    'call_volume': int,
                    'put_volume': int,
                    'call_open_interest': int,
                    'put_open_interest': int,
                    'stock_close_price': float
                }
            }
        }
    """
    print("🔄 正在按交易日期和行权价分组数据...")
    
    grouped_data = defaultdict(lambda: defaultdict(lambda: {
        'call_volume': 0,
        'put_volume': 0,
        'call_open_interest': 0,
        'put_open_interest': 0,
        'stock_close_price': 0
    }))
    
    for _, row in df.iterrows():
        # 使用日期作为键（不包含时间）
        date_key = row['update_time'].strftime('%Y-%m-%d')
        strike_price = float(row['strike_price'])
        option_type = row['type']
        
        # 更新对应类型的数据
        if option_type == 'call':
            grouped_data[date_key][strike_price]['call_volume'] = row['volume']
            grouped_data[date_key][strike_price]['call_open_interest'] = row['open_interest']
        else:  # put
            grouped_data[date_key][strike_price]['put_volume'] = row['volume']
            grouped_data[date_key][strike_price]['put_open_interest'] = row['open_interest']
        
        # 设置股票收盘价（所有记录应该相同，取最后一个）
        grouped_data[date_key][strike_price]['stock_close_price'] = row['stock_close_price']
    
    print(f"✅ 成功分组 {len(grouped_data)} 个交易日的数据")
    return dict(grouped_data)


def calculate_max_pain_for_date(date_data: Dict[float, Dict[str, Any]]) -> Tuple[float, int, int]:
    """
    计算单个交易日的最大痛点价格
    
    Args:
        date_data: 单个交易日的期权数据
        
    Returns:
        Tuple: (max_pain_price, total_volume, max_pain_volume)
    """
    if not date_data:
        return 0.0, 0, 0
    
    # 转换为 MaxPainCalculator 需要的格式
    data_list = []
    total_volume = 0
    
    for strike_price in sorted(date_data.keys()):
        strike_data = date_data[strike_price]
        
        # 计算总成交量
        call_volume = strike_data['call_volume']
        put_volume = strike_data['put_volume']
        total_volume += call_volume + put_volume
        
        # 构建数据格式
        option_data = {
            strike_price: {
                'volume': {
                    'call': call_volume,
                    'put': put_volume
                },
                'open_interest': {
                    'call': strike_data['call_open_interest'],
                    'put': strike_data['put_open_interest']
                }
            }
        }
        data_list.append(option_data)
    
    # 使用 MaxPainCalculator 计算最大痛点
    max_pain_result = MaxPainCalculator.calculate_max_pain_from_options_data(data_list, include_volume_std=False)
    
    # 获取最大痛点价格对应的成交量
    max_pain_price = max_pain_result['max_pain_price_volume']
    max_pain_volume = 0
    
    for strike_price in sorted(date_data.keys()):
        if abs(strike_price - max_pain_price) < 0.01:  # 允许小的浮点数误差
            max_pain_volume = date_data[strike_price]['call_volume'] + date_data[strike_price]['put_volume']
            break
    
    return max_pain_price, total_volume, max_pain_volume


def calculate_volume_deviation_metric(date_data: Dict[float, Dict[str, Any]], max_pain_price: float) -> Dict[str, float]:
    """
    计算最大痛点价格的成交量偏离程度指标
    
    设计思路：
    1. 找到最大痛点价格对应的成交量
    2. 计算周围 strike price 的成交量均值
    3. 使用多个指标衡量偏离程度：
       - 相对偏离度：最大痛点成交量 / 周围均值
       - 标准化偏离度：使用 Z-score
       - 分位数偏离度：最大痛点成交量在整体中的分位数
    
    Args:
        date_data: 单个交易日的期权数据
        max_pain_price: 最大痛点价格
        
    Returns:
        Dict: 包含各种偏离度指标的字典
    """
    if not date_data or max_pain_price == 0:
        return {
            'max_pain_volume': 0,
            'surrounding_avg_volume': 0,
            'relative_deviation': 0,
            'z_score_deviation': 0,
            'percentile_deviation': 0,
            'volume_concentration_index': 0
        }
    
    # 收集所有行权价的成交量数据
    strike_volumes = []
    max_pain_volume = 0
    
    for strike_price, data in date_data.items():
        total_volume = data['call_volume'] + data['put_volume']
        strike_volumes.append(total_volume)
        
        # 找到最大痛点价格对应的成交量
        if abs(strike_price - max_pain_price) < 0.01:  # 允许小的浮点数误差
            max_pain_volume = total_volume
    
    if not strike_volumes:
        return {
            'max_pain_volume': 0,
            'surrounding_avg_volume': 0,
            'relative_deviation': 0,
            'z_score_deviation': 0,
            'percentile_deviation': 0,
            'volume_concentration_index': 0
        }
    
    # 计算各种偏离度指标
    volumes_array = np.array(strike_volumes)
    
    # 1. 周围成交量均值（排除最大痛点价格本身）
    surrounding_volumes = volumes_array[volumes_array != max_pain_volume]
    surrounding_avg_volume = np.mean(surrounding_volumes) if len(surrounding_volumes) > 0 else np.mean(volumes_array)
    
    # 2. 相对偏离度
    relative_deviation = max_pain_volume / surrounding_avg_volume if surrounding_avg_volume > 0 else 0
    
    # 3. 标准化偏离度（Z-score）
    volume_mean = np.mean(volumes_array)
    volume_std = np.std(volumes_array)
    z_score_deviation = (max_pain_volume - volume_mean) / volume_std if volume_std > 0 else 0
    
    # 4. 分位数偏离度
    percentile_deviation = (np.sum(volumes_array <= max_pain_volume) / len(volumes_array)) * 100
    
    # 5. 成交量集中度指数（最大痛点成交量占总成交量的比例）
    total_volume = np.sum(volumes_array)
    volume_concentration_index = max_pain_volume / total_volume if total_volume > 0 else 0
    
    return {
        'max_pain_volume': max_pain_volume,
        'surrounding_avg_volume': surrounding_avg_volume,
        'relative_deviation': relative_deviation,
        'z_score_deviation': z_score_deviation,
        'percentile_deviation': percentile_deviation,
        'volume_concentration_index': volume_concentration_index
    }


def analyze_spy_options_data(csv_path: str, output_path: str):
    """
    分析 SPY 期权数据并生成报告
    
    Args:
        csv_path: 输入 CSV 文件路径
        output_path: 输出 CSV 文件路径
    """
    print("🚀 开始分析 SPY 期权数据")
    print("=" * 50)
    
    # 1. 加载数据
    df = load_spy_options_data(csv_path)
    
    # 2. 按日期和行权价分组
    grouped_data = group_options_by_date_and_strike(df)
    
    # 3. 分析每个交易日
    analysis_results = []
    
    print("🔄 正在分析每个交易日的最大痛点价格...")
    
    for date_str, date_data in grouped_data.items():
        try:
            # 计算最大痛点价格
            max_pain_price, total_volume, max_pain_volume = calculate_max_pain_for_date(date_data)
            
            # 计算偏离程度指标
            deviation_metrics = calculate_volume_deviation_metric(date_data, max_pain_price)
            
            # 获取股票收盘价
            stock_close_price = list(date_data.values())[0]['stock_close_price'] if date_data else 0
            
            # 构建结果记录
            result = {
                'date': date_str,
                'stock_close_price': stock_close_price,
                'max_pain_price': max_pain_price,
                'max_pain_volume': max_pain_volume,
                'total_volume': total_volume,
                **deviation_metrics
            }
            
            analysis_results.append(result)
            
            print(f"  📅 {date_str}: 最大痛点 ${max_pain_price:.0f}, 偏离度 {deviation_metrics['relative_deviation']:.2f}x")
            
        except Exception as e:
            print(f"  ❌ 分析 {date_str} 失败: {e}")
            continue
    
    # 4. 保存结果到 CSV
    if analysis_results:
        results_df = pd.DataFrame(analysis_results)
        
        # 按日期排序
        results_df['date'] = pd.to_datetime(results_df['date'])
        results_df = results_df.sort_values('date')
        results_df['date'] = results_df['date'].dt.strftime('%Y-%m-%d')
        
        # 保存到文件
        results_df.to_csv(output_path, index=False, encoding='utf-8')
        
        print(f"\n✅ 分析完成！")
        print(f"📊 分析了 {len(analysis_results)} 个交易日")
        print(f"💾 结果已保存到: {output_path}")
        
        # 显示统计摘要
        print(f"\n📈 统计摘要:")
        print(f"   平均最大痛点价格: ${results_df['max_pain_price'].mean():.2f}")
        print(f"   平均相对偏离度: {results_df['relative_deviation'].mean():.2f}x")
        print(f"   平均成交量集中度: {results_df['volume_concentration_index'].mean():.3f}")
        print(f"   最高偏离度: {results_df['relative_deviation'].max():.2f}x")
        print(f"   最低偏离度: {results_df['relative_deviation'].min():.2f}x")
        
        return results_df
    else:
        print("❌ 没有生成任何分析结果")
        return None


def main():
    """主函数"""
    # 文件路径
    csv_path = "data/options/spy_options_data.csv"
    output_path = "data/result/spy_max_pain_analysis.csv"
    
    # 检查输入文件是否存在
    if not os.path.exists(csv_path):
        print(f"❌ 输入文件不存在: {csv_path}")
        return
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 执行分析
    results = analyze_spy_options_data(csv_path, output_path)
    
    if results is not None:
        print(f"\n🎉 SPY 期权数据分析完成！")
        print(f"📁 详细结果请查看: {output_path}")


if __name__ == "__main__":
    main()
