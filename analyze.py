import streamlit as st
import pandas as pd
import plotly.express as px

st.markdown("### 📈 분석탭 실행됨")
st.write("이곳은 analyze.py 파일에서 렌더링된 내용입니다.")

# 예시: test.py에서 저장된 데이터 접근
filtered = st.session_state.get("filtered")
내부식률 = st.session_state.get("내부식률")

if filtered is not None:
    st.write(f"📊 조회탭에서 가져온 표본 수: {len(filtered)}")
else:
    st.warning("조회탭에서 데이터를 먼저 선택하세요!")

# 예시 그래프
if filtered is not None and len(filtered) > 0:
    fig = px.histogram(filtered, x="부식률", nbins=20, title="분석탭 예시 히스토그램")
    st.plotly_chart(fig)
