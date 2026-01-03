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
from models.options_data import OptionsData


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
                'volume_strike_price': result.volume_strike_price,
                'max_pain_price_open_interest': result.max_pain_price_open_interest,
                'open_interest_strike_price': result.open_interest_strike_price,
                'sum_volume': result.sum_volume,
                'sum_open_interest': result.sum_open_interest,
                'stock_price': result.stock_price
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


def calculate_volume_level(stock_code, expiry_date):
    """
    计算成交量水位
    
    Args:
        stock_code: 股票代码
        expiry_date: 到期日期
    
    Returns:
        tuple: (volume_level, latest_volume, max_volume)
    """
    try:
        # max_volume: 通过stock_code筛选出的所有数据中最大的sum_volume
        results_by_stock = MaxPainResult.get_max_pain_results(stock_code=stock_code)
        if not results_by_stock:
            return None, None, None
        
        stock_volumes = [result.sum_volume for result in results_by_stock if result.sum_volume and result.sum_volume > 0]
        if not stock_volumes:
            return None, None, None
        
        max_volume = max(stock_volumes)
        
        # latest_volume: 通过stock_code、expiry_date筛选出的所有数据中最新的sum_volume
        results_by_stock_and_date = MaxPainResult.get_max_pain_results(
            stock_code=stock_code,
            expiry_date=expiry_date
        )
        if not results_by_stock_and_date:
            return None, None, None
        
        # 按更新时间排序，获取最新的记录
        latest_result = max(results_by_stock_and_date, key=lambda x: x.update_time)
        latest_volume = latest_result.sum_volume if latest_result.sum_volume else 0
        
        # 计算水位（最新的成交量除以最大成交量）
        if max_volume > 0:
            volume_level = latest_volume / max_volume
        else:
            volume_level = 0
        
        return volume_level, latest_volume, max_volume
        
    except Exception as e:
        st.error(f"❌ 计算成交量水位失败: {e}")
        import traceback
        st.error(f"详细错误信息: {traceback.format_exc()}")
        return None, None, None


def create_time_series_chart(df_filtered):
    """创建时间序列图表"""
    if df_filtered.empty:
        st.warning("⚠️ 没有数据可以显示")
        return
    
    # 创建子图（5行：最大痛点价格Volume、最大痛点价格OI、股票价格、成交量、持仓量）
    fig = make_subplots(
        rows=5, cols=1,
        subplot_titles=('最大痛点价格 - Volume', '最大痛点价格 - Open Interest', '股票价格', 
                       '成交量 (Sum Volume)', '持仓量 (Sum Open Interest)'),
        vertical_spacing=0.08,
        shared_xaxes=True
    )
    
    # 定义三种固定的颜色
    volume_color = '#1f77b4'      # 蓝色 - Volume最大痛点价格
    oi_color = '#ff7f0e'          # 橙色 - Open Interest最大痛点价格
    stock_color = '#2ca02c'       # 绿色 - 股票价格
    
    # 按股票代码和到期日期分组绘制
    colors = px.colors.qualitative.Set1
    
    for i, (stock_expiry, group) in enumerate(df_filtered.groupby(['stock_code', 'expiry_date'])):
        stock_code, expiry_date = stock_expiry
        color = colors[i % len(colors)]
        
        # 确保数据按时间排序
        group = group.sort_values('update_time')
        
        # Volume最大痛点价格 - 使用蓝色
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_volume'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (Volume)',
                line=dict(color=volume_color, width=2),
                marker=dict(size=6, color=volume_color),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '最大痛点价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Open Interest最大痛点价格 - 使用橙色
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_open_interest'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (OI)',
                line=dict(color=oi_color, width=2),
                marker=dict(size=6, color=oi_color),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '最大痛点价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 股票价格 - 使用绿色
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['stock_price'],
                mode='lines+markers',
                name=f'{stock_code} - {expiry_date.strftime("%Y-%m-%d")} (Stock Price)',
                line=dict(color=stock_color, width=2),
                marker=dict(size=6, color=stock_color),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '时间: %{x}<br>' +
                            '股票价格: $%{y:.2f}<br>' +
                            '<extra></extra>'
            ),
            row=3, col=1
        )
        
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
            row=4, col=1
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
            row=5, col=1
        )
    
    # 更新布局
    fig.update_layout(
        height=1400,
        title={
            'text': '期权最大痛点价格、股票价格、成交量和持仓量时间序列',
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
        row=5, col=1
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
    fig.update_yaxes(
        title_text="股票价格 ($)",
        row=3, col=1
    )
    fig.update_yaxes(
        title_text="成交量",
        row=4, col=1,
        tickformat=",.0f"
    )
    fig.update_yaxes(
        title_text="持仓量",
        row=5, col=1,
        tickformat=",.0f"
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
    
    # 创建子图（4行：价格对比、成交量、持仓量、成交量与持仓量对比）
    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=('最大痛点价格与股票价格对比', '成交量 (Sum Volume)', '持仓量 (Sum Open Interest)'),
        vertical_spacing=0.1,
        shared_xaxes=True
    )
    
    # 定义三种固定的颜色
    volume_color = '#1f77b4'      # 蓝色 - Volume最大痛点价格
    oi_color = '#ff7f0e'          # 橙色 - Open Interest最大痛点价格
    stock_color = '#2ca02c'       # 绿色 - 股票价格
    
    # 定义不同的标记符号用于区分不同的股票/到期日期组合
    marker_symbols = ['circle', 'square', 'diamond', 'triangle-up', 'triangle-down', 
                     'star', 'pentagon', 'hexagon', 'cross', 'x']
    
    colors = px.colors.qualitative.Set1
    
    # 按股票代码和到期日期分组绘制
    for i, (stock_expiry, group) in enumerate(df_filtered.groupby(['stock_code', 'expiry_date'])):
        stock_code, expiry_date = stock_expiry
        symbol = marker_symbols[i % len(marker_symbols)]
        color = colors[i % len(colors)]
        
        # 确保数据按时间排序
        group = group.sort_values('update_time')
        
        # 第一行：价格对比
        # Volume最大痛点价格 - 使用蓝色
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_volume'],
                mode='lines+markers',
                name=f'{stock_code} Volume - {expiry_date.strftime("%Y-%m-%d")}',
                line=dict(color=volume_color, width=3),
                marker=dict(size=8, color=volume_color, symbol=symbol),
                hovertemplate='<b>Volume最大痛点</b><br>' +
                            '时间: %{x}<br>' +
                            '价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Open Interest最大痛点价格 - 使用橙色
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['max_pain_price_open_interest'],
                mode='lines+markers',
                name=f'{stock_code} OI - {expiry_date.strftime("%Y-%m-%d")}',
                line=dict(color=oi_color, width=3),
                marker=dict(size=8, color=oi_color, symbol=symbol),
                hovertemplate='<b>OI最大痛点</b><br>' +
                            '时间: %{x}<br>' +
                            '价格: $%{y:.0f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 股票价格 - 使用绿色
        fig.add_trace(
            go.Scatter(
                x=group['update_time'],
                y=group['stock_price'],
                mode='lines+markers',
                name=f'{stock_code} 股票价格 - {expiry_date.strftime("%Y-%m-%d")}',
                line=dict(color=stock_color, width=3),
                marker=dict(size=8, color=stock_color, symbol=symbol),
                hovertemplate='<b>股票价格</b><br>' +
                            '时间: %{x}<br>' +
                            '价格: $%{y:.2f}<br>' +
                            '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 第二行：成交量
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
            row=2, col=1
        )
        
        # 第三行：持仓量
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
            row=3, col=1
        )
    
    # 更新布局
    fig.update_layout(
        height=1200,
        title={
            'text': '最大痛点价格、股票价格、成交量和持仓量对比',
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
        row=4, col=1
    )
    
    # 更新y轴
    fig.update_yaxes(
        title_text="价格 ($)",
        row=1, col=1
    )
    fig.update_yaxes(
        title_text="成交量",
        row=2, col=1,
        tickformat=",.0f"
    )
    fig.update_yaxes(
        title_text="持仓量",
        row=3, col=1,
        tickformat=",.0f"
    )
    fig.update_yaxes(
        title_text="成交量 / 持仓量",
        row=4, col=1,
        tickformat=",.0f"
    )
    
    # 格式化x轴
    fig.update_xaxes(
        tickformat="%m-%d %H:%M",
        tickangle=45
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
    
    # 应用筛选 - 基于单选结果
    if selected_stock and selected_date:
        df_filtered = df[
            (df['stock_code'] == selected_stock) &
            (df['expiry_date'] == selected_date)
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
    volume_level, latest_volume, max_volume = calculate_volume_level(selected_stock, selected_date)
    
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
            f"当前成交量水位: {volume_level:.2f} |  "
            f"当前成交量: {latest_volume:,.0f} | 最大成交量: {max_volume:,.0f}"
        )
        
        # 获取最新的stock_price和max_pain_price_volume
        if not df_filtered.empty:
            # 按update_time排序，获取最新的记录
            df_latest = df_filtered.sort_values('update_time', ascending=False).iloc[0]
            latest_stock_price = df_latest['stock_price']
            latest_max_pain_price_volume = df_latest['max_pain_price_volume']
            
            st.info(
                f"当前股票价格: ${latest_stock_price:.2f} |  "
                f"最大痛点价格(基于Volume): ${latest_max_pain_price_volume:.2f}"
            )
    else:
        st.info(f"📊 当前查看: **{selected_stock}** - **{selected_date.strftime('%Y-%m-%d')}**")
        
        # 即使volume_level为None，也尝试显示stock_price和max_pain_price_volume
        if not df_filtered.empty:
            df_latest = df_filtered.sort_values('update_time', ascending=False).iloc[0]
            latest_stock_price = df_latest['stock_price']
            latest_max_pain_price_volume = df_latest['max_pain_price_volume']
            
            st.info(
                f"当前股票价格: ${latest_stock_price:.2f} |  "
                f"最大痛点价格(基于Volume): ${latest_max_pain_price_volume:.2f}"
            )
    
    # 图表显示选项
    chart_type = st.selectbox(
        "选择图表类型",
        ["时间序列图表", "合并对比图表"],
        help="选择要显示的图表类型"
    )
    
    if chart_type == "时间序列图表":
        st.subheader("📊 最大痛点价格时间序列")
        create_time_series_chart(df_filtered)
    elif chart_type == "合并对比图表":
        st.subheader("📊 最大痛点价格对比")
        create_combined_chart(df_filtered)
    
    # 添加期权Volume柱状图
    st.markdown("---")
    st.subheader("📊 期权成交量分布图")
    create_options_volume_chart(selected_stock, selected_date)


def create_options_volume_chart(stock_code, expiry_date):
    """
    创建期权成交量柱状图
    
    Args:
        stock_code: 股票代码
        expiry_date: 到期日期
    """
    try:
        # 从options_data表获取数据
        options_records = OptionsData.get_options_data(
            stock_code=stock_code,
            expiry_date=expiry_date
        )
        
        if not options_records:
            st.warning(f"⚠️ 没有找到 {stock_code} 在 {expiry_date} 的期权数据")
            return
        
        # 获取最新的update_time
        update_times = list(set([record.update_time for record in options_records]))
        if not update_times:
            st.warning("⚠️ 没有找到有效的更新时间")
            return
        
        # 使用最新的update_time
        latest_update_time = max(update_times)
        
        # 筛选最新时间的数据
        latest_options = [r for r in options_records if r.update_time == latest_update_time]
        
        if not latest_options:
            st.warning("⚠️ 没有找到最新时间的期权数据")
            return
        
        # 转换为DataFrame
        data_list = []
        for record in latest_options:
            data_list.append({
                'strike_price': record.strike_price,
                'type': record.type,
                'volume': record.volume if record.volume else 0
            })
        
        df_options = pd.DataFrame(data_list)
        
        # 筛选strike_price在500到800之间的数据
        df_options = df_options[
            (df_options['strike_price'] >= 650) & 
            (df_options['strike_price'] <= 750)
        ].copy()
        
        if df_options.empty:
            st.warning(f"⚠️ 在行权价范围 500-800 内没有找到期权数据")
            return
        
        # 按strike_price排序
        df_options = df_options.sort_values('strike_price')
        
        # 分别获取call和put的数据
        df_call = df_options[df_options['type'] == 'call'].copy()
        df_put = df_options[df_options['type'] == 'put'].copy()
        
        # 创建图表
        fig = go.Figure()
        
        # 添加Call的柱状图（正数，在上方）
        if not df_call.empty:
            fig.add_trace(go.Bar(
                x=df_call['strike_price'],
                y=df_call['volume'],
                name='Call Volume',
                marker_color='#2ca02c',  # 绿色
                hovertemplate='<b>Call</b><br>' +
                            '行权价: $%{x:.0f}<br>' +
                            '成交量: %{y:,.0f}<br>' +
                            '<extra></extra>'
            ))
        
        # 添加Put的柱状图（负数，在下方）
        if not df_put.empty:
            fig.add_trace(go.Bar(
                x=df_put['strike_price'],
                y=-df_put['volume'],  # 使用负数使柱状图显示在下方
                name='Put Volume',
                marker_color='#d62728',  # 红色
                hovertemplate='<b>Put</b><br>' +
                            '行权价: $%{x:.0f}<br>' +
                            '成交量: %{text:,.0f}<br>' +
                            '<extra></extra>',
                text=df_put['volume'].values  # 使用绝对值显示在hover中
            ))
        
        # 更新布局
        fig.update_layout(
            title={
                'text': f'期权成交量分布 - {stock_code} ({expiry_date.strftime("%Y-%m-%d")})',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18}
            },
            xaxis_title="行权价 (Strike Price)",
            yaxis_title="成交量 (Volume)",
            barmode='group',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='closest'
        )
        
        # 更新y轴，使负数显示为绝对值
        fig.update_yaxes(
            tickformat=",d",
            title_text="成交量 (Volume) - 上方: Call, 下方: Put"
        )
        
        # 添加零线
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示数据信息
        st.caption(f"数据更新时间: {latest_update_time} | "
                  f"Call数量: {len(df_call)} | Put数量: {len(df_put)}")
        
    except Exception as e:
        st.error(f"❌ 创建期权成交量图表失败: {e}")
        import traceback
        st.error(f"详细错误信息: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
