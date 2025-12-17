import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# 데이터 불러오기
# -----------------------------
df = pd.read_excel("data.xlsx", sheet_name="Sheet1", engine="openpyxl")
if "사용연수.1" in df.columns:
    df = df.drop(columns=["사용연수.1"])

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(page_title="위험물탱크 부식률 조회", layout="wide")

st.markdown(
    """
    <style>
    /* 기본값: PC 화면 */
    .main-title {
        text-align: center;
        font-weight: 600;
        margin-bottom: 10px;
        font-size: 2.2rem;   /* PC에서는 큼 */
        line-height: 1.2;
    }

    /* 화면 폭이 900px 이하일 때 (노트북/태블릿) */
    @media (max-width: 900px) {
        .main-title {
            font-size: 1.7rem;
        }
    }

    /* 화면 폭이 600px 이하일 때 (모바일) */
    @media (max-width: 600px) {
        .main-title {
            font-size: 1.4rem;
        }
    }
    </style>

    <div class="main-title">
        위험물탱크 기대수명<br>
        예측 프로그램
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")



# =============================
# 탭 생성
# =============================
tab_query, tab_analysis = st.tabs(["🔎 조회", "📊 결과분석"])

# =============================
# 🔎 조회탭 (지금까지 만든 화면 전부)
# =============================
with tab_query:

    # =============================
    # 상단: ① / ② 나란히 배치
    # =============================
    col_top_left, col_top_right = st.columns(2)

    with col_top_left:
        # -----------------------------
        # ① 조건별 조회
        # -----------------------------
        st.subheader("① 조건별 조회")

        mat_order = df["재질"].value_counts().index.tolist()

        재질 = st.selectbox("재질 선택", mat_order)
        품명 = st.selectbox("품명 선택", sorted(df["품명"].unique()))
        탱크형상 = st.selectbox(
            "탱크형상 선택",
            sorted(df["탱크형상"].unique()),
            index=sorted(df["탱크형상"].unique()).index("고정지붕")
        )
        전기방식 = st.selectbox("전기방식", ["O", "X"], index=1)
        히팅코일 = st.selectbox("히팅코일", ["O", "X"], index=1)
        지역 = st.selectbox(
            "지역 선택",
            sorted(df["지역"].unique()),
            index=sorted(df["지역"].unique()).index("울산")
        )

        # 조건 필터
        cond = (
            (df["재질"] == 재질) &
            (df["품명"] == 품명) &
            (df["탱크형상"] == 탱크형상) &
            (df["전기방식"] == 전기방식) &
            (df["히팅코일"] == 히팅코일) &
            (df["지역"] == 지역)
        )
        filtered = df[cond]

        # 👉 추후 분석탭에서 재사용할 수 있게 저장(선택)
        st.session_state["filtered"] = filtered

        # 분석탭에서 동일조건 비교에 필요한 값 저장
        st.session_state["재질"] = 재질
        st.session_state["품명"] = 품명
        st.session_state["탱크형상"] = 탱크형상
        st.session_state["히팅코일"] = 히팅코일
        st.session_state["지역"] = 지역
        st.session_state["전기방식"] = 전기방식

        # 전체 데이터 저장 (전기방식 비교에 필요)
        st.session_state["full_df"] = df


    with col_top_right:
        # -----------------------------
        # ② 내 탱크 데이터 입력
        # -----------------------------
        st.subheader("② 내 탱크 데이터 입력")

        col1, col2, col3 = st.columns(3)
        with col1:
            설계두께 = st.number_input("설계두께(mm)", min_value=0.0, format="%.2f")
        with col2:
            측정두께 = st.number_input("측정두께(mm)", min_value=0.0, format="%.2f")
        with col3:
            사용연수_내탱크 = st.number_input("내 탱크 사용연수 (년)", min_value=0.0, max_value=100.0, value=10.0)

        내부식률 = None
        if 설계두께 > 0 and 측정두께 > 0 and 사용연수_내탱크 > 0:
            # mm/년
            내부식률 = (설계두께 - 측정두께) / (사용연수_내탱크)
            st.info(f"🧮 내 탱크 계산된 부식률: **{내부식률:.5f} mm/년**")

        # 👉 추후 분석탭에서 재사용할 수 있게 저장(선택)
        st.session_state["내부식률"] = 내부식률
        st.session_state["설계두께"] = 설계두께
        st.session_state["측정두께"] = 측정두께
        st.session_state["사용연수_내탱크"] = 사용연수_내탱크

    st.markdown("---")

    # =============================
    # 중단: ③ / ④ 나란히 배치
    # =============================
    col_mid_left, col_mid_right = st.columns(2)

    # ===============================================================
    # ✅ 수정된 ③ 향후 부식 예측 및 기대수명 (남은기간 제거 + 11년 고정)
    # ===============================================================
    with col_mid_left:
        st.subheader("③ 향후 부식 예측 및 기대수명")

        # 다크 테이블 스타일
        st.markdown("""
            <style>
                .tbl-dark { width:98%; border-collapse:collapse; margin-top:15px; border:1px solid #4b5563; font-size:0.95rem; table-layout:fixed; background-color:#111827; color:#f3f4f6;}
                .tbl-dark th { width:40%; text-align:left; padding:10px; background-color:#1f2937; color:#f9fafb; border-bottom:2px solid #374151; white-space:nowrap;}
                .tbl-dark td { width:60%; padding:8px; color:#f3f4f6; border-bottom:1px solid #374151; background-color:#111827; word-break:keep-all;}
                .tbl-dark tr:nth-child(even) td { background-color:#1f2937;}
                .result-row { font-weight:600;}
            </style>
        """, unsafe_allow_html=True)

        if 설계두께 > 0 and 측정두께 > 0 and 사용연수_내탱크 > 0:

            # 연수구간
            bins = [0, 10, 20, 30, 200]
            labels = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
            내연수_라벨 = pd.cut([사용연수_내탱크], bins=bins, labels=labels, right=False)[0]

            # df에 연수구간 생성
            if "연수구간" not in df.columns:
                df["연수구간"] = pd.cut(df["사용연수"], bins=bins, labels=labels, right=False)

            # 동일 조건 필터
            cond_base = (
                (df["재질"] == 재질) &
                (df["품명"] == 품명) &
                (df["탱크형상"] == 탱크형상) &
                (df["전기방식"] == 전기방식) &
                (df["히팅코일"] == 히팅코일) &
                (df["지역"] == 지역)
            )
            cond_year = (df["연수구간"] == 내연수_라벨)
            filtered_pred = df[cond_base & cond_year]

            # 평균 부식률
            if len(filtered_pred) >= 10:
                평균부식률_조건 = filtered_pred["부식률"].mean()
                표본수 = len(filtered_pred)
            else:
                평균부식률_조건 = df["부식률"].mean()
                표본수 = len(filtered_pred)
                st.warning(f"⚠️ 같은 구간 표본이 {표본수}개로 적어 전체 평균 사용")

            # 산정 방식 선택
            산정방식 = st.selectbox(
                "부식률 산정 방식",
                ["평균", "중위수(P50)", "상위 75% (보수)", "상위 90% (매우 보수)"],
                key="rate_mode_fixed11"
            )

            # 산정 방식에 따른 대표부식률 계산
            if 산정방식 == "평균":
                대표부식률 = 평균부식률_조건
            elif 산정방식 == "중위수(P50)":
                대표부식률 = filtered_pred["부식률"].median() if len(filtered_pred) >= 1 else 평균부식률_조건
            elif 산정방식 == "상위 75% (보수)":
                대표부식률 = filtered_pred["부식률"].quantile(0.75) if len(filtered_pred) >= 1 else 평균부식률_조건
            else:
                대표부식률 = filtered_pred["부식률"].quantile(0.9) if len(filtered_pred) >= 1 else 평균부식률_조건

            # 하한값 보정
            if 대표부식률 < 0.0005:
                대표부식률 = 0.0005

            # -------------------------
            # 🔥 남은기간 = 11년으로 고정
            # -------------------------
            남은기간 = 11

            # 예측 계산
            예상부식량 = 대표부식률 * 남은기간
            예상두께 = 측정두께 - 예상부식량

            # 기대수명 계산
            기대수명 = (측정두께 - 3.2) / 대표부식률 if 대표부식률 > 0 else None
            if 기대수명 and 기대수명 > 100:
                기대수명_text = "11년 이상"
            elif 기대수명 and 기대수명 > 0:
                기대수명_text = f"{기대수명:.1f} 년 남음"
            else:
                기대수명_text = "3.2mm 이하 상태 가능"

            # 판정
            if 예상두께 >= 3.2:
                판정 = "✅ 적합(합격)"
                판정색 = "#065f46"
                판정글 = "#d1fae5"
            else:
                판정 = "⚠️ 부적합(불합격)"
                판정색 = "#7f1d1d"
                판정글 = "#fee2e2"

            # 결과 표 출력
            st.markdown(f"""
                <table class="tbl-dark">
                    <tr><th>항목</th><th>값</th></tr>
                    <tr><td>사용연수 구간</td><td>{내연수_라벨}</td></tr>
                    <tr><td>표본수</td><td>{표본수 if 표본수>=10 else f"{표본수} (전체보정)"} </td></tr>
                    <tr><td>부식률 산정 방식</td><td>{산정방식}</td></tr>
                    <tr><td>대표 부식률</td><td>{대표부식률:.5f} mm/년</td></tr>
                    <tr><td>예상 부식량 (11년)</td><td>{예상부식량:.3f} mm</td></tr>
                    <tr><td>예상 두께 (11년 후)</td><td>{예상두께:.3f} mm</td></tr>
                    <tr class="result-row" style="background-color:{판정색};color:{판정글};">
                        <td>판정 결과</td><td>{판정}</td>
                    </tr>
                    <tr><td>예상 잔여 수명</td><td>{기대수명_text}</td></tr>
                </table>
            """, unsafe_allow_html=True)

    # -----------------------------
    # ④ 조건에 맞는 표본 수 및 연수구간별 부식률표
    # -----------------------------
    with col_mid_right:
        st.subheader("④ 조건에 맞는 표본 수 및 연수구간별 부식률표")

        if len(filtered) < 30:
            st.warning(f"⚠️ 표본 수가 {len(filtered)}개로 너무 적습니다. (최소 30개 이상 필요)")
        else:
            st.success(f"조건에 맞는 표본 수: {len(filtered)}개")

            bins = [0, 10, 20, 30, 200]
            labels = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
            filtered["연수구간"] = pd.cut(filtered["사용연수"], bins=bins, labels=labels, right=False)

            grouped = filtered.groupby("연수구간").agg(
                평균부식률=("부식률", "mean"),
                표본수=("부식률", "count")
            ).reset_index()

            st.dataframe(grouped, use_container_width=True, height=200)

    st.markdown("---")

    # =============================
    # 하단: ⑤ 그래프 비교 (전체 폭)
    # =============================
    st.subheader("⑤ 그래프 비교")

    col_g1, col_g2 = st.columns(2)

    if len(filtered) >= 30:
        with col_g1:
            fig1 = px.bar(
                grouped,
                x="연수구간",
                y="평균부식률",
                text="평균부식률",
                color="평균부식률",
                color_continuous_scale=px.colors.sequential.Viridis,
                title="조건별 사용연수 구간 평균 부식률",
                template="plotly_white"
            )
            ymax = grouped["평균부식률"].max() * 2
            fig1.update_yaxes(range=[0, ymax])
            fig1.update_traces(
                texttemplate="%{text:.4f}<br>(n=%{customdata[0]})",
                textposition="outside",
                customdata=grouped[["표본수"]].values
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col_g2:
            if 내부식률 is not None:
                fig2 = px.histogram(
                    filtered, x="부식률", nbins=20, color_discrete_sequence=["#ff7f0e"],
                    title="같은 조건 표본 분포와 내 탱크 위치", template="plotly_white"
                )
                fig2.add_vline(x=내부식률, line_dash="dash", line_color="red",
                               annotation_text="내 탱크", annotation_position="top left")
                st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # -----------------------------
    # ⑥ 전체 데이터 요약
    # -----------------------------
    st.subheader("⑥ 전체 데이터 요약")

    mat_avg = df.groupby("재질").agg(
        평균부식률=("부식률","mean"),
        표본수=("부식률","count")
    ).reset_index()
    mat_avg = mat_avg[mat_avg["표본수"] >= 300].sort_values("평균부식률")

    bins_all = [0, 10, 20, 30, 200]
    labels_all = ["10년 미만", "10년 이상", "20년 이상", "30년 이상"]
    df["연수구간"] = pd.cut(df["사용연수"], bins=bins_all, labels=labels_all, right=False)

    year_avg = df.groupby("연수구간")["부식률"].mean().reset_index()
    region_avg = df.groupby("지역")["부식률"].mean().reset_index().sort_values("부식률")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.dataframe(mat_avg, use_container_width=True, height=200)
        fig3 = px.bar(
            mat_avg, x="재질", y="평균부식률", color="평균부식률",
            color_continuous_scale=px.colors.sequential.Viridis,
            title="재질별 평균 부식률 (표본≥300)", template="plotly_white"
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        st.dataframe(year_avg, use_container_width=True, height=200)
        fig4 = px.bar(
            year_avg, x="연수구간", y="부식률", color="부식률",
            color_continuous_scale=px.colors.sequential.Viridis,
            title="사용연수 구간별 평균 부식률", template="plotly_white"
        )
        ymax_all = year_avg["부식률"].max() * 2
        fig4.update_yaxes(range=[0, ymax_all])
        st.plotly_chart(fig4, use_container_width=True)

    with col3:
        st.dataframe(region_avg, use_container_width=True, height=200)
        fig5 = px.bar(
            region_avg, x="지역", y="부식률", color="부식률",
            color_continuous_scale=px.colors.sequential.Viridis,
            title="지역별 평균 부식률", template="plotly_white"
        )
        st.plotly_chart(fig5, use_container_width=True)

# =============================
# 📊 분석탭
# =============================
import importlib

with tab_analysis:
    analyze = importlib.import_module("analyze")
    importlib.reload(analyze)

