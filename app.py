import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 설정 (Dark Mode 친화적)
st.set_page_config(page_title="Pro 경제 대시보드 v2.0", layout="wide", page_icon="📈")

# Streamlit 스타일 커스텀 (강제 다크모드 느낌)
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* 탭 글씨 크기 키우기 */
    button[data-baseweb="tab"] {
        font-size: 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title(f"📈 Pro Global Market Dashboard")
st.markdown(f"**{datetime.date.today()}** 기준 | 암호화폐, ETF, 주요지수 통합 분석")

# 사이드바: API 키 및 설정
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("설정(Secrets)에서 Google API 키를 넣어주세요.")
    st.stop()

# ---------------------------------------------------------
# [기능 1] 데이터 수집 및 차트 그리기 함수
# ---------------------------------------------------------

# 종목 리스트 정의 (이름: 티커)
ASSETS = {
    "🇺🇸 S&P 500 (SPY)": "SPY",
    "🇺🇸 나스닥 100 (QQQ)": "QQQ",
    "🪙 비트코인 (BTC)": "BTC-USD",
    "💎 이더리움 (ETH)": "ETH-USD",
    "🇰🇷 원/달러 환율": "KRW=X",
    "🥇 금 선물": "GC=F",
    "🛢️ WTI 원유": "CL=F",
    "🇺🇸 미국채 10년물": "^TNX",
    "🏢 삼성전자": "005930.KS",
    "🍎 애플 (AAPL)": "AAPL",
    "🇹🇼 TSMC": "TSM"
}

@st.cache_data(ttl=300) # 5분마다 갱신
def get_market_data(period="1mo", interval="1d"):
    data_dict = {}
    for name, ticker in ASSETS.items():
        try:
            stock = yf.Ticker(ticker)
            # 1일 데이터는 분 단위로, 나머지는 일 단위로
            if period == "1d":
                hist = stock.history(period="1d", interval="30m")
            else:
                hist = stock.history(period=period, interval=interval)
            
            if not hist.empty:
                data_dict[name] = hist
        except:
            continue
    return data_dict

# 차트 그리기 함수 (Plotly 사용)
def draw_chart(name, df):
    # 등락에 따른 색상 결정 (상승: 빨강, 하락: 파랑 - 한국식 / 미국식은 반대지만 한국인에 맞춤)
    if len(df) > 1:
        color = '#ff4b4b' if df['Close'].iloc[-1] >= df['Close'].iloc[0] else '#4b7bff'
    else:
        color = '#ffffff'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        mode='lines', 
        name=name,
        line=dict(color=color, width=2)
    ))
    
    # 차트 디자인 (검은 배경)
    fig.update_layout(
        title=dict(text=f"{name} 추이", font=dict(color="white")),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color="white"),
        yaxis=dict(showgrid=True, gridcolor='#333333', color="white"),
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    return fig

# ---------------------------------------------------------
# [기능 2] 뉴스 수집 함수 (링크 포함)
# ---------------------------------------------------------
def get_real_news():
    news_list = []
    # 뉴스 검색용 주요 티커 몇 개만 선정
    targets = ["SPY", "BTC-USD", "AAPL", "005930.KS"] 
    
    for t in targets:
        try:
            ticker = yf.Ticker(t)
            news = ticker.news
            if news:
                for n in news[:2]: # 종목당 최신 2개만
                    news_list.append({
                        "title": n.get('title'),
                        "publisher": n.get('publisher'),
                        "link": n.get('link'),
                        "time": datetime.datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M')
                    })
        except:
            continue
    return news_list

# ---------------------------------------------------------
# [기능 3] AI 요약 함수 (이전과 동일하지만 강화됨)
# ---------------------------------------------------------
def get_ai_analysis(market_summary_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    prompt = f"""
    너는 억만장자 펀드매니저야. 아래 시장 데이터를 보고 브리핑해줘.
    
    [시장 데이터]
    {market_summary_text}
    
    [요청사항]
    1. 비트코인/이더리움 등 암호화폐 흐름과 ETF(SPY, QQQ) 동향을 꼭 포함할 것.
    2. 전체적인 시장 분위기(Risk On/Off)를 판단해줘.
    3. 말투는 전문가스럽게, 마크다운으로 작성해줘.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return "AI 분석 실패"
    except Exception as e:
        return f"에러: {str(e)}"

# =========================================================
# 메인 화면 구성
# =========================================================

# 1. 기간 선택 버튼 (상단 배치)
st.sidebar.header("⚙️ 차트 설정")
period_option = st.sidebar.radio(
    "조회 기간 선택", 
    ('1일', '1개월', '3개월', '1년', '3년'),
    index=1
)

# 선택에 따른 yfinance 파라미터 변환
period_map = {'1일': '1d', '1개월': '1mo', '3개월': '3mo', '1년': '1y', '3년': '3y'}
interval_map = {'1일': '30m', '1개월': '1d', '3개월': '1d', '1년': '1d', '3년': '1wk'}

selected_period = period_map[period_option]
selected_interval = interval_map[period_option]

# 2. 데이터 로딩
with st.spinner('글로벌 시장 데이터를 긁어오는 중입니다...'):
    market_data = get_market_data(selected_period, selected_interval)

# 3. 탭 구성 (대시보드 / 뉴스 / AI 분석)
tab1, tab2, tab3 = st.tabs(["📊 마켓 대시보드", "📰 실시간 뉴스", "🤖 AI 인사이트"])

# [탭 1] 차트 대시보드
with tab1:
    # 2열로 배치
    col1, col2 = st.columns(2)
    
    idx = 0
    for name, df in market_data.items():
        # 현재가와 등락률 계산
        if len(df) > 0:
            curr_price = df['Close'].iloc[-1]
            if len(df) > 1:
                prev_price = df['Close'].iloc[0] # 기간 내 시가 기준 등락
                pct_change = ((curr_price - prev_price) / prev_price) * 100
            else:
                pct_change = 0.0
            
            # 메트릭 표시 + 차트
            container = col1 if idx % 2 == 0 else col2
            with container:
                st.metric(label=name, value=f"{curr_price:,.2f}", delta=f"{pct_change:.2f}%")
                st.plotly_chart(draw_chart(name, df), use_container_width=True)
                st.divider()
            idx += 1

# [탭 2] 실시간 뉴스 (클릭 가능)
with tab2:
    st.subheader("🌍 주요 외신 헤드라인 (Yahoo Finance)")
    news_items = get_real_news()
    
    if news_items:
        for n in news_items:
            # 클릭 가능한 카드 형태로 표시
            st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #FF4B4B;">
                <a href="{n['link']}" target="_blank" style="text-decoration: none; color: white;">
                    <h4 style="margin:0;">{n['title']}</h4>
                </a>
                <p style="color: gray; margin-top: 5px; font-size: 0.9em;">
                    {n['publisher']} | {n['time']} <a href="{n['link']}" target="_blank">🔗 기사 원문 보기</a>
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("현재 가져올 최신 뉴스가 없습니다.")

# [탭 3] AI 분석
with tab3:
    if st.button("🚀 AI 마켓 브리핑 생성하기"):
        with st.spinner("Gemini가 차트를 분석하고 있습니다..."):
            # 요약용 데이터 텍스트 생성
            summary_txt = ""
            for name, df in market_data.items():
                if not df.empty:
                    summary_txt += f"{name}: 현재가 {df['Close'].iloc[-1]:.2f}\n"
            
            report = get_ai_analysis(summary_txt)
            st.markdown(report)
