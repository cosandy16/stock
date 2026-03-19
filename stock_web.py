import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from FinMind.data import DataLoader
from datetime import datetime, timedelta

# --- 1. 設定網頁頁面配置 ---
st.set_page_config(page_title="全球股市五線譜", layout="wide")

# --- 2. 設定環境偵測與字體切換 ---
def get_font_settings():
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    if 'Microsoft JhengHei' in available_fonts:
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
        return False
    else:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        return True

plt.rcParams['axes.unicode_minus'] = False 
IS_CLOUD = get_font_settings()

@st.cache_data(ttl=3600)
def load_data(stock_id, period_years):
    dl = DataLoader()
    
    # 判斷是台股還是美股
    is_us = any(c.isalpha() for c in stock_id)
    stock_id = stock_id.upper()
    start_date = (datetime.now() - timedelta(days=int((period_years + 0.6) * 365))).strftime('%Y-%m-%d')
    
    try:
        if is_us:
            # 抓取美股：指定美股資料集
            df = dl.get_data(dataset="USStockPrice", data_id=stock_id, start_date=start_date)
            display_name = f"US Stock: {stock_id}"
        else:
            # 抓取台股
            df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
            display_name = stock_id # 台股名稱抓取邏輯可保留原樣

        if df is None or df.empty:
            return None, None
            
        # --- 核心修正：統一欄位名稱為小寫，避免大小寫造成的 KeyError ---
        df.columns = [c.lower() for c in df.columns]
        
        # 再次檢查是否有 close 欄位
        if 'close' not in df.columns:
            return None, None
            
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').set_index('date')
        df = df.rename(columns={'close': 'Close'}) # 統一改回我們後面計算用的 'Close'
        
        df = df.tail(int(period_years * 252)).copy()
        return df, display_name
    except Exception as e:
        st.error(f"錯誤細節: {e}")
        return None, None

# --- 3. 側邊欄控制區 ---
st.sidebar.header("📊 設定參數" if not IS_CLOUD else "📊 Settings")
stock_input = st.sidebar.text_input("輸入代碼 (2330 或 AAPL)", value="2330").strip()
period_years = st.sidebar.slider("趨勢年限", 1.0, 5.0, 3.5, 0.5)

# --- 4. 主畫面 ---
st.title("📈 全球股市五線譜" if not IS_CLOUD else "📈 Global Lohas 5-Lines")
st.caption("自動識別台股 (數字) 與美股 (代號)")

if stock_input:
    with st.spinner(f'Analyzing {stock_input} ...'):
        df, full_name = load_data(stock_input, period_years)
    
    if df is not None:
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

        col1, col2, col3 = st.columns(3)
        col1.metric("目前價格", f"{last_price}")
        col2.metric("趨勢線值", f"{trend_price:.2f}")
        col3.metric("偏離率", f"{bias_ratio:.2f} %", delta=f"{bias_ratio:.2f}%", delta_color="inverse")

        # --- 5. 繪製圖表 (手機優化版) ---
        plt.rcParams['font.size'] = 14          # 全域字體加大
        plt.rcParams['legend.fontsize'] = 11    # 圖例適中
        
        # 增加高度比例，手機直向看圖更清楚
        fig, ax = plt.subplots(figsize=(10, 7)) 
        
        L = {
            'close': '收盤價' if not IS_CLOUD else 'Price',
            'up2': '極度樂觀' if not IS_CLOUD else 'Optimistic+2',
            'up1': '樂觀' if not IS_CLOUD else 'Optimistic+1',
            'trend': '趨勢線' if not IS_CLOUD else 'Trend',
            'low1': '悲觀' if not IS_CLOUD else 'Pessimistic-1',
            'low2': '極度悲觀' if not IS_CLOUD else 'Pessimistic-2',
        }

        ax.plot(df.index, df['Close'], label=L['close'], color='black', linewidth=1.5, alpha=0.7)
        ax.plot(df.index, df['Upper_2'], label=L['up2'], color='#d62728', linestyle='--', linewidth=1)
        ax.plot(df.index, df['Upper_1'], label=L['up1'], color='#ff7f0e', linestyle='--', linewidth=1)
        ax.plot(df.index, df['Trend'], label=L['trend'], color='#1f77b4', linewidth=2)
        ax.plot(df.index, df['Lower_1'], label=L['low1'], color='#2ca02c', linestyle='--', linewidth=1)
        ax.plot(df.index, df['Lower_2'], label=L['low2'], color='#006400', linestyle='--', linewidth=1)
        
        ax.set_title(f"{full_name} ({period_years}Y)", fontsize=16)
        
        # 核心優化：圖例放在圖表上方，避免擠壓 X 軸寬度造成手機字體過小
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
        
        ax.grid(True, alpha=0.2)
        plt.tight_layout()
        
        st.pyplot(fig)
        
        with st.expander("📝 原始數據 (Raw Data)"):
            st.dataframe(df.tail(10))
            
    elif full_name == "資料量不足":
        st.warning("數據太少，無法計算。")
    else:
        st.error("查無資料，請確認代碼（台股 2330 / 美股 AAPL）。")
