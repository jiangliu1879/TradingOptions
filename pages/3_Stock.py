"""
股票数据分析页面

展示股票的历史价格、成交量和成交额数据，支持按股票代码筛选数据。
"""

import streamlit as st

# set_page_config 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="股票数据分析",
    page_icon="📊",
    layout="wide"
)

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime, timedelta, date

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.stock_data import StockData


def load_stock_data():
    """从数据库加载股票数据"""
    try:
        # 从数据库获取所有股票数据
        results = StockData.get_stock_data()
        
        if not results:
            st.warning("⚠️ 数据库中没有股票数据，请先运行数据收集脚本")
            return pd.DataFrame()
        
        # 转换为DataFrame
        data_list = []
        for result in results:
            data_list.append({
                'stock_code': result.stock_code,
                'timestamp': result.timestamp,
                'open': result.open,
                'high': result.high,
                'low': result.low,
                'close': result.close,
                'volume': result.volume,
                'turnover': result.turnover
            })
        
        df = pd.DataFrame(data_list)
        
        if df.empty:
            st.warning("⚠️ 数据库查询结果为空")
            return df
        
        # 转换timestamp为datetime类型
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 按照stock_code分类，并按timestamp从小到大排序
        df = df.sort_values(['stock_code', 'timestamp'])
        
        return df
        
    except Exception as e:
        st.error(f"❌ 从数据库加载数据失败: {e}")
        import traceback
        st.error(f"详细错误信息: {traceback.format_exc()}")
        return pd.DataFrame()


def create_stock_charts(df_filtered):
    """创建股票数据图表（close、volume、turnover）"""
    if df_filtered.empty:
        st.warning("⚠️ 没有数据可以显示")
        return
    
    # 确保数据按时间排序
    df_filtered = df_filtered.sort_values('timestamp')
    
    # 创建子图
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('收盘价 (Close)', '成交量 (Volume)', '成交额 (Turnover)'),
        vertical_spacing=0.08,
        shared_xaxes=True
    )
    
    # 定义颜色
    close_color = '#1f77b4'      # 蓝色 - 收盘价
    volume_color = '#ff7f0e'     # 橙色 - 成交量
    turnover_color = '#2ca02c'   # 绿色 - 成交额
    
    # 收盘价曲线
    fig.add_trace(
        go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered['close'],
            mode='lines+markers',
            name='收盘价',
            line=dict(color=close_color, width=2),
            marker=dict(size=4, color=close_color),
            hovertemplate='<b>收盘价</b><br>' +
                        '时间: %{x}<br>' +
                        '价格: $%{y:.2f}<br>' +
                        '<extra></extra>'
        ),
        row=1, col=1
    )
    
    # 成交量曲线
    fig.add_trace(
        go.Scatter(
            x=df_filtered['timestamp'],
            y=df_filtered['volume'],
            mode='lines+markers',
            name='成交量',
            line=dict(color=volume_color, width=2),
            marker=dict(size=4, color=volume_color),
            hovertemplate='<b>成交量</b><br>' +
                        '时间: %{x}<br>' +
                        '成交量: %{y:,.0f}<br>' +
                        '<extra></extra>'
        ),
        row=2, col=1
    )
    
    # 成交额曲线（处理可能为None的情况）
    turnover_data = df_filtered['turnover'].fillna(0)  # 将None替换为0以便绘制
    fig.add_trace(
        go.Scatter(
            x=df_filtered['timestamp'],
            y=turnover_data,
            mode='lines+markers',
            name='成交额',
            line=dict(color=turnover_color, width=2),
            marker=dict(size=4, color=turnover_color),
            hovertemplate='<b>成交额</b><br>' +
                        '时间: %{x}<br>' +
                        '成交额: $%{y:,.2f}<br>' +
                        '<extra></extra>'
        ),
        row=3, col=1
    )
    
    # 更新布局
    fig.update_layout(
        height=900,
        title={
            'text': f'股票数据时间序列 - {df_filtered.iloc[0]["stock_code"] if not df_filtered.empty else ""}',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 更新x轴
    fig.update_xaxes(
        title_text="时间",
        row=3, col=1
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
        title_text="成交额 ($)",
        row=3, col=1,
        tickformat=",.2f"
    )
    
    # 格式化x轴时间显示
    fig.update_xaxes(
        tickformat="%Y-%m-%d",
        tickangle=45
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    """主函数"""
    st.title("📊 股票数据分析")
    st.markdown("---")
    
    # 加载数据
    with st.spinner("🔄 正在从数据库加载股票数据..."):
        df = load_stock_data()
    
    if df.empty:
        st.stop()
    
    # 侧边栏筛选器
    st.sidebar.header("🔍 数据筛选")
    
    # 股票代码筛选 - 单选
    available_stocks = sorted(df['stock_code'].unique())
    selected_stock = st.sidebar.selectbox(
        "选择股票代码",
        options=available_stocks,
        index=0 if len(available_stocks) > 0 else None,
        help="选择一个股票代码进行查看"
    )
    
    # 应用股票代码筛选
    if selected_stock:
        df_by_stock = df[df['stock_code'] == selected_stock].copy()
        
        # 确保按时间排序
        df_by_stock = df_by_stock.sort_values('timestamp')
        
        # 时间筛选
        st.sidebar.markdown("---")
        st.sidebar.header("⏰ 时间筛选")
        
        # 获取数据的时间范围
        df_by_stock['date'] = df_by_stock['timestamp'].dt.date
        available_dates = df_by_stock['date'].tolist()
        min_date = min(available_dates) if available_dates else date.today()
        max_date = max(available_dates) if available_dates else date.today()
        
        # 时间筛选选项
        time_filter_option = st.sidebar.radio(
            "选择时间筛选方式:",
            ["📅 最近N周", "📆 最近N月", "🎯 自定义日期范围"],
            help="选择不同的时间筛选方式来查看数据"
        )
        
        st.sidebar.markdown("---")
        
        # 根据选择显示不同的界面并计算时间范围
        if "最近N周" in time_filter_option:
            weeks = st.sidebar.selectbox(
                "周数选择:", 
                range(1, 13), 
                index=0,
                help="选择要查看的周数"
            )
            
            # 计算开始日期
            end_date = max_date
            start_date = end_date - timedelta(weeks=weeks)
            
        elif "最近N月" in time_filter_option:
            months = st.sidebar.selectbox(
                "月数选择:", 
                range(1, 25), 
                index=0,
                help="选择要查看的月数"
            )
            
            # 计算开始日期（使用更精确的月份计算）
            end_date = max_date
            # 使用relativedelta会更准确，但为了简化，使用近似值
            start_date = end_date - timedelta(days=months*30)  # 近似计算，每月30天
            
        else:  # 自定义日期范围
            start_date = st.sidebar.date_input(
                "开始日期",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                help="选择数据查询的开始日期"
            )
            
            end_date = st.sidebar.date_input(
                "结束日期",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                help="选择数据查询的结束日期"
            )
        
        # 应用时间筛选
        df_filtered = df_by_stock[
            (df_by_stock['date'] >= start_date) & 
            (df_by_stock['date'] <= end_date)
        ].copy()
        
        # 确保按时间排序
        df_filtered = df_filtered.sort_values('timestamp')
        
        # 移除临时添加的date列
        if 'date' in df_filtered.columns:
            df_filtered = df_filtered.drop(columns=['date'])
    else:
        df_filtered = pd.DataFrame()
    
    # 检查是否选择了股票代码
    if not selected_stock:
        st.warning("⚠️ 请选择股票代码来查看数据")
        st.stop()
    
    # 检查是否有数据
    if df_filtered.empty:
        st.warning(f"⚠️ 没有找到 {selected_stock} 的数据")
        st.stop()
    
    # 显示当前选择的股票代码和统计信息
    st.info(f"📊 当前查看: **{selected_stock}** | 数据点数: {len(df_filtered)} | "
            f"时间范围: {df_filtered['timestamp'].min().strftime('%Y-%m-%d')} 至 "
            f"{df_filtered['timestamp'].max().strftime('%Y-%m-%d')}")
    
    # 计算并显示最新交易日的统计信息
    if len(df_filtered) >= 2:
        # 获取最新交易日和上一个交易日的数据
        latest_close = df_filtered['close'].iloc[-1]
        previous_close = df_filtered['close'].iloc[-2]
        
        # 计算close差值和涨跌幅度
        close_diff = latest_close - previous_close
        change_pct = (close_diff / previous_close) * 100 if previous_close != 0 else 0
        
        # 计算交易量水位（使用该股票的所有历史数据中的最大volume）
        df_all_stock = df[df['stock_code'] == selected_stock].copy()
        max_volume_all_time = df_all_stock['volume'].max() if not df_all_stock.empty else 1
        avg_volume_all_time = df_all_stock['volume'].mean() if not df_all_stock.empty else 1
        latest_volume = df_filtered['volume'].iloc[-1]
        volume_level_max = (latest_volume / max_volume_all_time) if max_volume_all_time > 0 else 0
        volume_level_avg = (latest_volume / avg_volume_all_time) if avg_volume_all_time > 0 else 0
        
        # 显示统计信息
        st.markdown("### 📊 最新交易日统计")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # 根据涨跌设置颜色
            delta_color = "normal"
            delta_prefix = ""
            if close_diff > 0:
                delta_color = "normal"
                delta_prefix = "+"
            elif close_diff < 0:
                delta_color = "inverse"
            
            st.metric(
                "价格变化",
                f"${latest_close:.2f}",
                delta=f"{delta_prefix}${close_diff:.2f}",
                delta_color=delta_color
            )
        
        with col2:
            st.metric(
                "涨跌幅度",
                f"{change_pct:+.2f}%",
                delta=f"{change_pct:+.2f}%",
                delta_color=delta_color
            )
        
        with col3:
            # 根据水位设置颜色和图标（最大volume）
            if volume_level_max >= 1.0:
                volume_level_text_max = f"{volume_level_max:.2f} (🔥)"
            elif volume_level_max >= 0.8:
                volume_level_text_max = f"{volume_level_max:.2f} (⚡)"
            elif volume_level_max >= 0.5:
                volume_level_text_max = f"{volume_level_max:.2f} (📊)"
            else:
                volume_level_text_max = f"{volume_level_max:.2f} (📉)"
            
            st.metric(
                "交易量水位(最大)",
                f"{volume_level_max:.2f}",
                help=f"最新交易日成交量 / 历史最大成交量 = {latest_volume:,.0f} / {max_volume_all_time:,.0f}"
            )
            st.caption(volume_level_text_max)
        
        with col4:
            # 根据水位设置颜色和图标（平均volume）
            if volume_level_avg >= 2.0:
                volume_level_text_avg = f"{volume_level_avg:.2f} (🔥)"
            elif volume_level_avg >= 1.5:
                volume_level_text_avg = f"{volume_level_avg:.2f} (⚡)"
            elif volume_level_avg >= 1.0:
                volume_level_text_avg = f"{volume_level_avg:.2f} (📊)"
            else:
                volume_level_text_avg = f"{volume_level_avg:.2f} (📉)"
            
            st.metric(
                "交易量水位(平均)",
                f"{volume_level_avg:.2f}",
                help=f"最新交易日成交量 / 历史平均成交量 = {latest_volume:,.0f} / {avg_volume_all_time:,.0f}"
            )
            st.caption(volume_level_text_avg)
        
        st.markdown("---")
    elif len(df_filtered) == 1:
        st.info("ℹ️ 仅有一条数据，无法计算变化量")
        # 只显示交易量水位
        df_all_stock = df[df['stock_code'] == selected_stock].copy()
        max_volume_all_time = df_all_stock['volume'].max() if not df_all_stock.empty else 1
        avg_volume_all_time = df_all_stock['volume'].mean() if not df_all_stock.empty else 1
        latest_volume = df_filtered['volume'].iloc[-1]
        volume_level_max = (latest_volume / max_volume_all_time) if max_volume_all_time > 0 else 0
        volume_level_avg = (latest_volume / avg_volume_all_time) if avg_volume_all_time > 0 else 0
        
        st.markdown("### 📊 最新交易日统计")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("价格", f"${df_filtered['close'].iloc[-1]:.2f}")
        
        with col2:
            st.metric("涨跌幅度", "N/A", help="仅有一条数据，无法计算变化")
        
        with col3:
            st.metric(
                "交易量水位(最大)",
                f"{volume_level_max:.2f}",
                help=f"最新交易日成交量 / 历史最大成交量 = {latest_volume:,.0f} / {max_volume_all_time:,.0f}"
            )
        
        with col4:
            st.metric(
                "交易量水位(平均)",
                f"{volume_level_avg:.2f}",
                help=f"最新交易日成交量 / 历史平均成交量 = {latest_volume:,.0f} / {avg_volume_all_time:,.0f}"
            )
        
        st.markdown("---")
    
    # 显示图表
    st.subheader("📈 股票数据图表")
    create_stock_charts(df_filtered)
    
    # 显示数据摘要
    with st.expander("📋 数据摘要"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("最新收盘价", f"${df_filtered['close'].iloc[-1]:.2f}")
        
        with col2:
            st.metric("平均成交量", f"{df_filtered['volume'].mean():,.0f}")
        
        with col3:
            turnover_mean = df_filtered['turnover'].mean()
            if pd.notna(turnover_mean):
                st.metric("平均成交额", f"${turnover_mean:,.2f}")
            else:
                st.metric("平均成交额", "N/A")
        
        with col4:
            st.metric("最高价", f"${df_filtered['high'].max():.2f}")
        
        # 显示数据表格
        st.dataframe(
            df_filtered[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']],
            use_container_width=True,
            height=300
        )


if __name__ == "__main__":
    main()

