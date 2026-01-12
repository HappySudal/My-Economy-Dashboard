import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
import json

# 1. 페이지 설정
st.set_page_config(page_title="Pro 경제 대시보드 v2.2", layout="wide", page_icon="📈")

# 2. 커스텀 CSS (폰트 확대, 버튼 스타일, 다크모드, 텍스트 컬러)
st.markdown("""
    <style>
    /* 전체 배경 다크모드 고정 */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* 탭 메뉴 폰트 확대 */
    button[data-baseweb="tab"] div p {
        font-size: 20px !important;
        font-weight: 700 !important;
    }
    
    /* 버튼 스타일링 (빨간색) */
    div.stButton > button {
        background-color: #FF4B4B !important;
        color: white !important;
        font-size: 16px !important;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        width: 100%;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    div.stButton > button:hover {
        background-color: #FF2B2B !important;
        color: white !important;
        border: 1px solid white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title(f"📈 Pro Global Market Dashboard")
st.markdown(f"**{datetime.date.today()}** 기준 | 암호화폐, ETF, 국내외 증시 통합 분석")

# [Session State] AI 리포트 저장소 초기화 (화면 이동 방지용)
if "ai_report" not in st.session_state:
    st.session_state["ai_report"] = ""

# 사이드바: API 키
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Google API Key를 입력하세요", type="password")

# ---------------------------------------------------------
# [기능 1] 데이터 수집
# ---------------------------------------------------------
ASSETS = {
    "🇰🇷 코스피 (KOSPI)": "^KS11",
    "🇰🇷 코스닥 (KOSDAQ)": "^KQ11",
    "🇺🇸 S&P 500": "SPY",
    "🇺🇸 나스닥 100": "QQQ",
    "🪙 비트코인": "BTC-USD",
    "💎 이더리움": "ETH-USD",
    "💵 원/달러 환율": "KRW=X",
    "🥇 금 선물": "GC=F",
    "🛢️ WTI 원유": "CL=F",
    "🇺🇸 미국채 10년": "^TNX",
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

# 차트 그리기
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
        title=dict(text=f"{name}", font=dict(color="white", size=14)),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor='#333333', color="white"),
        margin=dict(l=10, r=10, t=30, b=10),
        height=200
    )
    return fig

# ---------------------------------------------------------
# [기능 2] 뉴스 수집
# ---------------------------------------------------------
def get_real_news():
    news_list = []
    targets = ["^KS11", "SPY", "BTC-USD", "005930.KS"] 
    
    for t in targets:
        try:
            ticker = yf.Ticker(t)
            news = ticker.news
            if news:
                for n in news[:2]:
                    title = n.get('title', '제목 없음')
                    link = n.get('link', '#')
                    publisher = n.get('publisher', 'Unknown')
                    pub_time = n.get('providerPublishTime')
                    if pub_time:
                        time_str = datetime.datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
                    else:
                        time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

                    news_list.append({
                        "title": title, "publisher": publisher, "link": link, "time": time_str
                    })
        except:
            continue
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list[:15]

# ---------------------------------------------------------
# [기능 3] AI 분석 (Gemini)
# ---------------------------------------------------------
def get_ai_analysis(market_summary_text):
    if not api_key:
        return "⚠️ API 키가 설정되지 않았습니다. 사이드바에 키를 입력해주세요."

    model_name = "gemini-pro"
    # 모델 확인 로직 생략(속도 최적화) - 기본 pro 사용
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    prompt = f"""
    너는 글로벌 투자 전문가야. 아래 데이터를 보고 브리핑해줘.
    
    [시장 데이터]
    {market_summary_text}
    
    [요청사항]
    1. 코스피/코스닥 등 한국 시장과 비트코인 흐름을 연결해서 분석할 것.
    2. 상승/하락 원인을 추론하고 투자자 대응 전략을 짧게 제시할 것.
    3. 중요 수치는 볼드체로, 가독성 좋게 마크다운으로 작성해줘.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        if res.status_code == 200:
            return f"✅ **분석 완료 (Model: {model_name})**\n\n" + res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ 분석 실패: {res.text}"
    except Exception as e:
        return f"⚠️ 에러 발생: {str(e)}"

# =========================================================
# 메인 화면 구성
# =========================================================

# 기간 설정
st.sidebar.header("⚙️ 차트 기간 설정")
period_option = st.sidebar.radio("기간 선택", ('1일', '1개월', '3개월', '1년', '3년'), index=1)

period_map = {'1일': '1d', '1개월': '1mo', '3개월': '3mo', '1년': '1y', '3년': '3y'}
interval_map = {'1일': '30m', '1개월': '1d', '3개월': '1d', '1년': '1d', '3년': '1wk'}

with st.spinner('데이터 수집 중...'):
    market_data = get_market_data(period_map[period_option], interval_map[period_option])

# 탭 구성
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

# [탭 3] AI 분석 (수정된 부분)
with tab3:
    st.markdown("### 🚀 AI 마켓 인텔리전스")
    
    # [수정3] 요청하신 텍스트 (흰색 폰트 적용)
    st.markdown("""
    <p style='color: white; font-size: 16px; margin-bottom: 20px;'>
        AI매크로 전략리포트, 환율, 선물, 채권 데이터를 종합하여 시장을 정밀 분석합니다.
    </p>
    """, unsafe_allow_html=True)
    
    # [수정2] 버튼은 한 번만 나오도록 정리됨
    if st.button("AI 마켓 브리핑 생성하기"):
        with st.spinner("Gemini가 시장 데이터를 분석 중입니다..."):
            summary_txt = ""
            for name, df in market_data.items():
                if not df.empty:
                    summary_txt += f"{name}: {df['Close'].iloc[-1]:.2f}\n"
            
            # [수정1] 결과를 session_state에 저장하여 탭 이동(새로고침) 시에도 내용 유지
            result_text = get_ai_analysis(summary_txt)
            st.session_state["ai_report"] = result_text

    # 저장된 리포트가 있으면 화면에 표시 (버튼 눌러서 새로고침 되어도 유지됨)
    if st.session_state["ai_report"]:
        st.markdown("---")
        st.markdown(st.session_state["ai_report"])
