import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob

def load_options_data():
    """加载期权数据"""
    try:
        # 读取data/options目录下的所有期权数据文件
        options_dir = "data/options"
        if not os.path.exists(options_dir):
            st.error(f"数据目录不存在: {options_dir}")
            return None
        
        # 获取所有CSV文件
        csv_files = glob.glob(os.path.join(options_dir, "*.csv"))
        if not csv_files:
            st.error(f"在 {options_dir} 目录下没有找到CSV文件")
            return None
        
        # 读取并合并所有CSV文件
        dataframes = []
        for file_path in csv_files:
            try:
                df_temp = pd.read_csv(file_path)
                dataframes.append(df_temp)
            except Exception as e:
                st.warning(f"读取文件 {file_path} 失败: {e}")
                continue
        
        if not dataframes:
            st.error("没有成功读取任何数据文件")
            return None
        
        df = pd.concat(dataframes, ignore_index=True)
        
        # 转换日期格式
        df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        df['update_time'] = pd.to_datetime(df['update_time'])
        
        return df
    except Exception as e:
        st.error(f"加载数据文件失败: {e}")
        return None


def create_combined_chart(df, metric, title, y_label):
    """创建call和put的对比图表，方向相反"""
    if df is None or df.empty:
        return None
    
    # 分离call和put数据
    calls_df = df[df['type'] == 'call'].copy()
    puts_df = df[df['type'] == 'put'].copy()
    
    # 过滤掉数据为0的记录
    calls_filtered = calls_df[calls_df[metric] > 0].copy()
    puts_filtered = puts_df[puts_df[metric] > 0].copy()
    
    if calls_filtered.empty and puts_filtered.empty:
        st.warning(f"没有{metric}为正的数据")
        return None
    
    fig = go.Figure()
    
    # 添加call数据（正值）
    if not calls_filtered.empty:
        calls_filtered = calls_filtered.sort_values('strike_price')
        fig.add_trace(go.Bar(
            x=calls_filtered['strike_price'],
            y=calls_filtered[metric],
            name='看涨期权 (Calls)',
            marker_color='green',
            opacity=0.7,
            hovertemplate=f'<b>看涨期权</b><br>' +
                         '行权价: %{x}<br>' +
                         f'{y_label}: %{{y}}<br>' +
                         '<extra></extra>'
        ))
    
    # 添加put数据（负值）
    if not puts_filtered.empty:
        puts_filtered = puts_filtered.sort_values('strike_price')
        fig.add_trace(go.Bar(
            x=puts_filtered['strike_price'],
            y=-puts_filtered[metric],  # 负值显示在下方
            name='看跌期权 (Puts)',
            marker_color='red',
            opacity=0.7,
            hovertemplate=f'<b>看跌期权</b><br>' +
                         '行权价: %{x}<br>' +
                         f'{y_label}: %{{customdata}}<br>' +
                         '<extra></extra>',
            customdata=puts_filtered[metric]
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="行权价",
        yaxis_title=f"{y_label} (看跌期权显示为负值)",
        height=600,
        barmode='group',
        hovermode='x unified'
    )
    
    # 更新y轴标签，显示绝对值
    fig.update_yaxes(
        tickformat='.0f'
    )
    
    return fig


def main():
    st.set_page_config(
        page_title="期权跟踪",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 期权跟踪分析")
    
    # 加载期权数据
    df = load_options_data()
    
    if df is None:
        st.error("无法加载期权数据")
        return
    
    # 侧边栏选择
    with st.sidebar:
        st.header("📋 数据选择")
        
        # 选择股票
        available_stocks = df['stock_code'].unique()
        selected_stock = st.selectbox(
            "选择股票:",
            options=available_stocks,
            help="选择要分析的股票期权"
        )
        
        # 选择到期日
        available_dates = df[df['stock_code'] == selected_stock]['expiry_date'].unique()
        # 按时间从新到旧排序
        available_dates = sorted(available_dates, reverse=True)
        selected_date = st.selectbox(
            "选择到期日:",
            options=available_dates,
            format_func=lambda x: x.strftime('%Y-%m-%d')
        )
        
        # 选择更新时间
        available_times = df[(df['stock_code'] == selected_stock) & 
                           (df['expiry_date'] == selected_date)]['update_time'].unique()
        selected_time = st.selectbox(
            "选择更新时间:",
            options=available_times,
            format_func=lambda x: x.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # 显示数据信息
        st.info(f"""
        **数据信息:**
        - 股票: {selected_stock}
        - 到期日: {selected_date.strftime('%Y-%m-%d')}
        - 更新时间: {selected_time.strftime('%Y-%m-%d %H:%M:%S')}
        """)
    
    # 过滤数据
    filtered_df = df[
        (df['stock_code'] == selected_stock) & 
        (df['expiry_date'] == selected_date) & 
        (df['update_time'] == selected_time)
    ].copy()
    
    # 对于SPY.US，过滤掉strike_price小于500的数据
    if selected_stock == "SPY.US":
        filtered_df = filtered_df[filtered_df['strike_price'] >= 550].copy()
        if not filtered_df.empty:
            st.info(f"已过滤SPY.US数据：只显示行权价 >= 500 的期权")
    
    if filtered_df.empty:
        st.error("没有找到符合条件的数据")
        return
    
    # 数据概览
    st.subheader(f"{selected_stock} 期权数据概览")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        total_options = len(filtered_df)
        st.metric(
            "期权总数",
            total_options
        )
    
    with col2:
        calls_count = len(filtered_df[filtered_df['type'] == 'call'])
        puts_count = len(filtered_df[filtered_df['type'] == 'put'])
        st.metric(
            "Calls/Puts",
            f"{calls_count}/{puts_count}"
        )
    
    with col3:
        total_volume = filtered_df['volume'].sum()
        st.metric(
            "总成交量",
            f"{total_volume:,}"
        )
    
    with col4:
        total_turnover = filtered_df['turnover'].sum()
        st.metric(
            "总成交额",
            f"${total_turnover:,.0f}"
        )
    
    with col5:
        total_oi = filtered_df['open_interest'].sum()
        st.metric(
            "总未平仓",
            f"{total_oi:,}"
        )
    
    with col6:
        # 获取标的价格（取第一个非空值）
        stock_close_price = filtered_df['stock_close_price'].iloc[0] if not filtered_df.empty else 0
        st.metric(
            "标的价格",
            f"${stock_close_price:.2f}"
        )
    
    # 图表展示
    st.subheader("📊 期权数据分析")
    
    # 创建三个标签页
    tab1, tab2, tab3 = st.tabs(["成交量分析", "成交额分析", "未平仓分析"])
    
    with tab1:
        st.subheader("成交量对比 (Calls vs Puts)")
        volume_chart = create_combined_chart(
            filtered_df, 
            'volume', 
            f"{selected_stock} 成交量分布 - {selected_date.strftime('%Y-%m-%d')}",
            "成交量"
        )
        if volume_chart:
            st.plotly_chart(volume_chart, use_container_width=True)
    
    with tab2:
        st.subheader("成交额对比 (Calls vs Puts)")
        turnover_chart = create_combined_chart(
            filtered_df, 
            'turnover', 
            f"{selected_stock} 成交额分布 - {selected_date.strftime('%Y-%m-%d')}",
            "成交额 ($)"
        )
        if turnover_chart:
            st.plotly_chart(turnover_chart, use_container_width=True)
    
    with tab3:
        st.subheader("未平仓对比 (Calls vs Puts)")
        oi_chart = create_combined_chart(
            filtered_df, 
            'open_interest', 
            f"{selected_stock} 未平仓分布 - {selected_date.strftime('%Y-%m-%d')}",
            "未平仓"
        )
        if oi_chart:
            st.plotly_chart(oi_chart, use_container_width=True)
    
    # 数据表格
    st.subheader("📋 详细数据")
    
    # 显示原始数据
    st.dataframe(
        filtered_df[['strike_price', 'type', 'volume', 'turnover', 'open_interest']].sort_values('strike_price'),
        use_container_width=True,
        height=400
    )

if __name__ == "__main__":
    main()
