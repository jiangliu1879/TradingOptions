"""
最大痛点价格分析页面

展示期权最大痛点价格的时间序列图表，支持按股票代码和到期日期筛选数据。
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime, date
import numpy as np

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.max_pain_result import MaxPainResult
from models.stock_max_pain_result import StockMaxPainResult


def calculate_volume_level():
    """
    计算成交量水位
    水位计算逻辑：从stock_max_pain_results表中读取全部sum_volume值并计算均值，
    用max_pain_results中最新的sum_volume除以前面计算的均值
    """
    try:
        # 从stock_max_pain_results表获取所有sum_volume值并计算均值
        stock_results = StockMaxPainResult.get_all_results()
        if not stock_results:
            return None, None, None
        
        stock_volumes = [result['sum_volume'] for result in stock_results if result['sum_volume'] > 0]
        if not stock_volumes:
            return None, None, None
        
        avg_volume = sum(stock_volumes) / len(stock_volumes)
        
        # 从max_pain_results表获取最新的sum_volume
        max_pain_results = MaxPainResult.get_max_pain_results()
        if not max_pain_results:
            return None, None, None
        
        # 按更新时间排序，获取最新的记录
        latest_result = max(max_pain_results, key=lambda x: x.update_time)
        latest_volume = latest_result.sum_volume
        
        # 计算水位（最新的成交量除以平均成交量）
        if avg_volume > 0:
            volume_level = latest_volume / avg_volume
        else:
            volume_level = 0
        
        return volume_level, latest_volume, avg_volume
        
    except Exception as e:
        st.error(f"❌ 计算成交量水位失败: {e}")
        return None, None, None


def load_max_pain_data():
    """从数据库加载最大痛点数据"""
    try:
        # 从数据库获取所有最大痛点结果
        results = MaxPainResult.get_max_pain_results()
        
        if not results:
            st.warning("⚠️ 数据库中没有最大痛点数据，请先运行数据收集和计算脚本")
            return pd.DataFrame()
        
        # 转换为DataFrame
        data_list = []
        for result in results:
            data_list.append({
                'stock_code': result.stock_code,
                'expiry_date': result.expiry_date,
                'update_time': result.update_time,
                'max_pain_price_volume': result.max_pain_price_volume,
                'max_pain_price_open_interest': result.max_pain_price_open_interest,
                'sum_volume': result.sum_volume,
                'volume_std_deviation': result.volume_std_deviation,
                'sum_open_interest': result.sum_open_interest
            })
        
        df = pd.DataFrame(data_list)
        
        if df.empty:
            st.warning("⚠️ 数据库查询结果为空")
            return df
        
        # 转换数据类型
        df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        df['update_time'] = pd.to_datetime(df['update_time'])
        
        return df
        
    except Exception as e:
        st.error(f"❌ 从数据库加载数据失败: {e}")
        import traceback
        st.error(f"详细错误信息: {traceback.format_exc()}")
        return pd.DataFrame()


def create_time_series_chart(df_filtered):
    """创建时间序列图表"""
    if df_filtered.empty:
        st.warning("⚠️ 没有数据可以显示")
        return
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('最大痛点价格 - Volume', '最大痛点价格 - Open Interest'),
        vertical_spacing=0.1,
        shared_xaxes=True
    )
    
    # 按股票代码和到期日期分组绘制
    colors = px.colors.qualitative.Set1
    
    for i, (stock_expiry, group) in enumerate(df_filtered.groupby(['stock_code', 'expiry_date'])):
        stock_code, expiry_date = stock_expiry
        color = colors[i % len(colors)]
        
        # 确保数据按时间排序
        group = group.sort_values('update_time')
        
        # Volume最大痛点价格
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_volume'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (Volume)',
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '最大痛点价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Open Interest最大痛点价格
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_open_interest'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (OI)',
                line=dict(color=color, width=2, dash='dash'),
                marker=dict(size=6),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '最大痛点价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            ),
            row=2, col=1
        )
    
    # 更新布局
    fig.update_layout(
        height=800,
        title={
            'text': '期权最大痛点价格时间序列',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 更新x轴
    fig.update_xaxes(
        title_text="更新时间",
        row=2, col=1
    )
    
    # 更新y轴
    fig.update_yaxes(
        title_text="最大痛点价格 ($)",
        row=1, col=1
    )
    fig.update_yaxes(
        title_text="最大痛点价格 ($)",
        row=2, col=1
    )
    
    # 格式化x轴时间显示
    fig.update_xaxes(
        tickformat="%m-%d %H:%M",
        tickangle=45
    )
    
    st.plotly_chart(fig, use_container_width=True)


def create_combined_chart(df_filtered):
    """创建合并图表"""
    if df_filtered.empty:
        return
    
    fig = go.Figure()
    
    # 按股票代码和到期日期分组绘制
    colors = px.colors.qualitative.Set1
    
    for i, (stock_expiry, group) in enumerate(df_filtered.groupby(['stock_code', 'expiry_date'])):
        stock_code, expiry_date = stock_expiry
        color = colors[i % len(colors)]
        
        # 确保数据按时间排序
        group = group.sort_values('update_time')
        
        # Volume最大痛点价格
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_volume'],
                mode='lines+markers',
                name=f'{stock_code} Volume - {expiry_date.strftime("%Y-%m-%d")}',
                line=dict(color=color, width=3),
                marker=dict(size=8),
                hovertemplate='<b>Volume最大痛点</b><br>' +
                            '时间: %{x}<br>' +
                            '价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            )
        )
        
        # Open Interest最大痛点价格
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_open_interest'],
                mode='lines+markers',
                name=f'{stock_code} OI - {expiry_date.strftime("%Y-%m-%d")}',
                line=dict(color=color, width=3, dash='dash'),
                marker=dict(size=8, symbol='diamond'),
                hovertemplate='<b>OI最大痛点</b><br>' +
                            '时间: %{x}<br>' +
                            '价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            )
        )
    
    # 更新布局
    fig.update_layout(
        height=600,
        title={
            'text': '最大痛点价格对比 (Volume vs Open Interest)',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis_title="更新时间",
        yaxis_title="最大痛点价格 ($)",
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 格式化x轴
    fig.update_xaxes(
        tickformat="%m-%d %H:%M",
        tickangle=45
    )
    
    st.plotly_chart(fig, use_container_width=True)


def create_volume_oi_chart(df_filtered):
    """创建成交量和持仓量图表"""
    if df_filtered.empty:
        st.warning("⚠️ 没有数据可以显示")
        return
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('成交量 (Sum Volume)', '持仓量 (Sum Open Interest)'),
        vertical_spacing=0.1,
        shared_xaxes=True
    )
    
    # 按股票代码和到期日期分组绘制
    colors = px.colors.qualitative.Set1
    
    for i, (stock_expiry, group) in enumerate(df_filtered.groupby(['stock_code', 'expiry_date'])):
        stock_code, expiry_date = stock_expiry
        color = colors[i % len(colors)]
        
        # 确保数据按时间排序
        group = group.sort_values('update_time')
        
        # 成交量曲线
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['sum_volume'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (Volume)',
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '成交量: %{y:,.0f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 持仓量曲线
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['sum_open_interest'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (OI)',
                line=dict(color=color, width=2, dash='dash'),
                marker=dict(size=6),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '持仓量: %{y:,.0f}<br>' +
                            '<extra></extra>'
            ),
            row=2, col=1
        )
    
    # 更新布局
    fig.update_layout(
        height=800,
        title={
            'text': '期权成交量和持仓量时间序列',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 更新x轴
    fig.update_xaxes(
        title_text="更新时间",
        row=2, col=1
    )
    
    # 更新y轴
    fig.update_yaxes(
        title_text="成交量",
        row=1, col=1,
        tickformat=",.0f"
    )
    fig.update_yaxes(
        title_text="持仓量",
        row=2, col=1,
        tickformat=",.0f"
    )
    
    # 格式化x轴时间显示
    fig.update_xaxes(
        tickformat="%m-%d %H:%M",
        tickangle=45
    )
    
    st.plotly_chart(fig, use_container_width=True)


def create_volume_std_deviation_chart(df_filtered):
    """创建成交量标准差图表"""
    if df_filtered.empty:
        st.warning("⚠️ 没有数据可以显示")
        return
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('成交量标准差 (Volume Std Deviation)', '成交量标准差 vs 最大痛点价格'),
        vertical_spacing=0.1,
        shared_xaxes=True
    )
    
    # 按股票代码和到期日期分组绘制
    colors = px.colors.qualitative.Set1
    
    for i, (stock_expiry, group) in enumerate(df_filtered.groupby(['stock_code', 'expiry_date'])):
        stock_code, expiry_date = stock_expiry
        color = colors[i % len(colors)]
        
        # 确保数据按时间排序
        group = group.sort_values('update_time')
        
        # 成交量标准差曲线
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['volume_std_deviation'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (Std Dev)',
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '成交量标准差: %{y:,.0f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 成交量标准差 vs 最大痛点价格散点图
        fig.add_trace(
            go.Scatter(
                x=group['volume_std_deviation'],
                y=group['max_pain_price_volume'],
                mode='markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (Scatter)',
                marker=dict(color=color, size=8),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '成交量标准差: %{x:,.0f}<br>' +
                            '最大痛点价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            ),
            row=2, col=1
        )
    
    # 更新布局
    fig.update_layout(
        height=800,
        title={
            'text': '期权成交量标准差分析',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    # 更新x轴
    fig.update_xaxes(
        title_text="更新时间",
        row=1, col=1
    )
    fig.update_xaxes(
        title_text="成交量标准差",
        row=2, col=1,
        tickformat=",.0f"
    )
    
    # 更新y轴
    fig.update_yaxes(
        title_text="成交量标准差",
        row=1, col=1,
        tickformat=",.0f"
    )
    fig.update_yaxes(
        title_text="最大痛点价格 ($)",
        row=2, col=1
    )
    
    # 格式化x轴时间显示
    fig.update_xaxes(
        tickformat="%m-%d %H:%M",
        tickangle=45,
        row=1, col=1
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    """主函数"""
    st.set_page_config(
        page_title="最大痛点价格分析",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 期权最大痛点价格分析")
    st.markdown("---")
    
    # 加载数据
    with st.spinner("🔄 正在从数据库加载最大痛点数据..."):
        df = load_max_pain_data()
    
    if df.empty:
        st.stop()
    
    # 侧边栏筛选器
    st.sidebar.header("🔍 数据筛选")
    
    # 股票代码筛选 - 单选
    available_stocks = df['stock_code'].unique()
    selected_stock = st.sidebar.selectbox(
        "选择股票代码",
        options=available_stocks,
        index=0 if len(available_stocks) > 0 else None,
        help="选择一个股票代码进行查看"
    )
    
    # 根据选择的股票代码筛选可用的到期日期，并按时间倒序排列（最近的在前面）
    if selected_stock:
        available_dates_for_stock = sorted(df[df['stock_code'] == selected_stock]['expiry_date'].unique(), reverse=True)
    else:
        available_dates_for_stock = []
    
    # 到期日期筛选 - 单选
    selected_date = st.sidebar.selectbox(
        "选择到期日期",
        options=available_dates_for_stock,
        index=0 if len(available_dates_for_stock) > 0 else None,
        format_func=lambda x: x.strftime('%Y-%m-%d') if x else '无数据',
        help="选择一个到期日期进行查看"
    )
    
    # 时间范围筛选
    if len(df) > 1:
        min_time = df['update_time'].min()
        max_time = df['update_time'].max()
        
        st.sidebar.subheader("⏰ 时间范围")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_time = st.date_input(
                "开始日期",
                value=min_time.date(),
                min_value=min_time.date(),
                max_value=max_time.date()
            )
        
        with col2:
            end_time = st.date_input(
                "结束日期",
                value=max_time.date(),
                min_value=min_time.date(),
                max_value=max_time.date()
            )
        
        # 时间筛选
        start_datetime = pd.Timestamp.combine(start_time, pd.Timestamp.min.time())
        end_datetime = pd.Timestamp.combine(end_time, pd.Timestamp.max.time())
        
        df_time_filtered = df[
            (df['update_time'] >= start_datetime) & 
            (df['update_time'] <= end_datetime)
        ]
    else:
        df_time_filtered = df
    
    # 应用筛选 - 基于单选结果
    if selected_stock and selected_date:
        df_filtered = df_time_filtered[
            (df_time_filtered['stock_code'] == selected_stock) &
            (df_time_filtered['expiry_date'] == selected_date)
        ]
    else:
        df_filtered = pd.DataFrame()  # 如果没有选择，显示空数据
    
    # 检查是否选择了股票和到期日期
    if not selected_stock or not selected_date:
        st.warning("⚠️ 请选择股票代码和到期日期来查看数据")
        st.stop()
    
    # 检查是否有数据
    if df_filtered.empty:
        st.warning(f"⚠️ 没有找到 {selected_stock} 在 {selected_date.strftime('%Y-%m-%d')} 的数据")
        st.stop()
    
    # 计算并显示成交量水位
    volume_level, latest_volume, avg_volume = calculate_volume_level()
    
    # 显示当前选择的股票和到期日期以及成交量水位
    if volume_level is not None:
        # 根据水位值设置颜色和图标
        if volume_level >= 1.5:
            level_emoji = "🔥"
            level_color = "red"
            level_text = "高水位"
        elif volume_level >= 1.2:
            level_emoji = "⚡"
            level_color = "orange"
            level_text = "中高水位"
        elif volume_level >= 0.8:
            level_emoji = "📊"
            level_color = "blue"
            level_text = "正常水位"
        else:
            level_emoji = "📉"
            level_color = "green"
            level_text = "低水位"
        
        st.info(
            f"{level_emoji} **成交量水位: {level_text}** ({volume_level:.2f}x)  |  "
            f"最新成交量: {latest_volume:,.0f}  |  平均成交量: {avg_volume:,.0f}"
        )
    else:
        st.info(f"📊 当前查看: **{selected_stock}** - **{selected_date.strftime('%Y-%m-%d')}**")
    
    # 图表显示选项
    chart_type = st.selectbox(
        "选择图表类型",
        ["时间序列图表", "合并对比图表", "成交量和持仓量图表", "成交量标准差分析"],
        help="选择要显示的图表类型"
    )
    
    if chart_type == "时间序列图表":
        st.subheader("📊 最大痛点价格时间序列")
        create_time_series_chart(df_filtered)
    elif chart_type == "合并对比图表":
        st.subheader("📊 最大痛点价格对比")
        create_combined_chart(df_filtered)
    elif chart_type == "成交量和持仓量图表":
        st.subheader("📊 成交量和持仓量时间序列")
        create_volume_oi_chart(df_filtered)
    else:
        st.subheader("📊 成交量标准差分析")
        create_volume_std_deviation_chart(df_filtered)


if __name__ == "__main__":
    main()
