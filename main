import datetime
import pandas as pd
import requests
import streamlit as st
import pytz

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 제목 표시
# -----------------------------------------------------------------------------
st.set_page_config(page_title="어제 박스오피스 순위", page_icon="🎬", layout="wide")

st.title("🎬 어제의 박스오피스 순위")
st.caption("KOBIS(영화관입장권통합전산망) 공식 Open API를 통해 집계된 순위입니다.")


# -----------------------------------------------------------------------------
# 2. 날짜 계산 (한국 시간 기준 '어제')
# Streamlit Cloud 서버는 해외 시계(UTC)를 사용할 수 있으므로 Asia/Seoul로 고정합니다.
# -----------------------------------------------------------------------------
seoul_tz = pytz.timezone("Asia/Seoul")
now_in_seoul = datetime.datetime.now(seoul_tz)
yesterday = now_in_seoul - datetime.timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")  # KOBIS 형식: YYYYMMDD (예: 20261025)

st.info(
    f"📅 **조회 기준일:** {yesterday.strftime('%Y년 %m월 %d일')} (한국 시간 기준 어제)"
)


# -----------------------------------------------------------------------------
# 3. KOBIS API 인증키 불러오기 및 주소 설정
# Secrets에 등록된 KOBIS_KEY를 읽어옵니다.
# -----------------------------------------------------------------------------
try:
    api_key = st.secrets["KOBIS_KEY"]
except KeyError:
    st.error("🔒 **인증키가 설정되지 않았습니다.**")
    st.warning(
        """
    **해결 방법:**
    1. Streamlit Cloud 설정의 **Secrets** 항목에 들어갑니다.
    2. 아래와 같이 KOBIS 인증키를 추가해 주세요.
    ```toml
    KOBIS_KEY = "발급받은_KOBIS_API_키"
    ```
    """
    )
    st.stop()  # 키가 없으면 아래 코드를 실행하지 않고 중단합니다.

url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {"key": api_key, "targetDt": target_dt}


# -----------------------------------------------------------------------------
# 4. API 데이터 요청 및 오류 예외 처리
# -----------------------------------------------------------------------------
try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # HTTP 오류(404, 500 등)가 발생하면 예외를 던집니다.
    data = response.json()
except requests.exceptions.RequestException as e:
    st.error("🌐 **KOBIS API 서버 연결에 실패했습니다.**")
    st.write(f"오류 내용: `{e}`")
    st.info("💡 인터넷 연결 상태나 KOBIS 서버 상태를 확인해 주세요.")
    st.stop()

# KOBIS API는 키가 틀려도 200 OK를 응답하고 내부에 'faultInfo'를 전달합니다.
if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ **API 인증키 오류가 발생했습니다.**")
    st.warning(
        f"""
    * **오류 메시지:** {fault.get('message', '알 수 없는 오류')}
    * **오류 코드:** {fault.get('errorCode', 'N/A')}

    💡 `secrets.toml`에 입력한 `KOBIS_KEY`가 정확한지 확인해 주세요.
    """
    )
    st.stop()

# 정상 응답 안에서 영화 목록 데이터 추출
boxoffice_result = data.get("boxOfficeResult", {})
daily_list = boxoffice_result.get("dailyBoxOfficeList", [])

# 영화 목록이 비어 있는 경우 처리
if not daily_list:
    st.warning("⚠️ **어제의 박스오피스 데이터가 비어 있습니다.**")
    st.info(
        """
    **확인사항:**
    * KOBIS 점검 시간이거나 아직 데이터 집계가 완료되지 않았을 수 있습니다.
    * 잠시 후 다시 시도해 주세요.
    """
    )
    st.stop()


# -----------------------------------------------------------------------------
# 5. 데이터 가공 및 변환 (문자열 -> 숫자 변환)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

# KOBIS API는 숫자를 문자열로 전달하므로 정수형으로 변환합니다.
numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# 순위 순서대로 정렬
df = df.sort_values(by="rank")


# -----------------------------------------------------------------------------
# 6. 1위 영화 지표 카드 3개 표시
# -----------------------------------------------------------------------------
top_1 = df.iloc[0]

st.subheader(f"🥇 어제 박스오피스 1위: {top_1['movieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="일별 관객수", value=f"{top_1['audiCnt']:,} 명", delta=top_1["rankInten"]
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

# 막대그래프 차트 출력 (x축: 영화명, y축: 관객수)
st.bar_chart(data=top_5_df, x="movieNm", y="audiCnt")

st.divider()


# -----------------------------------------------------------------------------
# 8. 전체 박스오피스 순위 표(Table) 출력
# -----------------------------------------------------------------------------
st.subheader("📋 전체 순위 목록")

# 필요한 컬럼선택 및 이름 변경
display_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()
display_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "어제 관객수",
    "누적 관객수",
    "스크린수",
]

# 숫자에 천 단위 쉼표(,) 적용하여 보여주기
st.dataframe(
    display_df.style.format(
        {"어제 관객수": "{:,}", "누적 관객수": "{:,}", "스크린수": "{:,}"}
    ),
    use_container_width=True,
    hide_index=True,
)
