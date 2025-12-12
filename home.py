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

