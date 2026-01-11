import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
import json
import feedparser

# 1. 페이지 설정
st.set_page_config(page_title="Pro 경제 대시보드 v2.3", layout="wide", page_icon="📈")

# 2. 커스텀 CSS (폰트 색상 강제 White 적용)
st.markdown("""
    <style>
    /* 전체 배경 다크모드 */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* [수정 요청] 금융지표 텍스트(제목, 숫자) 강제 흰색 적용 */
    [data-testid="stMetricLabel"] {
        color: #FFFFFF !important;
        font-size: 14px !important;
    }
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
    }

    /* 탭 메뉴: 폰트 14px, 흰색 */
    button[data-baseweb="tab"] div p {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
    }
    
    /* 탭 선택되었을 때 강조 색상 */
    button[data-baseweb="tab"][aria-selected="true"] div p {
        color: #FF4B4B !important;
    }

    /* 버튼 스타일 */
    div.stButton > button {
        background-color: #FF4B4B !important;
        color: white !important;
        font-size: 14px !important;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #FF2B2B !important;
        border: 1px solid white;
    }
    
    /* 뉴스 카드 링크 스타일 */
    a.news-link {
        text-decoration: none !important;
        color: #FAFAFA !important;
    }
    a.news-link:hover {
        color: #FF4B4B !important;
        text-decoration: underline !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title(f"📈 Pro Global Market Dashboard")
st.markdown(f"**{datetime.date.today()}** 기준 | 2026년 최신 금융 트렌드 분석")

# 사이드바: API 키
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("설정(Secrets)에서 Google API 키를 넣어주세요.")
    st.stop()

# ---------------------------------------------------------
# [기능 1] 데이터 수집 및 차트
# ---------------------------------------------------------
ASSETS = {
    "🇰🇷 코스피": "^KS11",
    "🇰🇷 코스닥": "^KQ11",
    "🇺🇸 S&P 500": "SPY",
    "🇺🇸 나스닥 100": "QQQ",
    "🪙 비트코인": "BTC-USD",
    "💎 이더리움": "ETH-USD",
    "💵 원/달러": "KRW=X",
    "🥇 금 선물": "GC=F",
    "🛢️ WTI 원유": "CL=F",
    "🇺🇸 국채 10년": "^TNX",
    "🏢 삼성전자": "005930.KS",
    "🍎 애플": "AAPL"
}

@st.cache_data(ttl=300)
def get_market_data(period="1mo", interval="1d"):
    data_dict = {}
    for name, ticker in ASSETS.items():
        try:
            stock = yf.Ticker(ticker)
            if period == "1d":
                hist = stock.history(period="1d", interval="30m")
            else:
                hist = stock.history(period=period, interval=interval)
            if not hist.empty:
                data_dict[name] = hist
        except:
            continue
    return data_dict

def draw_chart(name, df):
    if len(df) > 1:
        color = '#ff4b4b' if df['Close'].iloc[-1] >= df['Close'].iloc[0] else '#4b7bff'
    else:
        color = '#ffffff'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], mode='lines', name=name,
        line=dict(color=color, width=2)
    ))
    
    fig.update_layout(
        title=dict(text=f"{name}", font=dict(color="white", size=12)),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor='#333333', color="white"),
        margin=dict(l=5, r=5, t=25, b=5),
        height=180
    )
    return fig

# ---------------------------------------------------------
# [기능 2] 뉴스 수집 (Google RSS)
# ---------------------------------------------------------
def get_real_news():
    rss_url = "https://news.google.com/rss/search?q=경제+주식+비트코인+미국증시&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(rss_url)
        news_list = []
        for entry in feed.entries[:20]:
            try:
                dt = datetime.datetime(*entry.published_parsed[:6])
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                
            news_list.append({
                "title": entry.title,
                "link": entry.link,
                "publisher": entry.source.title if 'source' in entry else "Google News",
                "time": time_str
            })
        return news_list
    except:
        return []

# ---------------------------------------------------------
# [기능 3] AI 분석
# ---------------------------------------------------------
def get_ai_analysis(market_summary_text):
    model_name = "gemini-pro"
    check_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        check_res = requests.get(check_url)
        if check_res.status_code == 200:
            models = check_res.json().get('models', [])
            for m in models:
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    if 'flash' in m['name']:
                        model_name = m['name']
                        break
                    if 'pro' in m['name']:
                        model_name = m['name']
    except:
        pass 

    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    prompt = f"""
    너는 글로벌 자산운용사 수석 매니저야. 
    아래 시장 데이터를 보고, 40대 투자자를 위한 포트폴리오 관점의 브리핑을 작성해줘.
    [데이터] {market_summary_text}
    [필수 포함] 1. 비트코인 및 암호화폐 방향성 2. 한국/미국 증시 비교 3. '오늘의 투자 포인트' 3가지
    [형식] 중요 숫자는 **볼드체**, 마크다운.
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        if res.status_code == 200:
            return f"✅ **분석 모델: {model_name}**\n\n" + res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ 분석 실패: {res.text}"
    except Exception as e:
        return f"⚠️ 에러: {str(e)}"

# =========================================================
# 메인 화면
# =========================================================

st.sidebar.header("⚙️ 기간 설정")
period_option = st.sidebar.radio("", ('1일', '1개월', '3개월', '1년', '3년'), index=1)

period_map = {'1일': '1d', '1개월': '1mo', '3개월': '3mo', '1년': '1y', '3년': '3y'}
interval_map = {'1일': '30m', '1개월': '1d', '3개월': '1d', '1년': '1d', '3년': '1wk'}

with st.spinner('데이터 동기화 중...'):
    market_data = get_market_data(period_map[period_option], interval_map[period_option])

tab1, tab2, tab3 = st.tabs(["📊 마켓 대시보드", "📰 실시간 뉴스", "🤖 AI 인사이트"])

# [탭 1] 대시보드
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

# [탭 2] 뉴스
with tab2:
    st.markdown("### 🌍 주요 금융 뉴스 (Google News)")
    news_items = get_real_news()
    if news_items:
        for n in news_items:
            st.markdown(f"""
            <div style="background-color: #1E2126; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #FF4B4B; transition: 0.3s;">
                <a href="{n['link']}" target="_blank" class="news-link">
                    <div style="font-size: 16px; font-weight: bold; margin-bottom: 5px; color: #FFFFFF;">
                        {n['title']}
                    </div>
                </a>
                <div style="font-size: 12px; color: #B0B0B0;">
                    <span>📅 {n['time']}</span> | <span>📰 {n['publisher']}</span>
                    <span style="float:right;">
                        <a href="{n['link']}" target="_blank" style="color: #FF4B4B; text-decoration: none;">기사 보기 🔗</a>
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("뉴스를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.")

# [탭 3] AI 분석
with tab3:
    st.markdown("### 🚀 AI 마켓 인텔리전스")
    st.info("실시간 데이터를 바탕으로 AI가 시장 흐름을 분석합니다.")
    if st.button("AI 브리핑 생성하기"):
        with st.spinner("분석 리포트 작성 중..."):
            summary_txt = ""
            for name, df in market_data.items():
                if not df.empty:
                    summary_txt += f"{name}: {df['Close'].iloc[-1]:.2f}\n"
            report = get_ai_analysis(summary_txt)
            st.markdown(report)
