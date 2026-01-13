import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go
import requests
import json
import xml.etree.ElementTree as ET # 내장 라이브러리 (별도 설치 불필요)

# 1. 페이지 설정
st.set_page_config(page_title="Pro 경제 대시보드 v3.0", layout="wide", page_icon="📈")

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
api_key = "AIzaSyAEe4RzV2O63ZnwKrBdSk_UCmVsIn_sjIo"

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
# [기능 2] 뉴스 수집 (Requests + XML 파싱 직접 구현)
# ---------------------------------------------------------
def get_real_news():
    # 구글 뉴스 RSS (한국 금융)
    rss_url = "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRDgwQ0lzZ3BeRVJ5Y3R5Z0J5Z0pFLAo?hl=ko&gl=KR&ceid=KR%3Ako"
    
    # [핵심] 브라우저인 척 속이는 헤더 (차단 방지)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    news_list = []
    try:
        response = requests.get(rss_url, headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # XML 파싱
            for item in root.findall('.//item')[:15]:
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('pubDate').text
                source = item.find('source').text if item.find('source') is not None else "Google News"
                
                # 날짜 포맷 정리 (간단하게)
                try:
                    # pubDate 예: Tue, 13 Jan 2026 05:00:00 GMT
                    time_str = pubDate.split(" +")[0]
                except:
                    time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

                news_list.append({
                    "title": title, "publisher": source, "link": link, "time": time_str
                })
    except Exception as e:
        # 에러 발생 시 빈 리스트 반환 (화면에 에러 로그 대신 '뉴스 없음' 표시)
        return []
        
    return news_list

# ---------------------------------------------------------
# [기능 3] AI 분석 (REST API 직접 호출 - 라이브러리 미사용)
# ---------------------------------------------------------
def get_ai_analysis(market_summary_text):
    if not api_key:
        return "⚠️ 오류: Google API 키가 입력되지 않았습니다."

    # [수정] 라이브러리 대신 HTTP 요청을 직접 보냅니다. (가장 확실한 방법)
    # 모델: gemini-1.5-flash (2026년 기준 표준 모델)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    
    prompt_text = f"""
    당신은 월스트리트의 수석 투자 전략가입니다. 아래 시장 데이터를 바탕으로 전문적인 브리핑을 작성하세요.

    [현재 시장 데이터]
    {market_summary_text}

    [작성 가이드]
    1. **시장 동향 요약**: 코스피, 미국 증시, 암호화폐 간의 상관관계를 분석하세요.
    2. **핵심 원인 분석**: 현재 상승 또는 하락을 이끄는 거시경제적 요인(환율, 금리 등)을 추론하세요.
    3. **투자 전략**: 보수적 투자자와 공격적 투자자를 위한 대응 전략을 각각 한 줄로 제시하세요.
    4. 중요 숫자는 **볼드체**로 표시하고, 가독성 높은 마크다운 형식을 사용하세요.
    """
    
    data = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        if response.status_code == 200:
            result = response.json()
            return f"✅ **Gemini Market Insight (v1.5 Flash)**\n\n" + result['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ **분석 실패 (HTTP {response.status_code})**: {response.text}"
            
    except Exception as e:
        return f"⚠️ **연결 오류**: {str(e)}"

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
    st.subheader("🌍 주요 뉴스 피드 (Google Finance RSS)")
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
        st.warning("뉴스를 가져오는데 실패했습니다. (Google 차단 또는 네트워크 문제)")

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
