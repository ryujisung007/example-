import streamlit as st
import pdfplumber
import re
from pathlib import Path

st.title("📊 요르단 주요 경제 지표 분석")

# PDF 읽기
pdf_path = Path("data/2018_jordan.pdf")
if not pdf_path.exists():
    st.error("PDF 파일을 찾을 수 없습니다.")
    st.stop()

with pdfplumber.open(str(pdf_path)) as pdf:
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)

# 정규식 기반 지표 추출
def extract_value(pattern, text, group=1, cast_type=float):
    match = re.search(pattern, text)
    if match:
        try:
            return cast_type(match.group(group).replace(",", ""))
        except:
            return None
    return None

gdp = extract_value(r"GDP\s*:\s*([\d,]+)\s*억", text)
growth = extract_value(r"실질\s*GDP\s*성장률\s*:\s*([\d\.]+)", text)
unemp = extract_value(r"실업률\s*:\s*([\d\.]+)%", text)

# KPI 표시
c1, c2, c3 = st.columns(3)
c1.metric("💰 GDP (억 USD)", f"{gdp or 'N/A'}")
c2.metric("📈 성장률 (%)", f"{growth or 'N/A'}")
c3.metric("📉 실업률 (%)", f"{unemp or 'N/A'}")

st.markdown("#### 전체 본문 보기")
with st.expander("PDF 전체 텍스트 열기"):
    st.text_area("텍스트", value=text[:10000], height=400)

