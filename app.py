import streamlit as st
import pdfplumber
import io
from pathlib import Path

# 기본 PDF 경로 (상대경로로 작성)
DEFAULT_PDF_PATH = "data/2018_jordan.pdf"

# 텍스트 추출 함수
def extract_text_from_pdf(file_bytes=None, file_path=None):
    if file_bytes is not None:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])

    if file_path is not None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF 파일이 존재하지 않아요: {path.resolve()}")
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])

    raise ValueError("PDF 파일 경로나 업로드 파일이 없습니다.")

# 스트림릿 UI 시작
st.set_page_config(page_title="요르단 개황 대시보드", layout="wide")
st.title("📄 2018 요르단 개황 PDF 분석")

# 사이드바: 파일 업로드 or 기본 PDF 사용
with st.sidebar:
    st.header("📎 PDF 선택")
    uploaded = st.file_uploader("PDF 파일 업로드", type=["pdf"])
    use_default = st.checkbox("기본 PDF 사용 (data/2018_jordan.pdf)", value=uploaded is None)

# PDF 읽기
file_bytes = uploaded.read() if uploaded else None
file_path = DEFAULT_PDF_PATH if use_default else None

try:
    text = extract_text_from_pdf(file_bytes=file_bytes, file_path=file_path)
except FileNotFoundError as e:
    st.error(f"❌ PDF 파일을 찾을 수 없습니다.\n\n{e}")
    st.stop()
except Exception as e:
    st.error(f"❌ PDF 처리 중 오류가 발생했습니다.\n\n{e}")
    st.stop()

# 본문 출력
st.success("✅ PDF에서 텍스트를 성공적으로 추출했습니다!")
st.text_area("📜 PDF 본문 미리보기", text[:3000], height=400)

# 선택적으로 전체 보기
if st.checkbox("전체 텍스트 보기"):
    st.text_area("📄 전체 텍스트", text, height=800)
