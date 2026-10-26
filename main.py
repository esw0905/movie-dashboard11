import datetime
import pandas as pd
import requests
import streamlit as st
import pytz

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 제목
# -----------------------------------------------------------------------------
st.set_page_config(page_title="일별 박스오피스 순위", page_icon="🎬", layout="wide")

st.title("🎬 일별 박스오피스 순위 검색")
st.caption("KOBIS(영화관입장권통합전산망) 공식 Open API 데이터입니다.")


# -----------------------------------------------------------------------------
# 2. 날짜 선택 (한국 시간 KST 기준 어제까지만 선택 허용)
# Streamlit Cloud 서버 시계와 무관하게 Asia/Seoul 기준으로 날짜를 다룹니다.
# -----------------------------------------------------------------------------
seoul_tz = pytz.timezone("Asia/Seoul")
now_in_seoul = datetime.datetime.now(seoul_tz).date()
max_allowed_date = now_in_seoul - datetime.timedelta(days=1)  # KST 기준 어제

# 사이드바에서 조회 날짜를 선택할 수 있게 배치합니다.
selected_date = st.sidebar.date_input(
    label="📅 조회 날짜 선택",
    value=max_allowed_date,           # 기본값: 어제
    max_value=max_allowed_date,       # 오늘 이후 날짜 선택 방지
    help="오늘 데이터는 집계 전이므로 어제 날짜까지만 조회할 수 있습니다."
)

target_dt = selected_date.strftime("%Y%m%d")  # KOBIS API 입력 형식: YYYYMMDD

st.info(f"📅 **조회 일자:** {selected_date.strftime('%Y년 %m월 %d일')}")


# -----------------------------------------------------------------------------
# 3. KOBIS API 인증키 불러오기 (Secrets 사용)
# -----------------------------------------------------------------------------
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("🔒 **인증키가 설정되지 않았습니다.**")
    st.warning(
        """
    **해결 방법:**
    Streamlit Cloud 설정의 **Secrets** 항목에 `KOBIS_KEY`를 등록해 주세요.
    ```toml
    KOBIS_KEY = "발급받은_KOBIS_API_키"
    ```
    """
    )
    st.stop()

url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {"key": api_key, "targetDt": target_dt}


# -----------------------------------------------------------------------------
# 4. API 요청 및 데이터 처리/오류 처리
# -----------------------------------------------------------------------------
try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException as e:
    st.error("🌐 **KOBIS API 서버 연결에 실패했습니다.**")
    st.write(f"오류 상세: `{e}`")
    st.stop()

# 인증키 오류 발생 처리 (KOBIS는 키가 틀려도 200 OK를 던지고 faultInfo 전달)
if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ **API 인증키 오류가 발생했습니다.**")
    st.warning(f"메시지: {fault.get('message', '알 수 없는 오류')}")
    st.stop()

# 응답 안에서 dailyBoxOfficeList 추출
boxoffice_result = data.get("boxOfficeResult", {})
daily_list = boxoffice_result.get("dailyBoxOfficeList", [])

# 선택한 날짜의 데이터가 비어 있는 경우 지정된 메시지 출력
if not daily_list:
    st.warning("⚠️ **그날은 아직 집계 전입니다.**")
    st.info("다른 날짜를 선택하시거나 잠시 후 다시 시도해 주세요.")
    st.stop()


# -----------------------------------------------------------------------------
# 5. 데이터 가공 및 변환 (문자열 -> 숫자 및 기호 변환)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

# 문자열 숫자를 정수형(int)으로 안전하게 변환
numeric_columns = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# 순위 오름차순 정렬
df = df.sort_values(by="rank")

# [기능 추가 1] 누적관객 100만 명 이상 영화에 트로피 이모지(🏆) 붙이기
def add_trophy(row):
    movie_name = row["movieNm"]
    if row["audiAcc"] >= 1_000_000:
        return f"{movie_name} 🏆"
    return movie_name

df["display_movieNm"] = df.apply(add_trophy, axis=1)

# [기능 추가 2] 전날 대비 순위 증감(rankInten) 화살표 기호 표시
def format_rank_change(inten):
    if inten > 0:
        return f"🔺 {inten}"  # 순위 상승 (양수): 빨간 위 화살표
    elif inten < 0:
        return f"🔹 {abs(inten)}"  # 순위 하락 (음수): 파란 아래 화살표
    else:
        return "-"  # 변동 없음

df["rank_change"] = df["rankInten"].apply(format_rank_change)


# -----------------------------------------------------------------------------
# 6. 1위 영화 지표 카드 3개
# -----------------------------------------------------------------------------
top_1 = df.iloc[0]

st.subheader(f"🥇 1위 영화: {top_1['display_movieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="일별 관객수",
        value=f"{top_1['audiCnt']:,} 명",
        delta=top_1["rank_change"]
    )
with col2:
    st.metric(label="누적 관객수", value=f"{top_1['audiAcc']:,} 명")
with col3:
    st.metric(label="스크린수", value=f"{top_1['scrnCnt']:,} 개")

st.divider()


# -----------------------------------------------------------------------------
# 7. 관객수 상위 5편 막대그래프
# -----------------------------------------------------------------------------
st.subheader("📊 관객수 상위 5개 영화")
top_5_df = df.head(5).copy()

# 시각화용 막대그래프 (x축: 표시용 영화명, y축: 관객수)
st.bar_chart(data=top_5_df, x="display_movieNm", y="audiCnt")

st.divider()


# -----------------------------------------------------------------------------
# 8. 전체 박스오피스 순위 표(Table) 출력
# -----------------------------------------------------------------------------
st.subheader("📋 전체 순위 목록")

# 표에 보여줄 컬럼 선택 및 열 이름 변경
display_df = df[
    ["rank", "rank_change", "display_movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()

display_df.columns = [
    "순위",
    "순위 변동",
    "영화명",
    "개봉일",
    "당일 관객수",
    "누적 관객수",
    "스크린수",
]

# 숫자에 천 단위 쉼표(,) 포맷팅하여 출력
st.dataframe(
    display_df.style.format(
        {"당일 관객수": "{:,}", "누적 관객수": "{:,}", "스크린수": "{:,}"}
    ),
    use_container_width=True,
    hide_index=True,
)
