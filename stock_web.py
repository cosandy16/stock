import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 設定網頁頁面配置 ---
st.set_page_config(page_title="台股樂活五線譜", layout="wide")

# --- 2. 設定環境偵測與字體切換 ---
def get_font_settings():
    # 檢查系統中可用的字體名稱
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    if 'Microsoft JhengHei' in available_fonts:
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
        return False  # 不是雲端 (或是具備中文字體的環境)
    else:
        # 雲端環境通常只有 DejaVu Sans 或 Arial
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        return True   # 是雲端環境 (需使用英文標籤)

plt.rcParams['axes.unicode_minus'] = False 
IS_CLOUD = get_font_settings()

@st.cache_data(ttl=3600)
def load_data(stock_id, period_years):
    dl = DataLoader()
    
    stock_name = ""
    try:
        df_info = dl.taiwan_stock_info()
        if not df_info.empty:
            stock_name_row = df_info[df_info['stock_id'] == stock_id]
            stock_name = stock_name_row['stock_name'].values[0] if not stock_name_row.empty else ""
    except:
        pass

    try:
        start_date = (datetime.now() - timedelta(days=int((period_years + 0.6) * 365))).strftime('%Y-%m-%d')
        df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        
        if df is None or df.empty or 'close' not in df.columns:
            return None, None
            
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df = df.set_index('date')
        df = df.rename(columns={'close': 'Close'})
        
        total_days = int(period_years * 252)
        df = df.tail(total_days).copy()
        
        if len(df) < 100:
            return None, "資料量不足"
            
        # 如果是雲端，名稱只傳代碼避免亂碼；本地則傳全名
        display_name = stock_id if IS_CLOUD else f"{stock_id} {stock_name}"
        return df, display_name.strip()
    except Exception as e:
        st.error(f"連線 API 發生錯誤: {e}")
        return None, None

# --- 3. 側邊欄控制區 ---
st.sidebar.header("📊 設定參數" if not IS_CLOUD else "📊 Settings")
stock_id = st.sidebar.text_input("輸入台股代碼" if not IS_CLOUD else "Stock ID", value="2330").strip()
period_years = st.sidebar.slider("趨勢計算年限" if not IS_CLOUD else "Period (Years)", 1.0, 5.0, 3.5, 0.5)

# --- 4. 主畫面 ---
st.title("📈 樂活五線譜分析儀" if not IS_CLOUD else "📈 Lohas 5-Lines Analysis")

if stock_id:
    with st.spinner(f'Analyzing {stock_id} ...'):
        df, full_name = load_data(stock_id, period_years)
    
    if df is not None:
        # 計算回歸與五線譜
        y = df['Close'].values
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        df['Trend'] = slope * x + intercept
        
        std = np.std(y - df['Trend'])
        df['Upper_2'] = df['Trend'] + 2 * std
        df['Upper_1'] = df['Trend'] + 1 * std
        df['Lower_1'] = df['Trend'] - 1 * std
        df['Lower_2'] = df['Trend'] - 2 * std
        
        last_price = df['Close'].iloc[-1]
        trend_price = df['Trend'].iloc[-1]
        bias_ratio = ((last_price - trend_price) / trend_price) * 100

        # 數據卡片 (標籤自動換語系)
        col1, col2, col3 = st.columns(3)
        col1.metric("目前股價" if not IS_CLOUD else "Current Price", f"{last_price}")
        col2.metric("中心線值" if not IS_CLOUD else "Trend Value", f"{trend_price:.2f}")
        col3.metric("偏離率" if not IS_CLOUD else "Bias Ratio", f"{bias_ratio:.2f} %", delta=f"{bias_ratio:.2f}%", delta_color="inverse")

        # 5. 繪製圖表
        #fig, ax = plt.subplots(figsize=(12, 6))
        # --- 在 plt.subplots 之前加入這些設定 ---
        plt.rcParams['font.size'] = 12          # 提高基礎字體大小 (預設通常是 10)
        plt.rcParams['legend.fontsize'] = 10    # 圖例字體大小
        plt.rcParams['axes.labelsize'] = 12     # 座標軸標籤大小
        plt.rcParams['xtick.labelsize'] = 10    # X 軸刻度大小
        plt.rcParams['ytick.labelsize'] = 10    # Y 軸刻度大小

        fig, ax = plt.subplots(figsize=(10, 8)) # 稍微調高高度比例，適合手機直向閱讀
        
        # 語言對照表
        L = {
            'close': '收盤價' if not IS_CLOUD else 'Close Price',
            'up2': '極度樂觀 (+2SD)' if not IS_CLOUD else 'Extreme Optimistic (+2SD)',
            'up1': '樂觀 (+1SD)' if not IS_CLOUD else 'Optimistic (+1SD)',
            'trend': '趨勢線 (中心線)' if not IS_CLOUD else 'Trend Line',
            'low1': '悲觀 (-1SD)' if not IS_CLOUD else 'Pessimistic (-1SD)',
            'low2': '極度悲觀 (-2SD)' if not IS_CLOUD else 'Extreme Pessimistic (-2SD)',
        }

        ax.plot(df.index, df['Close'], label=L['close'], color='black', linewidth=1.5, alpha=0.6)
        ax.plot(df.index, df['Upper_2'], label=L['up2'], color='#d62728', linestyle='--')
        ax.plot(df.index, df['Upper_1'], label=L['up1'], color='#ff7f0e', linestyle='--')
        ax.plot(df.index, df['Trend'], label=L['trend'], color='#1f77b4', linewidth=2)
        ax.plot(df.index, df['Lower_1'], label=L['low1'], color='#2ca02c', linestyle='--')
        ax.plot(df.index, df['Lower_2'], label=L['low2'], color='#006400', linestyle='--')
        
        chart_title = f"{full_name} Lohas 5-Lines" if IS_CLOUD else f"{full_name} 樂活五線譜"
        ax.set_title(chart_title, fontsize=14)
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        st.pyplot(fig)
        
        # 6. 數據詳情
        expander_title = "📝 查看原始數據" if not IS_CLOUD else "📝 View Raw Data"
        with st.expander(expander_title):
            st.dataframe(df.tail(10))
            
    elif full_name == "資料量不足":
        st.warning("該標的上市時間太短，不足以計算長期趨勢。" if not IS_CLOUD else "Insufficient data for trend calculation.")
    else:
        st.error("無法取得資料。請確認代碼是否正確。" if not IS_CLOUD else "Data unavailable. Please check the Stock ID.")
