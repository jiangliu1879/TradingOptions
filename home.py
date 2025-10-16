import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.stock_data import StockData

# 设置页面标题
st.set_page_config(page_title="市场概览", page_icon="📊", layout="wide")
st.title("📊 市场概览")

# 从数据库读取股票数据的通用函数
@st.cache_data
def load_stock_data(stock_code):
    """从数据库加载指定股票的历史数据"""
    try:
        # 从数据库获取股票数据
        stock_data = StockData.get_stock_data(stock_code=stock_code)
        
        if not stock_data:
            st.error(f"数据库中未找到 {stock_code} 的数据")
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame([record.to_dict() for record in stock_data])
        
        # 将timestamp列转换为datetime格式，使用 format='mixed' 处理不同格式
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        # 按时间排序
        df = df.sort_values('timestamp')
        # 添加日期列（不含时间）
        df['date'] = df['timestamp'].dt.date
        return df
    except Exception as e:
        st.error(f"从数据库读取 {stock_code} 数据时出错: {e}")
        return None

def get_daily_change_percentage(df):
    """计算当日涨跌幅度"""
    if df is None or len(df) < 2:
        return None, None, None, None
    
    # 获取最新交易日数据
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    # 计算涨跌额和涨跌幅
    change_amount = latest['close'] - previous['close']
    change_percentage = (change_amount / previous['close']) * 100
    
    return latest['close'], change_amount, change_percentage, latest['date']

# 从数据库加载所有股票数据
@st.cache_data
def load_all_stocks_data():
    """加载所有股票数据"""
    try:
        stock_codes = StockData.get_stock_codes()
        stocks_data = {}
        
        for code in stock_codes:
            stock_data = StockData.get_stock_data(stock_code=code)
            if stock_data:
                df = pd.DataFrame([record.to_dict() for record in stock_data])
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
                df = df.sort_values('timestamp')
                df['date'] = df['timestamp'].dt.date
                stocks_data[code] = df
        
        return stocks_data
    except Exception as e:
        st.error(f"加载股票数据时出错: {e}")
        return {}

# 加载所有股票数据
stocks_data = load_all_stocks_data()

# 显示当日市场概览
st.subheader("📈 当日市场表现")

if stocks_data:
    # 显示所有股票的涨跌幅度
    stock_names = {
        'SPY.US': 'SPY',
        'QQQ.US': 'QQQ', 
        'NVDA.US': 'NVDA',
        'HIMS.US': 'HIMS'
    }
    
    # 创建4列布局
    cols = st.columns(4)
    
    for i, (code, name) in enumerate(stock_names.items()):
        if code in stocks_data:
            df = stocks_data[code]
            close, change, change_pct, date = get_daily_change_percentage(df)
            
            with cols[i % 4]:
                if change is not None:
                    # 修正箭头方向：上涨用向上箭头，下跌用向下箭头
                    arrow = "📈" if change >= 0 else "📉"
                    # 上涨用绿色，下跌用红色
                    delta_color = "inverse" if change >= 0 else "normal"
                    st.metric(
                        f"{name} 收盘价",
                        f"${close:.2f}",
                        delta=f"{arrow} ${change:.2f} ({change_pct:.2f}%)",
                        delta_color=delta_color
                    )
                else:
                    st.metric(f"{name} 收盘价", "数据不足")