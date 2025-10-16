import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import numpy as np
import os
import sys

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.stock_data import StockData

# 设置页面标题
st.set_page_config(page_title="SPY 涨跌幅分析", layout="wide")
st.title("📈 SPY 涨跌幅分析")

# 从数据库读取SPY数据
@st.cache_data
def load_data():
    try:
        # 从数据库获取SPY数据
        spy_data = StockData.get_stock_data(stock_code='SPY.US')
        
        if not spy_data:
            st.error("数据库中未找到SPY数据")
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame([record.to_dict() for record in spy_data])
        
        # 检查DataFrame是否为空
        if df.empty:
            st.error("SPY数据为空")
            return None
        
        # 将timestamp列转换为datetime格式，使用 format='mixed' 处理不同格式
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        # 按时间排序
        df = df.sort_values('timestamp')
        
        # 计算涨跌幅
        df['price_change'] = df['close'].diff()  # 价格变化
        df['price_change_pct'] = df['close'].pct_change() * 100  # 百分比变化
        
        # 计算涨跌方向
        df['direction'] = np.where(df['price_change'] > 0, '上涨', 
                                 np.where(df['price_change'] < 0, '下跌', '平盘'))
        
        # 计算累计涨跌幅
        df['cumulative_return'] = (df['close'] / df['close'].iloc[0] - 1) * 100
        
        return df
    except Exception as e:
        st.error(f"从数据库读取数据时出错: {e}")
        import traceback
        st.error(f"详细错误信息: {traceback.format_exc()}")
        return None

# 加载数据
with st.spinner("正在加载SPY数据..."):
    df = load_data()

if df is not None:
    # 侧边栏时间筛选功能
    with st.sidebar:
        st.header("📊 数据筛选")
        
        # 添加日期列
        df['date'] = df['timestamp'].dt.date
        available_dates = df['date'].tolist()
        min_date = min(available_dates)
        max_date = max(available_dates)
        
        # 时间筛选选项
        time_filter_option = st.radio(
            "📊 选择时间筛选方式:",
            ["📅 最近N周", "📆 最近N月", "🎯 自定义日期范围"],
            help="选择不同的时间筛选方式来查看数据"
        )
        
        st.markdown("---")
        
        # 根据选择显示不同的界面
        if "最近N周" in time_filter_option:
            weeks = st.selectbox(
                "📊 周数选择:", 
                range(1, 5), 
                index=0,
                help="选择要查看的周数"
            )
            
            # 计算开始日期
            end_date = max_date
            start_date = end_date - timedelta(weeks=weeks)
            
        elif "最近N月" in time_filter_option:
            months = st.selectbox(
                "📊 月数选择:", 
                range(1, 13), 
                index=0,
                help="选择要查看的月数"
            )
            
            # 计算开始日期
            end_date = max_date
            start_date = end_date - timedelta(days=months*30)  # 近似计算，每月30天
            
        else: 
            start_date = st.date_input(
                "📅 开始日期",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                help="选择数据查询的开始日期"
            )
            
            end_date = st.date_input(
                "📅 结束日期",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                help="选择数据查询的结束日期"
            )
            
            # 计算选择的日期范围天数
            date_range_days = (end_date - start_date).days
            st.info(f"📊 选择的日期范围: {date_range_days} 天")
        
        # 过滤数据
        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
        
    # 使用过滤后的数据
    df = filtered_df
    
    # 检查是否有数据
    if df.empty:
        st.warning("⚠️ 选择的时间范围内没有数据，请选择其他时间范围")
        st.stop()
    
    # 显示数据基本信息
    st.subheader("📊 数据概览")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总记录数", len(df))
    with col2:
        st.metric("数据起始日期", df['timestamp'].min().strftime('%Y-%m-%d'))
    with col3:
        st.metric("数据结束日期", df['timestamp'].max().strftime('%Y-%m-%d'))
    with col4:
        st.metric("最新收盘价", f"${df['close'].iloc[-1]:.2f}")
    
    # 涨跌幅统计概览
    st.subheader("📈 涨跌幅统计概览")
    col1, col2, col3, col4 = st.columns(4)
    
    # 计算基本统计
    total_days = len(df) - 1  # 减去第一天（没有前一天数据）
    up_days = len(df[df['direction'] == '上涨'])
    down_days = len(df[df['direction'] == '下跌'])
    flat_days = len(df[df['direction'] == '平盘'])
    
    with col1:
        st.metric("上涨天数", up_days, f"{up_days/total_days*100:.1f}%")
    with col2:
        st.metric("下跌天数", down_days, f"{down_days/total_days*100:.1f}%")
    with col3:
        st.metric("平盘天数", flat_days, f"{flat_days/total_days*100:.1f}%")
    with col4:
        st.metric("总涨跌幅", f"{df['cumulative_return'].iloc[-1]:.2f}%")
    
    # 涨跌幅分布图
    st.subheader("📊 日涨跌幅分布")
    
    # 创建涨跌幅分布直方图
    fig_dist = px.histogram(
        df.dropna(subset=['price_change_pct']),
        x='price_change_pct',
        nbins=50,
        title="日涨跌幅分布直方图",
        labels={'price_change_pct': '日涨跌幅 (%)', 'count': '频次'},
        color_discrete_sequence=['#1f77b4']
    )
    
    fig_dist.add_vline(x=0, line_dash="dash", line_color="red", 
                      annotation_text="0%", annotation_position="top right")
    
    fig_dist.update_layout(
        xaxis_title="日涨跌幅 (%)",
        yaxis_title="频次",
        height=400
    )
    
    st.plotly_chart(fig_dist, use_container_width=True)
    
    # 涨跌幅统计详情
    st.subheader("📋 涨跌幅统计详情")
    
    # 计算详细统计信息
    price_changes = df['price_change_pct'].dropna()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**基本统计**")
        st.write(f"平均日涨跌幅: {price_changes.mean():.3f}%")
        st.write(f"中位数日涨跌幅: {price_changes.median():.3f}%")
        st.write(f"标准差: {price_changes.std():.3f}%")
        st.write(f"最大单日涨幅: {price_changes.max():.3f}%")
        st.write(f"最大单日跌幅: {price_changes.min():.3f}%")
        st.write(f"波动率(年化): {price_changes.std() * np.sqrt(252):.2f}%")
    
    with col2:
        st.write("**分位数区间统计（以0为中心）**")
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        price_changes_sorted = price_changes.sort_values()
        n = len(price_changes_sorted)
        for p in percentiles:
            count = int(n * (p / 100) / 2)
            if count == 0:
                st.write(f"{p}分位区间：样本数过少，无法统计")
                continue
            # 以0为中心，向左、右各取count个
            left = price_changes_sorted[price_changes_sorted < 0].tail(count)
            right = price_changes_sorted[price_changes_sorted > 0].head(count)
            if len(left) == 0 or len(right) == 0:
                st.write(f"{p}分位区间：样本数过少，无法统计")
                continue
            min_val = left.min()
            max_val = right.max()
            st.write(f"{p}分位区间： {min_val:.3f}% ~ {max_val:.3f}%")

    # 累计收益率走势图
    st.subheader("📈 累计收益率走势")
    
    fig_cumulative = go.Figure()
    
    fig_cumulative.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['cumulative_return'],
        mode='lines',
        name='累计收益率',
        line=dict(color='#2ca02c', width=2),
        hovertemplate='<b>日期:</b> %{x}<br>' +
                     '<b>累计收益率:</b> %{y:.2f}%<br>' +
                     '<extra></extra>'
    ))
    
    fig_cumulative.update_layout(
        title="SPY 累计收益率走势",
        xaxis_title="日期",
        yaxis_title="累计收益率 (%)",
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    st.plotly_chart(fig_cumulative, use_container_width=True)
    
    # 最大涨跌幅记录
    st.subheader("🏆 最大涨跌幅记录")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**最大单日涨幅**")
        max_gain_idx = df['price_change_pct'].idxmax()
        max_gain_row = df.loc[max_gain_idx]
        st.write(f"日期: {max_gain_row['timestamp'].strftime('%Y-%m-%d')}")
        st.write(f"涨幅: {max_gain_row['price_change_pct']:.3f}%")
        st.write(f"收盘价: ${max_gain_row['close']:.2f}")
        st.write(f"成交量: {max_gain_row['volume']:,.0f}")
    
    with col2:
        st.write("**最大单日跌幅**")
        max_loss_idx = df['price_change_pct'].idxmin()
        max_loss_row = df.loc[max_loss_idx]
        st.write(f"日期: {max_loss_row['timestamp'].strftime('%Y-%m-%d')}")
        st.write(f"跌幅: {max_loss_row['price_change_pct']:.3f}%")
        st.write(f"收盘价: ${max_loss_row['close']:.2f}")
        st.write(f"成交量: {max_loss_row['volume']:,.0f}")
    
    # 最近30天涨跌幅
    st.subheader("📅 最近30天涨跌幅")
    
    recent_data = df.tail(30).copy()
    recent_data['date_str'] = recent_data['timestamp'].dt.strftime('%m-%d')
    
    fig_recent = go.Figure()
    
    colors = ['red' if x < 0 else 'green' for x in recent_data['price_change_pct']]
    
    fig_recent.add_trace(go.Bar(
        x=recent_data['date_str'],
        y=recent_data['price_change_pct'],
        marker_color=colors,
        name='日涨跌幅',
        hovertemplate='<b>日期:</b> %{x}<br>' +
                     '<b>涨跌幅:</b> %{y:.2f}%<br>' +
                     '<extra></extra>'
    ))
    
    fig_recent.update_layout(
        title="最近30天日涨跌幅",
        xaxis_title="日期",
        yaxis_title="涨跌幅 (%)",
        template='plotly_white',
        height=400
    )
    
    st.plotly_chart(fig_recent, use_container_width=True)
    
    # 数据表格
    st.subheader("📋 详细数据")
    
    # 显示过滤后的数据
    display_columns = ['timestamp', 'close', 'price_change', 'price_change_pct', 'direction', 'cumulative_return']
    
    # 创建显示用的数据副本，将timestamp格式化为只显示日期
    display_df = df[display_columns].copy()
    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d')
    
    st.dataframe(
        display_df.round(3),
        use_container_width=True
    )

else:
    st.info("请先运行 longport_test.py 来获取SPY历史数据")
