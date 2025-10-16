import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import os
import sys

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.stock_data import StockData

def get_available_stocks():
    """获取数据库中可用的股票"""
    try:
        stock_codes = StockData.get_stock_codes()
        # 转换为简化的股票代码格式
        available_stocks = {}
        for code in stock_codes:
            # 将 'NVDA.US' 转换为 'NVDA'
            simple_code = code.replace('.US', '')
            available_stocks[simple_code] = code
        return available_stocks
    except Exception as e:
        st.error(f"获取股票列表时出错: {e}")
        return {}

def load_stock_data(stock_code, db_stock_code):
    """从数据库加载指定股票的历史数据"""
    try:
        # 从数据库获取股票数据
        stock_data = StockData.get_stock_data(stock_code=db_stock_code)
        
        if not stock_data:
            st.error(f"数据库中未找到 {stock_code} 的数据")
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame([record.to_dict() for record in stock_data])
        
        # 转换时间戳列为datetime类型
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # 添加日期列（不含时间）
        df['date'] = df['timestamp'].dt.date
        
        return df
    except Exception as e:
        st.error(f"从数据库读取 {stock_code} 数据时出错: {e}")
        return None

def main():
    st.set_page_config(page_title="股票分析平台", page_icon="📈", layout="wide")
    
    st.title("📈 股票分析平台")
    st.markdown("---")
    
    # 获取可用股票
    available_stocks = get_available_stocks()
    
    if not available_stocks:
        st.error("❌ 数据库中未找到任何股票数据")
        st.info("请确保数据库中存在股票数据，或先运行数据导入脚本")
        return
    
    # 侧边栏股票选择和时间筛选功能
    with st.sidebar:
        # 股票选择
        selected_stock = st.selectbox(
            "📊 选择股票标的:",
            options=list(available_stocks.keys()),
            help="选择要分析的股票"
        )
        
        st.markdown("---")
        
        # 获取所有可用日期
        db_stock_code = available_stocks[selected_stock]
        df = load_stock_data(selected_stock, db_stock_code)
        
        if df is None:
            return
        
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
            st.metric("选择天数", f"{date_range_days}天")
    
    # 获取最新交易日数据
    latest_data = df.iloc[-1]  # 获取最后一行数据（最新的交易日）
    
    # 显示当前分析的股票
    st.info(f"📈 当前分析标的：**{selected_stock}**")
    
    # 数据概览 - 展示最新交易日数据
    st.subheader(f"📅 最新交易日：{str(latest_data['date'])}")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("开盘价", f"${latest_data['open']:.2f}")
    with col2:
        st.metric("收盘价", f"${latest_data['close']:.2f}")
    with col3:
        st.metric("最高价", f"${latest_data['high']:.2f}")
    with col4:
        st.metric("最低价", f"${latest_data['low']:.2f}")
    with col5:
        st.metric("成交量", f"{latest_data['volume']:,.0f}")
    with col6:
        st.metric("成交额", f"${latest_data['turnover']/10000:.1f}万")
    
    # 确保开始日期不晚于结束日期
    if start_date > end_date:
        st.error("开始日期不能晚于结束日期")
        start_date = end_date
    
    # 筛选数据
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    if len(filtered_df) == 0:
        st.error("❌ 选择的日期范围内没有数据，请调整时间范围")
        st.info("💡 提示：数据范围为 {} 至 {}".format(min_date, max_date))
        return
    
    st.markdown("---")
    
    # 显示选择日期范围的数据概览 - 使用更好的视觉设计
    with st.container():
        # 动态标题
        if "最近N周" in time_filter_option:
            st.subheader(f"📊 最近 {weeks} 周数据概览")
        elif "最近N月" in time_filter_option:
            st.subheader(f"📊 最近 {months} 个月数据概览")
        else:
            st.subheader(f"📊 自定义时间段数据概览")
        
        # 使用卡片式布局显示关键指标
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "📈 数据点数量", 
                len(filtered_df),
                help="选定时间范围内的交易日数量"
            )
        
        with col2:
            high_price = filtered_df['high'].max()
            st.metric(
                "📈 期间最高价", 
                f"${high_price:.2f}",
                help="选定时间范围内的最高价格"
            )
        
        with col3:
            low_price = filtered_df['low'].min()
            st.metric(
                "📉 期间最低价", 
                f"${low_price:.2f}",
                help="选定时间范围内的最低价格"
            )
        
        with col4:
            price_change = filtered_df['close'].iloc[-1] - filtered_df['open'].iloc[0]
            price_change_pct = (price_change / filtered_df['open'].iloc[0]) * 100
            delta_color = "normal" if price_change >= 0 else "inverse"
            st.metric(
                "📊 期间涨跌幅", 
                f"{price_change_pct:.2f}%",
                delta=f"${price_change:.2f}",
                delta_color=delta_color,
                help="从开始到结束的总体涨跌幅"
            )
        
        with col5:
            avg_volume = filtered_df['volume'].mean()
            st.metric(
                "📊 平均成交量", 
                f"{avg_volume:,.0f}",
                help="选定时间范围内的平均成交量"
            )
        
        # 添加时间范围信息
        st.caption(f"📅 时间范围：{start_date} 至 {end_date} ({len(filtered_df)} 个交易日)")
    
    st.markdown("---")
    
    # 股价波动范围与成交量对比图
    st.subheader(f"📊 股价波动范围与成交量对比")
    
    # 计算每日股价波动范围，区分涨跌
    filtered_df['price_range'] = filtered_df['high'] - filtered_df['low']
    filtered_df['price_range_pct'] = (filtered_df['price_range'] / filtered_df['open']) * 100
    
    # 计算涨跌情况
    filtered_df['daily_change'] = filtered_df['close'] - filtered_df['open']
    filtered_df['is_positive'] = filtered_df['daily_change'] >= 0
    
    # 创建双轴图表
    fig_comparison = go.Figure()
    
    # 分别添加上涨和下跌的柱状图
    # 上涨日（深绿色）
    up_data = filtered_df[filtered_df['is_positive']]
    if not up_data.empty:
        fig_comparison.add_trace(go.Bar(
            x=up_data['date'],
            y=up_data['price_range'],
            name='上涨日波动范围',
            yaxis='y',
            marker=dict(color='rgba(0, 128, 0, 0.8)', line=dict(color='rgba(0, 100, 0, 1)', width=1)),
            hovertemplate='<b>%{x}</b><br>上涨日<br>波动范围: $%{y:.2f}<br>涨跌幅: $%{customdata:.2f}<extra></extra>',
            customdata=up_data['daily_change']
        ))
    
    # 下跌日（深红色）
    down_data = filtered_df[~filtered_df['is_positive']]
    if not down_data.empty:
        fig_comparison.add_trace(go.Bar(
            x=down_data['date'],
            y=down_data['price_range'],
            name='下跌日波动范围',
            yaxis='y',
            marker=dict(color='rgba(220, 20, 60, 0.8)', line=dict(color='rgba(180, 20, 60, 1)', width=1)),
            hovertemplate='<b>%{x}</b><br>下跌日<br>波动范围: $%{y:.2f}<br>涨跌幅: $%{customdata:.2f}<extra></extra>',
            customdata=down_data['daily_change']
        ))
    
    # 添加成交量（折线图）- 使用深蓝色
    fig_comparison.add_trace(go.Scatter(
        x=filtered_df['date'],
        y=filtered_df['volume'],
        mode='lines+markers',
        name='成交量',
        yaxis='y2',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=5, color='#1f77b4', line=dict(color='#ffffff', width=1)),
        hovertemplate='<b>%{x}</b><br>成交量: %{y:,.0f}<extra></extra>'
    ))
    
    # 设置双Y轴布局
    fig_comparison.update_layout(
        title=f"{selected_stock} 股价波动范围与成交量对比分析",
        xaxis_title="日期",
        yaxis=dict(
            title="股价波动范围 ($)",
            side="left",
            showgrid=True
        ),
        yaxis2=dict(
            title="成交量",
            side="right",
            overlaying="y",
            showgrid=False
        ),
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig_comparison, use_container_width=True)
    
    # 添加分析说明
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **📈 股价波动范围分析：**
        - 🟢 深绿色：上涨日波动范围（收盘价 > 开盘价）
        - 🔴 深红色：下跌日波动范围（收盘价 < 开盘价）
        - 显示每日最高价与最低价的差值
        - 反映单日价格波动的激烈程度
        """)
    
    with col2:
        st.info("""
        **📊 成交量分析：**
        - 🔵 深蓝色折线：显示每日交易量的大小
        - 反映市场参与度和流动性
        - 高成交量通常伴随大的价格波动
        - 可以对比涨跌日与成交量的关系
        """)

    st.markdown("---")

     # K线图
    st.subheader("🕯️ K线图")
    
    fig_candlestick = go.Figure(data=go.Candlestick(
        x=filtered_df['date'],
        open=filtered_df['open'],
        high=filtered_df['high'],
        low=filtered_df['low'],
        close=filtered_df['close'],
        name=selected_stock
    ))
    
    # 根据筛选类型设置图表标题
    if time_filter_option == "最近N周":
        chart_title = f"{selected_stock} K线图 - 最近 {weeks} 周 ({start_date} 至 {end_date})"
    elif time_filter_option == "最近N月":
        chart_title = f"{selected_stock} K线图 - 最近 {months} 个月 ({start_date} 至 {end_date})"
    else:
        chart_title = f"{selected_stock} K线图 ({start_date} 至 {end_date})"
    
    fig_candlestick.update_layout(
        title=chart_title,
        xaxis_title="日期",
        yaxis_title="价格 ($)",
        height=500,
        xaxis_rangeslider_visible=False  # 隐藏底部范围滑块，因为我们有自己的日期选择器
    )
    
    st.plotly_chart(fig_candlestick, use_container_width=True)
    
    st.markdown("---")
    
    # 显示筛选后的数据表格
    st.subheader("📋 数据表格")
    
    display_df = filtered_df[['date', 'open', 'close', 'high', 'low', 'price_range', 'daily_change', 'volume']].copy()
    display_df = display_df.round(2)
    
    # 添加涨跌标识列
    display_df['涨跌'] = display_df['daily_change'].apply(lambda x: '📈' if x >= 0 else '📉')
    
    st.dataframe(display_df, use_container_width=True)
    
    # 下载按钮
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="下载筛选后的数据",
        data=csv,
        file_name=f"{selected_stock.lower()}_data_{start_date}_to_{end_date}.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
