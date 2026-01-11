import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
import json  # [수정5] 에러 해결을 위해 import 추가

# 1. 페이지 설정
st.set_page_config(page_title="Pro 경제 대시보드 v2.1", layout="wide", page_icon="📈")

# 2. 커스텀 CSS (폰트 확대, 버튼 스타일, 다크모드)
st.markdown("""
    <style>
    /* 전체 배경 다크모드 고정 */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* [수정1] 탭 메뉴 폰트 확대 (15px 이상) */
    button[data-baseweb="tab"] div p {
        font-size: 20px !important;
        font-weight: 700 !important;
    }
    
    /* [수정4] 버튼이 잘 보이도록 강제 스타일링 */
    div.stButton > button {
        background-color: #FF4B4B !important;
        color: white !important;
        font-size: 16px !important;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        width: 100%;
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

# 사이드바: API 키
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("설정(Secrets)에서 Google API 키를 넣어주세요.")
    st.stop()

# ---------------------------------------------------------
# [기능 1] 데이터 수집 및 차트 (종목 추가 및 배열 변경)
# ---------------------------------------------------------

# [수정2] 코스피, 코스닥 포함한 자산 리스트
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

# 차트 그리기 함수
def draw_chart(name, df):
    # 색상 결정 (한국식: 상승=빨강, 하락=파랑)
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
        xaxis=dict(showgrid=False, showticklabels=False), # X축 간소화
        yaxis=dict(showgrid=True, gridcolor='#333333', color="white"),
        margin=dict(l=10, r=10, t=30, b=10),
        height=200 # 차트 높이 조정
    )
    return fig

# ---------------------------------------------------------
# [기능 2] 뉴스 수집 함수 (버그 수정됨)
# ---------------------------------------------------------
def get_real_news():
    news_list = []
    # 뉴스 검색용 티커 (대표성 있는 것들)
    targets = ["^KS11", "SPY", "BTC-USD", "005930.KS"] 
    
    for t in targets:
        try:
            ticker = yf.Ticker(t)
            news = ticker.news
            if news:
                for n in news[:2]: # 종목당 2개씩
                    # [수정3] 뉴스 데이터 파싱 안전장치 추가
                    title = n.get('title', '제목 없음')
                    link = n.get('link', '#')
                    publisher = n.get('publisher', 'Unknown')
                    
                    # 시간 변환 로직 수정
                    pub_time = n.get('providerPublishTime')
                    if pub_time:
                        time_str = datetime.datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
                    else:
                        time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

                    # 중복 제거를 위해 리스트에 추가
                    news_list.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                        "time": time_str
                    })
        except:
            continue
            
    # 최신순 정렬 (날짜 문자열 기준 역순)
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list[:15] # 최대 15개만 표시

# ---------------------------------------------------------
# [기능 3] AI 분석 함수 (JSON 에러 수정됨)
# ---------------------------------------------------------
def get_ai_analysis(market_summary_text):
    # [수정5] json 모듈 사용을 위해 상단에 import json 추가 완료
    
    # 1. 사용 가능한 모델 찾기
    model_name = "gemini-pro" # 기본값
    check_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        check_res = requests.get(check_url)
        if check_res.status_code == 200:
            models = check_res.json().get('models', [])
            for m in models:
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    # flash 모델 우선, 없으면 pro
                    if 'flash' in m['name']:
                        model_name = m['name']
                        break
                    if 'pro' in m['name']:
                        model_name = m['name']
    except:
        pass # 실패하면 gemini-pro 사용

    # 2. 분석 요청
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
            return f"✅ **분석 모델: {model_name}**\n\n" + res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ 분석 실패: {res.text}"
    except Exception as e:
        return f"⚠️ 에러 발생: {str(e)}"

# =========================================================
# 메인 화면
# =========================================================

# 상단: 기간 선택
st.sidebar.header("⚙️ 차트 기간 설정")
period_option = st.sidebar.radio("기간 선택", ('1일', '1개월', '3개월', '1년', '3년'), index=1)

period_map = {'1일': '1d', '1개월': '1mo', '3개월': '3mo', '1년': '1y', '3년': '3y'}
interval_map = {'1일': '30m', '1개월': '1d', '3개월': '1d', '1년': '1d', '3년': '1wk'}

with st.spinner('데이터 수집 중...'):
    market_data = get_market_data(period_map[period_option], interval_map[period_option])

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 마켓 대시보드", "📰 실시간 뉴스", "🤖 AI 인사이트"])

# [탭 1] 대시보드 (4열 배열 수정)
with tab1:
    # [수정3] 4개 열 생성
    cols = st.columns(4) 
    
    idx = 0
    for name, df in market_data.items():
        if len(df) > 0:
            curr = df['Close'].iloc[-1]
            prev = df['Close'].iloc[0]
            pct = ((curr - prev) / prev) * 100
            
            # 4열로 순차적 배치 (idx % 4)
            with cols[idx % 4]:
                st.metric(label=name, value=f"{curr:,.2f}", delta=f"{pct:.2f}%")
                st.plotly_chart(draw_chart(name, df), use_container_width=True)
                st.divider() # 구분선
            idx += 1

# [탭 2] 뉴스
with tab2:
    st.subheader("🌍 주요 뉴스 피드")
    news_items = get_real_news()
    
    if news_items:
        for n in news_items:
            # 뉴스 카드 디자인
            st.markdown(f"""
            <div style="background-color: #262730; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 5px solid #FF4B4B;">
                <a href="{n['link']}" target="_blank" style="text-decoration: none; color: #FAFAFA;">
                    <h4 style="margin:0; font-size:18px;">{n['title']}</h4>
                </a>
                <div style="color: #A0A0A0; margin-top: 8px; font-size: 14px;">
                    <span>📅 {n['time']}</span> | <span>📰 {n['publisher']}</span>
                    <span style="float:right;"><a href="{n['link']}" target="_blank" style="color:#FF4B4B;">기사 원문 ></a></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("표시할 최신 뉴스가 없습니다.")

# [탭 3] AI 분석
with tab3:
    st.markdown("### 🚀 AI 마켓 인텔리전스")
    st.info("현재 차트 데이터를 기반으로 Gemini가 시장을 분석합니다.")
    
    # [수정4] CSS로 버튼 강제 스타일링 완료 (빨간색 배경)
    if st.button("AI 마켓 브리핑 생성하기"):
        with st.spinner("데이터 분석 및 리포트 작성 중..."):
            summary_txt = ""
            for name, df in market_data.items():
                if not df.empty:
                    summary_txt += f"{name}: 현재 {df['Close'].iloc[-1]:.2f} (변동률 반영)\n"
            
            report = get_ai_analysis(summary_txt)
            st.markdown(report)
