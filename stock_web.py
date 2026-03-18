import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 設定網頁頁面配置 ---
st.set_page_config(page_title="台股樂活五線譜", layout="wide")

# --- 設定中文顯示 (重要：部署到雲端時需注意字體問題) ---
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False 

@st.cache_data(ttl=3600) # 快取功能：一小時內重複查詢不重抓，節省流量
def load_data(stock_id, period_years):
    dl = DataLoader()
    
    # 抓取股票名稱
    try:
        df_info = dl.taiwan_stock_info()
        stock_name_row = df_info[df_info['stock_id'] == stock_id]
        stock_name = stock_name_row['stock_name'].values[0] if not stock_name_row.empty else ""
    except:
        stock_name = ""
    
    # 抓取報價
    start_date = (datetime.now() - timedelta(days=int((period_years + 0.5) * 365))).strftime('%Y-%m-%d')
    df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
    
    if df.empty:
        return None, None
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    df = df.rename(columns={'close': 'Close'})
    
    total_days = int(period_years * 252)
    df = df.tail(total_days).copy()
    return df, f"{stock_id} {stock_name}".strip()

# --- 側邊欄控制區 ---
st.sidebar.header("設定參數")
stock_id = st.sidebar.text_input("輸入台股代碼", value="2330")
period_years = st.sidebar.slider("趨勢計算年限", 1.0, 5.0, 3.5, 0.5)

# --- 主畫面 ---
st.title("📈 樂活五線譜分析儀")
st.markdown(f"目前分析標的：**{stock_id}**")

if stock_id:
    df, full_name = load_data(stock_id, period_years)
    
    if df is not None:
        # 1. 計算線性回歸
        y = df['Close'].values
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        df['Trend'] = slope * x + intercept
        
        # 2. 計算標準差與五條線
        std = np.std(y - df['Trend'])
        df['Upper_2'] = df['Trend'] + 2 * std
        df['Upper_1'] = df['Trend'] + 1 * std
        df['Lower_1'] = df['Trend'] - 1 * std
        df['Lower_2'] = df['Trend'] - 2 * std
        
        # 3. 計算目前的偏離率
        last_price = df['Close'].iloc[-1]
        trend_price = df['Trend'].iloc[-1]
        bias_ratio = ((last_price - trend_price) / trend_price) * 100

        # 4. 顯示關鍵數據卡片
        col1, col2, col3 = st.columns(3)
        col1.metric("目前股價", f"{last_price}")
        col2.metric("中心線值", f"{trend_price:.2f}")
        col3.metric("偏離率", f"{bias_ratio:.2f} %", delta=f"{bias_ratio:.2f}%", delta_color="inverse")

        # 5. 繪製圖表
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['Close'], label='收盤價', color='black', linewidth=1.5, alpha=0.6)
        ax.plot(df.index, df['Upper_2'], label='極度樂觀 (+2SD)', color='#d62728', linestyle='--')
        ax.plot(df.index, df['Upper_1'], label='樂觀 (+1SD)', color='#ff7f0e', linestyle='--')
        ax.plot(df.index, df['Trend'], label='趨勢線 (中心線)', color='#1f77b4', linewidth=2)
        ax.plot(df.index, df['Lower_1'], label='悲觀 (-1SD)', color='#2ca02c', linestyle='--')
        ax.plot(df.index, df['Lower_2'], label='極度悲觀 (-2SD)', color='#006400', linestyle='--')
        
        ax.set_title(f"{full_name} 樂活五線譜 ({period_years}Y)", fontsize=14)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        st.pyplot(fig) # 在網頁畫出圖表
        
        # 6. 顯示原始資料表格 (可折疊)
        with st.expander("查看原始數據"):
            st.dataframe(df.tail(10))
            
    else:
        st.error("找不到該股票資料，請檢查代碼是否正確。")