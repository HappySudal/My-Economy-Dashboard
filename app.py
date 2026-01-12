import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go
import google.generativeai as genai  # [핵심] 공식 라이브러리 사용

# 1. 페이지 설정
st.set_page_config(page_title="Pro 경제 대시보드 v2.3", layout="wide", page_icon="📈")

# 2. 커스텀 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    button[data-baseweb="tab"] div p { font-size: 20px !important; font-weight: 700 !important; }
    div.stButton > button {
        background-color: #FF4B4B !important; color: white !important;
        font-size: 16px !important; border: none; padding: 10px 20px;
        border-radius: 8px; width: 100%; margin-top: 10px; margin-bottom: 20px;
    }
    div.stButton > button:hover { background-color: #FF2B2B !important; border: 1px solid white; }
    </style>
    """, unsafe_allow_html=True)

st.title(f"📈 Pro Global Market Dashboard")
st.markdown(f"**{datetime.date.today()}** 기준 | 암호화폐, ETF, 국내외 증시 통합 분석")

# [Session State] 리포트 유지
if "ai_report" not in st.session_state:
    st.session_state["ai_report"] = ""

# API 키 설정
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Google API Key를 입력하세요", type="password")

# ---------------------------------------------------------
# [기능 1] 데이터 수집
# ---------------------------------------------------------
ASSETS = {
    "🇰🇷 코스피 (KOSPI)": "^KS11", "🇰🇷 코스닥 (KOSDAQ)": "^KQ11",
    "🇺🇸 S&P 500": "SPY", "🇺🇸 나스닥 100": "QQQ",
    "🪙 비트코인": "BTC-USD", "💎 이더리움": "ETH-USD",
    "💵 원/달러 환율": "KRW=X", "🥇 금 선물": "GC=F",
    "🛢️ WTI 원유": "CL=F", "🇺🇸 미국채 10년": "^TNX",
    "🏢 삼성전자": "005930.KS", "🍎 애플": "AAPL"
}

@st.cache_data(ttl=300)
def get_market_data(period="1mo", interval="1d"):
    data_dict = {}
    for name, ticker in ASSETS.items():
        try:
            stock = yf.Ticker(ticker)
            if period == "1d": hist = stock.history(period="1d", interval="30m")
            else: hist = stock.history(period=period, interval=interval)
            if not hist.empty: data_dict[name] = hist
        except: continue
    return data_dict

def draw_chart(name, df):
    color = '#ff4b4b' if len(df) > 1 and df['Close'].iloc[-1] >= df['Close'].iloc[0] else '#4b7bff'
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=name, line=dict(color=color, width=2)))
    fig.update_layout(
        title=dict(text=f"{name}", font=dict(color="white", size=14)),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor='#333333', color="white"),
        margin=dict(l=10, r=10, t=30, b=10), height=200
    )
    return fig

# ---------------------------------------------------------
# [기능 2] 뉴스 수집
# ---------------------------------------------------------
def get_real_news():
    news_list = []
    for t in ["^KS11", "SPY", "BTC-USD", "005930.KS"]:
        try:
            ticker = yf.Ticker(t)
            news = ticker.news
            if news:
                for n in news[:2]:
                    title = n.get('title', '제목 없음')
                    link = n.get('link', '#')
                    publisher = n.get('publisher', 'Unknown')
                    pub_time = n.get('providerPublishTime')
                    time_str = datetime.datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M') if pub_time else datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    news_list.append({"title": title, "publisher": publisher, "link": link, "time": time_str})
        except: continue
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list[:15]

# ---------------------------------------------------------
# [기능 3] AI 분석 (공식 라이브러리 사용으로 수정됨)
# ---------------------------------------------------------
def get_ai_analysis(market_summary_text):
    if not api_key:
        return "⚠️ 오류: Google API 키가 입력되지 않았습니다."

    try:
        # 공식 라이브러리 설정
        genai.configure(api_key=api_key)
        
        # 최신 모델 사용 (gemini-1.5-flash가 빠르고 안정적임)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        당신은 월스트리트의 수석 투자 전략가입니다. 아래 시장 데이터를 바탕으로 전문적인 브리핑을 작성하세요.

        [현재 시장 데이터]
        {market_summary_text}

        [작성 가이드]
        1. **시장 동향 요약**: 코스피, 미국 증시, 암호화폐 간의 상관관계를 분석하세요.
        2. **핵심 원인 분석**: 현재 상승 또는 하락을 이끄는 거시경제적 요인(환율, 금리 등)을 추론하세요.
        3. **투자 전략**: 보수적 투자자와 공격적 투자자를 위한 대응 전략을 각각 한 줄로 제시하세요.
        4. 중요 숫자는 **볼드체**로 표시하고, 가독성 높은 마크다운 형식을 사용하세요.
        """
        
        response = model.generate_content(prompt)
        return f"✅ **Gemini Market Insight**\n\n{response.text}"
        
    except Exception as e:
        return f"⚠️ **분석 실패**: {str(e)}\n\n(API 키가 정확한지, 혹은 사용량이 초과되지 않았는지 확인해주세요.)"

# =========================================================
# 메인 화면
# =========================================================
st.sidebar.header("⚙️ 차트 기간 설정")
period_option = st.sidebar.radio("기간 선택", ('1일', '1개월', '3개월', '1년', '3년'), index=1)
period_map = {'1일': '1d', '1개월': '1mo', '3개월': '3mo', '1년': '1y', '3년': '3y'}
interval_map = {'1일': '30m', '1개월': '1d', '3개월': '1d', '1년': '1d', '3년': '1wk'}

with st.spinner('데이터 수집 중...'):
    market_data = get_market_data(period_map[period_option], interval_map[period_option])

tab1, tab2, tab3 = st.tabs(["📊 마켓 대시보드", "📰 실시간 뉴스", "🤖 AI 인사이트"])

with tab1:
    cols = st.columns(4) 
    idx = 0
    for name, df in market_data.items():
        if len(df) > 0:
            curr = df['Close'].iloc[-1]
            prev = df['Close'].iloc[0]
            pct = ((curr - prev) / prev) * 100
            with cols[idx % 4]:
                st.metric(label=name, value=f"{curr:,.2f}", delta=f"{pct:.2f}%")
                st.plotly_chart(draw_chart(name, df), use_container_width=True)
                st.divider()
            idx += 1

with tab2:
    st.subheader("🌍 주요 뉴스 피드")
    news_items = get_real_news()
    if news_items:
        for n in news_items:
            st.markdown(f"""
            <div style="background-color: #262730; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 5px solid #FF4B4B;">
                <a href="{n['link']}" target="_blank" style="text-decoration: none; color: #FAFAFA;">
                    <h4 style="margin:0; font-size:18px;">{n['title']}</h4>
                </a>
                <div style="color: #A0A0A0; margin-top: 8px; font-size: 14px;">
                    <span>📅 {n['time']}</span> | <span>📰 {n['publisher']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("뉴스가 없습니다.")

with tab3:
    st.markdown("### 🚀 AI 마켓 인텔리전스")
    st.markdown("""
    <p style='color: white; font-size: 16px; margin-bottom: 20px;'>
        AI매크로 전략리포트, 환율, 선물, 채권 데이터를 종합하여 시장을 정밀 분석합니다.
    </p>
    """, unsafe_allow_html=True)
    
    if st.button("AI 마켓 브리핑 생성하기"):
        with st.spinner("Gemini가 시장 데이터를 분석 중입니다..."):
            summary_txt = ""
            for name, df in market_data.items():
                if not df.empty:
                    summary_txt += f"{name}: {df['Close'].iloc[-1]:.2f}\n"
            
            result_text = get_ai_analysis(summary_txt)
            st.session_state["ai_report"] = result_text

    if st.session_state["ai_report"]:
        st.markdown("---")
        st.markdown(st.session_state["ai_report"])
