import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 設定網頁頁面配置 ---
st.set_page_config(page_title="台股樂活五線譜", layout="wide")

# --- 2. 設定中文顯示與雲端相容性 ---
# 檢查環境是否有微軟正黑體，沒有則不設定(避免報錯)，並讓圖表能顯示負號
plt.rcParams['axes.unicode_minus'] = False 
IS_CLOUD = False
try:
    # 嘗試設定字體
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial']
    # 簡單測試是否能顯示中文 (本地環境通常 OK)
except:
    IS_CLOUD = True

@st.cache_data(ttl=3600)
def load_data(stock_id, period_years):
    dl = DataLoader()
    # 如果你有 FinMind Token，請取消下面這行註釋並填入 Token
    # dl.login(token="YOUR_FINMIND_TOKEN") 
    
    stock_name = ""
    try:
        df_info = dl.taiwan_stock_info()
        if not df_info.empty:
            stock_name_row = df_info[df_info['stock_id'] == stock_id]
            stock_name = stock_name_row['stock_name'].values[0] if not stock_name_row.empty else ""
    except:
        pass # 抓不到名稱不影響繪圖

    try:
        # 抓取報價 (多抓一點緩衝)
        start_date = (datetime.now() - timedelta(days=int((period_years + 0.6) * 365))).strftime('%Y-%m-%d')
        df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        
        # 關鍵檢查：防止 KeyError 'data' 或空資料
        if df is None or df.empty or 'close' not in df.columns:
            return None, None
            
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date') # 確保日期排序正確
        df = df.set_index('date')
        df = df.rename(columns={'close': 'Close'})
        
        total_days = int(period_years * 252) # 一年約 252 個交易日
        df = df.tail(total_days).copy()
        
        if len(df) < 100: # 資料太少無法計算趨勢
            return None, "資料量不足"
            
        return df, f"{stock_id} {stock_name}".strip()
    except Exception as e:
        st.error(f"連線 API 發生錯誤: {e}")
        return None, None

# --- 3. 側邊欄控制區 ---
st.sidebar.header("📊 設定參數")
stock_id = st.sidebar.text_input("輸入台股代碼 (例如 2330)", value="2330").strip()
period_years = st.sidebar.slider("趨勢計算年限 (推薦 3.5 年)", 1.0, 5.0, 3.5, 0.5)

# --- 4. 主畫面 ---
st.title("📈 樂活五線譜分析儀")
st.info("💡 提示：若出現 KeyError，通常是 FinMind API 免費流量達到上限，請稍後再試或輸入 Token。")

if stock_id:
    with st.spinner(f'正在分析 {stock_id} ...'):
        df, full_name = load_data(stock_id, period_years)
    
    if df is not None:
        # 1. 計算線性回歸 (Trend Line)
        y = df['Close'].values
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        df['Trend'] = slope * x + intercept
        
        # 2. 計算標準差與五條線
        std = np.std(
