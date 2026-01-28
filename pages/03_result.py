import streamlit as st
import pandas as pd

st.title("📌 요약 결과 및 내보내기")

# 예시 파생지표
derived = {
    "무역 수지 (억 USD)": -13.0,
    "수출입 비율 (X/M)": 0.36,
    "무역의존도 ((X+M)/GDP)": 0.69,
    "실업-성장 간극": 16.4
}

st.markdown("### 📉 파생 지표 요약")
df = pd.DataFrame(derived.items(), columns=["지표", "값"])
st.table(df)

st.markdown("### ⚠️ 리스크 진단")
if derived["수출입 비율 (X/M)"] < 0.5:
    st.warning("수출이 수입의 절반 이하입니다. 무역수지 적자 구조 가능성이 높습니다.")
if derived["실업-성장 간극"] > 10:
    st.warning("경제 성장 대비 실업률이 매우 높아 고용 창출 역부족 상태입니다.")

st.markdown("### ⬇️ 데이터 내보내기")
st.download_button("📥 CSV 다운로드", data=df.to_csv(index=False).encode("utf-8-sig"),
                   file_name="jordan_summary.csv", mime="text/csv")

