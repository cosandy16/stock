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
        std = np.std(y - df['Trend'])
        df['Upper_2'] = df['Trend'] + 2 * std
        df['Upper_1'] = df['Trend'] + 1 * std
        df['Lower_1'] = df['Trend'] - 1 * std
        df['Lower_2'] = df['Trend'] - 2 * std
        
        # 3. 計算目前的數據
        last_price = df['Close'].iloc[-1]
        trend_price = df['Trend'].iloc[-1]
        bias_ratio = ((last_price - trend_price) / trend_price) * 100

        # 4. 顯示數據指標
        col1, col2, col3 = st.columns(3)
        col1.metric("目前股價 (Current)", f"{last_price}")
        col2.metric("中心線值 (Trend)", f"{trend_price:.2f}")
        col3.metric("偏離率 (Bias)", f"{bias_ratio:.2f} %", delta=f"{bias_ratio:.2f}%", delta_color="inverse")

        # 5. 繪製圖表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 設定語系 (避免雲端亂碼)
        L = {
            'close': '收盤價 (Close)' if not IS_CLOUD else 'Close',
            'up2': '極度樂觀 (+2SD)' if not IS_CLOUD else 'Extreme Optimistic (+2SD)',
            'up1': '樂觀 (+1SD)' if not IS_CLOUD else 'Optimistic (+1SD)',
            'trend': '趨勢線 (Trend)' if not IS_CLOUD else 'Trend Line',
            'low1': '悲觀 (-1SD)' if not IS_CLOUD else 'Pessimistic (-1SD)',
            'low2': '極度悲觀 (-2SD)' if not IS_CLOUD else 'Extreme Pessimistic (-2SD)',
        }

        ax.plot(df.index, df['Close'], label=L['close'], color='black', linewidth=1.5, alpha=0.6)
        ax.plot(df.index, df['Upper_2'], label=L['up2'], color='#d62728', linestyle='--')
        ax.plot(df.index, df['Upper_1'], label=L['up1'], color='#ff7f0e', linestyle='--')
        ax.plot(df.index, df['Trend'], label=L['trend'], color='#1f77b4', linewidth=2)
        ax.plot(df.index, df['Lower_1'], label=L['low1'], color='#2ca02c', linestyle='--')
        ax.plot(df.index, df['Lower_2'], label=L['low2'], color='#006400', linestyle='--')
        
        ax.set_title(f"{full_name} ({period_years}Y Trend)", fontsize=14)
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        st.pyplot(fig)
        
        # 6. 數據詳情
        with st.expander("📝 查看原始數據與分析結果"):
            st.dataframe(df.tail(10))
            
    elif full_name == "資料量不足":
        st.warning("該標的上市時間太短，不足以計算長期趨勢。")
    else:
        st.error("無法取得資料。請確認代碼是否正確，或 API 流量已達上限。")
