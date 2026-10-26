
# 어제의 박스오피스 — KOBIS 일별 박스오피스 API
# 초보자 안내:
# 1. Streamlit Cloud의 Settings > Secrets에 KOBIS_KEY를 등록합니다.
# 2. 실제 인증키는 코드에 직접 적지 않습니다.
# 3. requirements.txt에 추가 라이브러리를 적습니다.

import datetime
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="어제의 박스오피스", page_icon="🎬", layout="wide")

API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

# 서버 시간대와 관계없이 한국 시간(UTC+9) 기준으로 어제를 계산합니다.
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
yesterday = today_kst - datetime.timedelta(days=1)

st.title("🎬 일별 박스오피스")
st.caption("달력에서 날짜를 선택하세요. 가장 늦게 선택할 수 있는 날짜는 한국 시간 기준 어제입니다.")
selected_date = st.date_input(
    "조회 날짜",
    value=yesterday,
    min_value=datetime.date(2004, 1, 1),
    max_value=yesterday,
    format="YYYY/MM/DD"
)
target_dt = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

# 인증키는 Streamlit 비밀 금고(Secrets)에서만 불러옵니다.
try:
    API_KEY = st.secrets["KOBIS_KEY"]
except Exception:
    st.error("🔐 KOBIS 인증키를 찾을 수 없습니다.")
    st.markdown(
        "Streamlit Cloud의 **Settings → Secrets**에 `KOBIS_KEY`가 등록되어 있는지 확인하세요."
    )
    st.code('KOBIS_KEY = "발급받은_인증키"', language="toml")
    st.stop()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_boxoffice(date_text, api_key):
    """KOBIS API를 호출해 JSON 응답을 가져옵니다."""
    response = requests.get(
        API_URL,
        params={"key": api_key, "targetDt": date_text},
        timeout=20
    )
    response.raise_for_status()
    return response.json()


# 요청 실패 시 빈 화면 대신 원인과 확인 방법을 표시합니다.
try:
    with st.spinner("KOBIS에서 데이터를 불러오는 중입니다..."):
        data = fetch_boxoffice(target_dt, str(API_KEY).strip())
except requests.exceptions.Timeout:
    st.error("⏱️ KOBIS 서버 응답 시간이 초과되었습니다.")
    st.info("인터넷 연결을 확인하고 잠시 후 새로고침해 주세요.")
    st.stop()
except requests.exceptions.HTTPError as error:
    st.error("🌐 KOBIS 서버가 HTTP 오류를 반환했습니다.")
    st.write(f"오류 내용: {error}")
    st.info("KOBIS 서비스 상태와 요청 주소를 확인해 주세요.")
    st.stop()
except requests.exceptions.RequestException as error:
    st.error("🌐 KOBIS 서버에 연결하지 못했습니다.")
    st.write(f"오류 내용: {error}")
    st.info("인터넷 연결, 방화벽, KOBIS API 서비스 상태를 확인해 주세요.")
    st.stop()
except ValueError:
    st.error("📦 KOBIS 응답을 JSON으로 읽지 못했습니다.")
    st.info("잠시 후 다시 시도하거나 KOBIS API 상태를 확인해 주세요.")
    st.stop()
except Exception as error:
    st.error("예상하지 못한 문제가 발생했습니다.")
    st.write(f"오류 내용: {error}")
    st.info("앱 설정과 실행 로그를 확인해 주세요.")
    st.stop()

# 인증키가 틀려도 HTTP 상태코드가 200일 수 있으므로 faultInfo를 확인합니다.
if not isinstance(data, dict):
    st.error("KOBIS에서 예상한 형식의 데이터를 받지 못했습니다.")
    st.info("잠시 후 다시 시도하고 KOBIS API 응답을 확인해 주세요.")
    st.stop()

if "faultInfo" in data:
    fault = data.get("faultInfo") or {}
    if isinstance(fault, dict):
        code = fault.get("errorCode", "정보 없음")
        message = fault.get("message", "오류 메시지가 없습니다.")
    else:
        code, message = "정보 없음", str(fault)
    st.error("🚨 KOBIS API가 오류 정보를 반환했습니다.")
    st.write(f"오류 코드: {code}")
    st.write(f"오류 메시지: {message}")
    st.markdown(
        "**확인할 사항:** Secrets의 이름이 `KOBIS_KEY`인지, 인증키가 올바른지, "
        "조회 날짜가 `YYYYMMDD` 형식인지 확인하세요."
    )
    st.stop()

boxoffice_result = data.get("boxOfficeResult", {})
if not isinstance(boxoffice_result, dict):
    boxoffice_result = {}
movies = boxoffice_result.get("dailyBoxOfficeList", [])

if not movies:
    st.warning("📭 그날은 아직 집계 전입니다.")
    st.info(
        "KOBIS에서 해당 날짜의 박스오피스 집계를 완료했는지 확인해 주세요. "
        "날짜를 다시 선택하거나 잠시 후 새로고침할 수 있습니다."
    )
    st.stop()

df = pd.DataFrame(movies)

# 필요한 항목이 응답에 있는지 먼저 확인합니다.
required = ["rank", "rankInten", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
missing = [column for column in required if column not in df.columns]
if missing:
    st.error("KOBIS 응답에 필요한 항목이 없습니다: " + ", ".join(missing))
    st.info("KOBIS API 응답 구조가 변경되었는지 공식 문서를 확인해 주세요.")
    st.stop()

# 숫자가 문자열로 오므로 정수로 변환합니다.
for column in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]:
    df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)

df["movieNm"] = df["movieNm"].fillna("영화명 없음").astype(str)
df["openDt"] = df["openDt"].fillna("-").replace("", "-").astype(str)

# 누적 관객수가 100만 명을 초과한 영화명에는 트로피 이모지를 붙입니다.
df["표시 영화명"] = df.apply(
    lambda row: f"{row['movieNm']} 🏆" if row["audiAcc"] > 1_000_000 else row["movieNm"],
    axis=1
)

# 전일 대비 순위 변동: 양수는 상승(빨간 ↑), 음수는 하락(파란 ↓)입니다.
def format_rank_change(value):
    if value > 0:
        return f"↑ {value}"
    if value < 0:
        return f"↓ {abs(value)}"
    return "— 0"

df["순위 변동"] = df["rankInten"].map(format_rank_change)
df = df.sort_values("rank").reset_index(drop=True)

# 1위 영화의 주요 지표 세 가지를 크게 보여 줍니다.
first = df.iloc[0]
st.subheader(f"🥇 {display_date} 1위 — {first['표시 영화명']}")
c1, c2, c3 = st.columns(3)
c1.metric("관객수", f"{first['audiCnt']:,}명")
c2.metric("누적 관객수", f"{first['audiAcc']:,}명")
c3.metric("스크린수", f"{first['scrnCnt']:,}개")

# 순위 변동을 색으로 구분해 표에 표시합니다.
st.subheader("📋 박스오피스 순위")
table = df[["rank", "순위 변동", "표시 영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
table.columns = ["순위", "전일 대비", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
for column in ["관객수", "누적관객", "스크린수"]:
    table[column] = table[column].map(lambda value: f"{value:,}")

def color_rank_change(value):
    if isinstance(value, str) and value.startswith("↑"):
        return "color: #e53935; font-weight: bold;"
    if isinstance(value, str) and value.startswith("↓"):
        return "color: #1976d2; font-weight: bold;"
    return "color: #777777;"

st.dataframe(
    table.style.map(color_rank_change, subset=["전일 대비"]),
    hide_index=True,
    use_container_width=True
)

# 관객수 상위 5편을 막대그래프로 표시합니다.
st.subheader("📊 관객수 상위 5편")
top5 = df.nlargest(5, "audiCnt").sort_values("audiCnt", ascending=True)
chart = px.bar(
    top5,
    x="audiCnt",
    y="표시 영화명",
    orientation="h",
    labels={"audiCnt": "관객수(명)", "표시 영화명": "영화명"},
    text="audiCnt"
)
chart.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
chart.update_layout(
    yaxis_title="",
    xaxis_title="관객수(명)",
    margin=dict(l=10, r=40, t=20, b=10)
)
st.plotly_chart(chart, use_container_width=True)

st.caption("데이터 출처: 영화관입장권통합전산망(KOBIS) 일별 박스오피스 API")
  
