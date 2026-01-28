import streamlit as st
from pathlib import Path

st.title("📘 2018 요르단 개황 분석 프로젝트")
st.markdown(""
이 앱은 요르단 개황 PDF를 기반으로 국가 거시지표, 산업 구조, 리스크 요인 등을 분석하는 Streamlit 대시보드입니다.
"")

st.header("🔍 분석 대상 PDF")
pdf_path = Path("data/2018_jordan.pdf")
if not pdf_path.exists():
    st.error("PDF 파일이 존재하지 않습니다. `data/2018_jordan.pdf` 경로를 확인해주세요.")
else:
    with open(pdf_path, "rb") as f:
        st.download_button(label="PDF 다운로드", data=f, file_name="2018_jordan.pdf", mime="application/pdf")

    st.markdown("#### 📑 본문 일부 미리보기")
    import pdfplumber
    with pdfplumber.open(str(pdf_path)) as pdf:
        first_page = pdf.pages[0].extract_text()
        st.text_area("첫 페이지 텍스트", value=first_page[:3000], height=400)

