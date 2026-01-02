import streamlit as st
import yfinance as yf
import pandas as pd
import requests # 직통 연결을 위한 도구
import datetime
import json

# 1. 페이지 설정
st.set_page_config(page_title="글로벌 경제 대시보드", layout="wide")

st.title(f"🌏 글로벌 마켓 & 경제 브리핑")
st.markdown(f"**{datetime.date.today()}** 기준, 세계 주요 지수 및 AI 분석 리포트입니다.")

# 사이드바에 API 키 입력 확인
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("설정(Secrets)에서 Google API 키를 넣어주세요.")
    st.stop()

# 2. 데이터 수집 함수
@st.cache_data(ttl=3600) 
def get_financial_data():
    tickers = {
        "🇺🇸 S&P 500": "^GSPC",
        "🇯🇵 니케이 225": "^N225",
        "🇨🇳 상해 종합": "000001.SS",
        "🇪🇺 유로 스톡스 50": "^STOXX50E",
        "🇰🇷 원/달러 환율": "KRW=X",
        "🥇 금 선물": "GC=F",
        "🛢️ WTI 원유": "CL=F",
        "🇺🇸 애플 (AAPL)": "AAPL",
        "🇰🇷 삼성전자": "005930.KS",
        "🇹🇼 TSMC": "TSM"
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
                data_list.append({"항목": name, "현재가": current, "등락률": change})
            else:
                data_list.append({"항목": name, "현재가": 0, "등락률": 0})
        except:
            data_list.append({"항목": name, "현재가": 0, "등락률": 0})
            continue
            
    return pd.DataFrame(data_list)

# 3. AI 요약 함수 (requests를 사용한 직통 연결)
def get_ai_summary(df_text):
    # 구글 Gemini API 주소 (gemini-1.5-flash 사용)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # AI에게 보낼 편지 내용
    prompt = f"""
    너는 경제 전문가야. 아래 데이터를 보고 한국인 투자자를 위한 오늘의 경제 뉴스 10가지를 요약해줘.
    특히 환율, 유가, 반도체 대장주(삼성전자, TSMC)의 흐름을 잘 짚어줘.
    
    데이터: {df_text}
    형식: 마크다운, 해요체.
    """
    
    # 데이터 포장
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # 우체통에 넣기 (POST 요청)
        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        
        # 답장 확인
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ 오류 발생 (코드 {response.status_code}): {response.text}"
            
    except Exception as e:
        return f"⚠️ 연결 실패: {str(e)}"

# --- 화면 구성 ---
st.header("📊 주요 지표")
df = get_financial_data()
cols = st.columns(4)
for index, row in df.iterrows():
    with cols[index % 4]:
        st.metric(label=row['항목'], value=f"{row['현재가']:,.2f}", delta=f"{row['등락률']:.2f}%")

st.divider()

st.info("AI 분석 버튼을 누르면 구글 Gemini가 분석을 시작합니다.")
if st.button("AI 리포트 생성"):
    with st.spinner("Gemini가 분석 중..."):
        st.markdown(get_ai_summary(df.to_string()))
