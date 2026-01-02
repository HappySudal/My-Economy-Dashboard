import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import datetime

# 1. 페이지 설정
st.set_page_config(page_title="글로벌 경제 대시보드", layout="wide")

st.title(f"🌏 글로벌 마켓 & 경제 브리핑 (Gemini Ver.)")
st.markdown(f"**{datetime.date.today()}** 기준, 세계 주요 지수, 원자재, 대장주 현황 및 AI 분석 리포트입니다.")

# 사이드바에 API 키 입력
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("설정(Secrets)에서 Google API 키를 넣어주세요.")
    st.stop()

# 구글 Gemini 설정 (모델 변경: flash -> pro)
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro') 

# 2. 데이터 수집 함수 (지수, 환율, 원자재, 대장주)
@st.cache_data(ttl=3600) 
def get_financial_data():
    tickers = {
        # [주요 지수]
        "🇺🇸 S&P 500": "^GSPC",
        "🇯🇵 니케이 225": "^N225",
        "🇨🇳 상해 종합": "000001.SS",
        "🇪🇺 유로 스톡스 50": "^STOXX50E",
        "🇮🇳 인도 Nifty 50": "^NSEI",
        
        # [환율/금리/원자재]
        "🇰🇷 원/달러 환율": "KRW=X",
        "🇺🇸 미국 10년물 국채": "^TNX",
        "🥇 금 선물": "GC=F",
        "🛢️ WTI 원유": "CL=F",
        
        # [각국 대장주]
        "🇺🇸 애플 (AAPL)": "AAPL",
        "🇰🇷 삼성전자": "005930.KS",
        "🇹🇼 TSMC (대만)": "TSM",
        "🇯🇵 토요타": "7203.T",
        "🇨🇳 텐센트 (홍콩)": "0700.HK",
        "🇪🇺 LVMH (루이비통)": "MC.PA",
        "🇮🇳 릴라이언스": "RELIANCE.NS"
    }
    
    data_list = []
    for name, ticker in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if len(hist) > 1:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = ((current - prev) / prev) * 100
                data_list.append({
                    "항목": name, 
                    "현재가": current, 
                    "등락률": change
                })
        except:
            data_list.append({"항목": name, "현재가": 0, "등락률": 0})
            continue
            
    return pd.DataFrame(data_list)

# 3. 구글 Gemini 뉴스 요약 함수
def get_ai_summary(df_text):
    prompt = f"""
    너는 세계 최고의 글로벌 매크로 투자 전략가야. 
    오늘 수집된 전 세계 주요 금융 데이터는 다음과 같아: 
    {df_text}
    
    이 데이터와 현재 인터넷상의 최신 경제 뉴스를 결합해서,
    내 자산 증식에 도움이 될 '오늘의 핵심 경제 뉴스 10선'을 브리핑해줘.
    
    [분석 포인트]
    1. **시장 전반:** 미국, 아시아, 유럽 증시 분위기와 환율/금리 영향
    2. **원자재:** 유가(WTI)와 금값 변동이 시사하는 인플레이션 신호
    3. **핵심 기업:** 애플, 삼성전자, TSMC 등 기술주 및 주요 대장주의 주가 흐름과 관련 뉴스
    4. **신흥국:** 인도 및 중국 시장의 특이사항
    
    [형식]
    - 읽기 편하게 '해요체'를 사용해줘.
    - 중요한 숫자는 **볼드체**로 강조해줘.
    - 마크다운 형식으로 깔끔하게 정리해줘.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"요약 중 오류가 발생했습니다: {str(e)}"

# --- 화면 구성 ---

st.header("📊 주요 시장 및 대장주 현황")
st.caption("※ 데이터 로딩에 몇 초 정도 걸릴 수 있습니다.")

df = get_financial_data()

cols = st.columns(4)
for index, row in df.iterrows():
    col = cols[index % 4]
    with col:
        val_str = f"{row['현재가']:,.2f}"
        st.metric(
            label=row['항목'],
            value=val_str,
            delta=f"{row['등락률']:.2f}%"
        )

st.divider()

st.header("🤖 Gemini 글로벌 마켓 브리핑")
st.info("각국의 지수와 삼성전자, 애플, 유가 등 최신 데이터를 기반으로 분석합니다.")

if st.button("오늘의 경제 리포트 생성 (Google AI)"):
    with st.spinner("Gemini가 주요국 뉴스, 유가, 대장주 흐름을 분석 중입니다..."):
        df_text = df.to_string()
        summary = get_ai_summary(df_text)
        st.markdown(summary)
