import yfinance as yf
import datetime
import streamlit as st
import requests
import pandas as pd

# --- 1. 页面配置 (设置为宽屏) ---
st.set_page_config(
    page_title="美股定投策略助手",
    page_icon="🇺🇸",
    layout="wide"
)

# --- 2. 数据获取函数 (带缓存功能) ---

@st.cache_data(ttl=3600)  # 缓存1小时，避免频繁请求
def get_market_data(ticker_symbol):
    """获取市场历史数据"""
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="max")
    return hist

@st.cache_data(ttl=3600)  # 缓存1小时
def get_fear_and_greed_index():
    """获取贪婪与恐惧指数"""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.cnn.com/",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 如果请求失败则抛出异常
        data = response.json()
        
        score = int(data['fear_and_greed']['score'])
        rating_en = data['fear_and_greed']['rating']
        
        translations = {
            "extreme fear": "极度恐惧 🥶", "fear": "恐惧 😨", "neutral": "中性 😐",
            "greed": "贪婪 🤑", "extreme greed": "极度贪婪 😈"
        }
        rating = translations.get(rating_en.lower(), rating_en)
        return score, rating
    except requests.exceptions.RequestException as e:
        st.toast(f"无法获取贪婪指数: {e}", icon="⚠️")
        return "N/A", "获取失败"
    except Exception as e:
        st.toast(f"处理贪婪指数时出错: {e}", icon="🔥")
        return "N/A", "处理失败"

# --- 3. 主应用界面 ---

def main():
    """
    渲染Streamlit UI界面
    """
    # --- CSS 样式注入 (让界面更精致、字体更小) ---
    st.markdown("""
        <style>
            /* 调整主标题 */
            h1 { font-size: 1.8rem !important; padding-bottom: 0.5rem !important; }
            /* 调整小标题 */
            h3 { font-size: 1.2rem !important; padding-top: 0.5rem !important; }
            /* 调整 Metric 指标数值 */
            [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
            /* 调整 Metric 指标标签 */
            [data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
            /* 调整侧边栏文字 */
            [data-testid="stSidebar"] { font-size: 0.9rem; }
            /* 减少顶部空白 */
            .block-container { padding-top: 2rem !important; }
            /* 调整普通文本 */
            p { font-size: 0.95rem; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🇺🇸 美股定投策略助手")
    st.caption("一个基于市场回撤与情绪指标的定投决策工具")

    # --- 侧边栏：放置设置和操作按钮 ---
    with st.sidebar:
        st.markdown("### 🔍 指数选择")
        index_map = {
            "标普500 (S&P 500)": "^GSPC",
            "纳斯达克 (Nasdaq)": "^IXIC",
            "道琼斯 (Dow Jones)": "^DJI"
        }
        selected_name = st.selectbox("请选择要分析的指数", list(index_map.keys()))
        ticker_symbol = index_map[selected_name]

        st.markdown("### ⚙️ 策略设置")
        drawdown_threshold = st.slider(
            "定投触发回撤阈值 (%)", 
            min_value=5, max_value=30, value=10, step=1,
            help="当指数从历史最高点回撤超过此百分比时，建议开始定投。"
        )
        
        if st.button("🔄 清除缓存并刷新"):
            st.cache_data.clear()
            st.rerun()
        
        st.caption(f"数据更新于: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- 主面板：获取数据并展示 ---
    with st.spinner(f"正在获取 {selected_name} 历史数据..."):
        hist = get_market_data(ticker_symbol)

    if hist is None or hist.empty:
        st.error(f"无法获取 {selected_name} 数据，请检查网络或稍后再试。")
        return

    fg_score, fg_rating = get_fear_and_greed_index()

    # 计算核心指标
    all_time_high = hist['High'].max()
    current_price = hist['Close'].iloc[-1]
    current_date = hist.index[-1].strftime('%Y-%m-%d')
    drawdown = (all_time_high - current_price) / all_time_high
    drawdown_percent = drawdown * 100

    # --- 4. 美化后的指标展示 ---
    st.subheader(f"📊 {selected_name} 核心指标 (截至 {current_date})", divider='rainbow')
    
    cols = st.columns(4)
    cols[0].metric("历史最高点 (ATH)", f"{all_time_high:,.2f}")
    cols[1].metric("最新收盘价", f"{current_price:,.2f}", f"{current_price - hist['Close'].iloc[-2]:,.2f}")
    cols[2].metric("较最高点回撤", f"{drawdown_percent:.2f}%", help="计算公式: (历史最高点 - 最新价) / 历史最高点")
    cols[3].metric("贪婪恐惧指数", f"{fg_score}", delta=fg_rating)

    # --- 5. 更智能和美观的投资建议 ---
    st.subheader("💡 今日定投建议", divider='rainbow')

    is_drawdown_met = drawdown_percent >= drawdown_threshold
    is_extreme_fear = isinstance(fg_score, int) and fg_score <= 25

    with st.container(border=True):
        if is_drawdown_met:
            st.success(f"✅ **建议定投**：当前回撤 **{drawdown_percent:.2f}%**，已达到您设置的 **{drawdown_threshold}%** 阈值。", icon="💰")
            if is_extreme_fear:
                st.info("📈 **额外信号**：市场处于 **极度恐惧** 状态，是很好的逆向投资时机。", icon="🔔")
        elif is_extreme_fear:
            st.success(f"✅ **建议定投**：市场情绪已进入 **极度恐惧** ({fg_score})，是潜在的买入机会。", icon="💰")
        else:
            st.warning(f"🚫 **建议观望**：当前回撤 **{drawdown_percent:.2f}%**，未达到您设置的 **{drawdown_threshold}%** 阈值。", icon="✋")
            st.info(f"当前市场情绪为 **{fg_rating}**。")

    # --- 6. 新增价格走势图 ---
    st.subheader("📈 近一年价格走势", divider='rainbow')
    last_year_data = hist[hist.index > (hist.index[-1] - pd.DateOffset(days=365))]
    st.line_chart(last_year_data['Close'], use_container_width=True)


if __name__ == "__main__":
    main()