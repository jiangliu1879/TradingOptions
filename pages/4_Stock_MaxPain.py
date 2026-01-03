"""
股票最大痛点价格分析页面

展示期权最大痛点价格的时间序列图表，支持按股票代码和到期日期筛选数据。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime, date

# set_page_config 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="股票最大痛点价格分析",
    page_icon="📈",
    layout="wide"
)

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.max_pain_result2 import MaxPainResult2


def load_max_pain_data():
    """从数据库加载最大痛点数据"""
    try:
        # 从数据库获取所有最大痛点结果
        results = MaxPainResult2.get_max_pain_results2()
        
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


def create_price_chart(df_filtered):
    """
    创建价格相关图表（第一组）
    包含：max_pain_price_volume、max_pain_price_open_interest、stock_price
    """
    if df_filtered.empty:
        st.warning("⚠️ 没有数据可以显示")
        return
    
    # 确保数据按时间排序
    df_filtered = df_filtered.sort_values('update_time').reset_index(drop=True)
    
    # 创建图表
    fig = go.Figure()
    
    # 定义颜色
    volume_color = '#1f77b4'      # 蓝色 - Volume最大痛点价格
    oi_color = '#ff7f0e'          # 橙色 - Open Interest最大痛点价格
    stock_color = '#2ca02c'       # 绿色 - 股票价格
    
    # max_pain_price_volume
    fig.add_trace(
        go.Scatter(
            x=df_filtered['update_time'],
            y=df_filtered['max_pain_price_volume'],
            mode='lines+markers',
            name='最大痛点价格 (Volume)',
            line=dict(color=volume_color, width=2),
            marker=dict(size=6, color=volume_color),
            hovertemplate='<b>最大痛点价格 (Volume)</b><br>' +
                        '时间: %{x}<br>' +
                        '价格: $%{y:.2f}<br>' +
                        '<extra></extra>'
        )
    )
    
    # max_pain_price_open_interest
    fig.add_trace(
        go.Scatter(
            x=df_filtered['update_time'],
            y=df_filtered['max_pain_price_open_interest'],
            mode='lines+markers',
            name='最大痛点价格 (Open Interest)',
            line=dict(color=oi_color, width=2),
            marker=dict(size=6, color=oi_color),
            hovertemplate='<b>最大痛点价格 (Open Interest)</b><br>' +
                        '时间: %{x}<br>' +
                        '价格: $%{y:.2f}<br>' +
                        '<extra></extra>'
        )
    )
    
    # stock_price
    fig.add_trace(
        go.Scatter(
            x=df_filtered['update_time'],
            y=df_filtered['stock_price'],
            mode='lines+markers',
            name='股票价格',
            line=dict(color=stock_color, width=2),
            marker=dict(size=6, color=stock_color),
            hovertemplate='<b>股票价格</b><br>' +
                        '时间: %{x}<br>' +
                        '价格: $%{y:.2f}<br>' +
                        '<extra></extra>'
        )
    )
    
    # 更新布局
    fig.update_layout(
        height=500,
        title={
            'text': '最大痛点价格与股票价格',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis_title="更新时间",
        yaxis_title="价格 ($)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    # 格式化x轴时间显示
    fig.update_xaxes(
        tickformat="%m-%d %H:%M",
        tickangle=45
    )
    
    st.plotly_chart(fig, use_container_width=True)


def create_volume_oi_chart(df_filtered):
    """
    创建成交量和持仓量图表（第二组）
    包含：sum_volume、sum_open_interest
    """
    if df_filtered.empty:
        st.warning("⚠️ 没有数据可以显示")
        return
    
    # 确保数据按时间排序
    df_filtered = df_filtered.sort_values('update_time').reset_index(drop=True)
    
    # 创建图表
    fig = go.Figure()
    
    # 定义颜色
    volume_color = '#1f77b4'      # 蓝色 - 成交量
    oi_color = '#ff7f0e'          # 橙色 - 持仓量
    
    # sum_volume
    fig.add_trace(
        go.Scatter(
            x=df_filtered['update_time'],
            y=df_filtered['sum_volume'],
            mode='lines+markers',
            name='成交量 (Sum Volume)',
            line=dict(color=volume_color, width=2),
            marker=dict(size=6, color=volume_color),
            hovertemplate='<b>成交量</b><br>' +
                        '时间: %{x}<br>' +
                        '成交量: %{y:,.0f}<br>' +
                        '<extra></extra>'
        )
    )
    
    # sum_open_interest
    fig.add_trace(
        go.Scatter(
            x=df_filtered['update_time'],
            y=df_filtered['sum_open_interest'],
            mode='lines+markers',
            name='持仓量 (Sum Open Interest)',
            line=dict(color=oi_color, width=2, dash='dash'),
            marker=dict(size=6, color=oi_color),
            hovertemplate='<b>持仓量</b><br>' +
                        '时间: %{x}<br>' +
                        '持仓量: %{y:,.0f}<br>' +
                        '<extra></extra>'
        )
    )
    
    # 更新布局
    fig.update_layout(
        height=500,
        title={
            'text': '成交量和持仓量',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis_title="更新时间",
        yaxis_title="数量",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    # 格式化y轴
    fig.update_yaxes(
        tickformat=",.0f"
    )
    
    # 格式化x轴时间显示
    fig.update_xaxes(
        tickformat="%m-%d %H:%M",
        tickangle=45
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    """主函数"""
    st.title("📈 股票最大痛点价格分析")
    st.markdown("---")
    
    # 加载数据
    with st.spinner("🔄 正在从数据库加载最大痛点数据..."):
        df = load_max_pain_data()
    
    if df.empty:
        st.stop()
    
    # 侧边栏筛选器
    st.sidebar.header("🔍 数据筛选")
    
    # 股票代码筛选 - 下拉框
    available_stocks = sorted(df['stock_code'].unique())
    
    if not available_stocks:
        st.warning("⚠️ 没有可用的股票数据")
        st.stop()
    
    selected_stock = st.sidebar.selectbox(
        "选择股票代码",
        options=available_stocks,
        index=0 if len(available_stocks) > 0 else None,
        help="选择一个股票代码进行查看"
    )
    
    # 根据选择的股票代码筛选可用的到期日期，并按时间倒序排列（最近的在前面）
    if selected_stock:
        available_dates_for_stock = sorted(
            df[df['stock_code'] == selected_stock]['expiry_date'].unique(), 
            reverse=True
        )
    else:
        available_dates_for_stock = []
    
    # 到期日期筛选 - 下拉框
    selected_date = st.sidebar.selectbox(
        "选择到期日期",
        options=available_dates_for_stock,
        index=0 if len(available_dates_for_stock) > 0 else None,
        format_func=lambda x: x.strftime('%Y-%m-%d') if x else '无数据',
        help="选择一个到期日期进行查看"
    )
    
    # 应用筛选
    if selected_stock and selected_date:
        df_filtered = df[
            (df['stock_code'] == selected_stock) &
            (df['expiry_date'] == selected_date)
        ].copy()
    else:
        df_filtered = pd.DataFrame()
    
    # 检查是否选择了股票和到期日期
    if not selected_stock or not selected_date:
        st.warning("⚠️ 请选择股票代码和到期日期来查看数据")
        st.info("💡 提示：使用侧边栏的下拉框选择股票代码和到期日期")
        st.stop()
    
    # 检查是否有数据
    if df_filtered.empty:
        st.warning(f"⚠️ 没有找到 {selected_stock} 在 {selected_date.strftime('%Y-%m-%d')} 的数据")
        st.stop()
    
    # 显示当前选择的信息
    st.info(f"📊 当前查看: **{selected_stock}** - **{selected_date.strftime('%Y-%m-%d')}** | "
            f"数据点数: {len(df_filtered)}")
    
    # 显示最新的数据摘要
    if not df_filtered.empty:
        df_latest = df_filtered.sort_values('update_time', ascending=False).iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("最新股票价格", f"${df_latest['stock_price']:.2f}")
        
        with col2:
            st.metric("最大痛点价格 (Volume)", f"${df_latest['max_pain_price_volume']:.2f}")
        
        with col3:
            st.metric("最大痛点价格 (OI)", f"${df_latest['max_pain_price_open_interest']:.2f}")
        
        with col4:
            st.metric("成交量", f"{df_latest['sum_volume']:,.0f}")
        
        st.markdown("---")
    
    # 第一组图表：价格相关
    st.subheader("📊 最大痛点价格与股票价格")
    create_price_chart(df_filtered)
    
    # 第二组图表：成交量和持仓量
    st.subheader("📊 成交量和持仓量")
    create_volume_oi_chart(df_filtered)
    
    # 显示数据表格
    with st.expander("📋 详细数据"):
        display_df = df_filtered[[
            'update_time',
            'stock_price',
            'max_pain_price_volume',
            'max_pain_price_open_interest',
            'sum_volume',
            'sum_open_interest'
        ]].copy()
        
        display_df = display_df.sort_values('update_time', ascending=False)
        display_df['update_time'] = pd.to_datetime(display_df['update_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df.columns = [
            '更新时间',
            '股票价格',
            '最大痛点价格 (Volume)',
            '最大痛点价格 (OI)',
            '成交量',
            '持仓量'
        ]
        
        # 格式化数值
        display_df['股票价格'] = display_df['股票价格'].apply(lambda x: f'${x:.2f}')
        display_df['最大痛点价格 (Volume)'] = display_df['最大痛点价格 (Volume)'].apply(lambda x: f'${x:.2f}')
        display_df['最大痛点价格 (OI)'] = display_df['最大痛点价格 (OI)'].apply(lambda x: f'${x:.2f}')
        display_df['成交量'] = display_df['成交量'].apply(lambda x: f'{x:,.0f}')
        display_df['持仓量'] = display_df['持仓量'].apply(lambda x: f'{x:,.0f}')
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

