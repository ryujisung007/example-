# app.py
# Streamlit dashboard MVP for "2018 요르단 개황(2018.12).pdf"
# - Extracts key indicators (capital, area, population, GDP, trade, unemployment, sector shares)
# - Shows KPI cards + charts + extracted text table
#
# Run:
#   streamlit run app.py
#
# Requirements:
#   streamlit, pdfplumber, pandas, matplotlib

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, Dict, Any, List

import pandas as pd
import pdfplumber
import streamlit as st
import matplotlib.pyplot as plt


DEFAULT_PDF_PATH = "/mnt/data/2018 요르단 개황(2018.12).pdf"


# ----------------------------
# Utilities
# ----------------------------
def safe_float(x: str) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def parse_korean_amount_to_usd_billion(text: str) -> Optional[float]:
    """
    Parse strings like:
      "74억 9천만" -> 7.49 (USD billion)
      "204억 6천만" -> 20.46 (USD billion)
      "400억" -> 40.0 (USD billion)
    Assumption: unit is USD, and "억 달러" base.
      - 1억 달러 = 0.1 billion USD
      - 1천만 달러 = 0.01 billion USD
    """
    text = text.replace(",", "").strip()

    # e.g., "74억 9천만"
    m = re.search(r"(\d+)\s*억(?:\s*(\d+)\s*천만)?", text)
    if not m:
        return None

    eok = int(m.group(1))  # 억 달러
    cheonman = int(m.group(2)) if m.group(2) else 0  # 천만 달러

    # Convert to USD billion
    # eok * 0.1 + cheonman * 0.01
    return round(eok * 0.1 + cheonman * 0.01, 4)


def format_optional(value: Any, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value}{suffix}"


# ----------------------------
# Extraction model
# ----------------------------
@dataclass
class JordanIndicators:
    country_name: Optional[str] = None
    capital: Optional[str] = None
    capital_population_hint: Optional[str] = None

    area_km2: Optional[int] = None
    population_million: Optional[float] = None  # national population (million)

    language: Optional[str] = None
    religion: Optional[str] = None
    government_form: Optional[str] = None

    gdp_year: Optional[int] = None
    gdp_usd_billion: Optional[float] = None

    gdp_per_capita_year: Optional[int] = None
    gdp_per_capita_usd: Optional[int] = None

    real_gdp_growth_year: Optional[int] = None
    real_gdp_growth_pct: Optional[float] = None

    trade_year: Optional[int] = None
    export_usd_billion: Optional[float] = None
    import_usd_billion: Optional[float] = None

    unemployment_year: Optional[int] = None
    unemployment_pct: Optional[float] = None
    youth_unemployment_pct: Optional[float] = None

    # sector shares (from text: "금융·부동산·통신 및 공공 서비스 ... 제조업 ... ICT ... 농업 ...")
    sector_fin_public_pct: Optional[float] = None
    sector_manufacturing_pct: Optional[float] = None
    sector_ict_pct: Optional[float] = None
    sector_agri_pct_range: Optional[str] = None  # keep "3~4" as range text

    def trade_balance_usd_billion(self) -> Optional[float]:
        if self.export_usd_billion is None or self.import_usd_billion is None:
            return None
        return round(self.export_usd_billion - self.import_usd_billion, 4)


@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_bytes: Optional[bytes], file_path: Optional[str]) -> str:
    text_all: List[str] = []
    if file_bytes is not None:
        with pdfplumber.open(file_bytes) as pdf:
            for p in pdf.pages:
                text_all.append(p.extract_text() or "")
    else:
        if not file_path:
            return ""
        with pdfplumber.open(file_path) as pdf:
            for p in pdf.pages:
                text_all.append(p.extract_text() or "")
    return "\n".join(text_all)


def extract_indicators(text: str) -> JordanIndicators:
    ind = JordanIndicators()

    # Country name
    m = re.search(r"국\s*명\s*:\s*(.+)", text)
    if m:
        ind.country_name = m.group(1).strip()

    # Capital: "수 도 : 암만(Amman, 인구 약 400만 명)"
    m = re.search(r"수\s*도\s*:\s*([^\(\n]+)\(([^)\n]+)\)", text)
    if m:
        ind.capital = m.group(1).strip()
        ind.capital_population_hint = m.group(2).strip()

    # Area: "면 적 : 89,342km2"
    m = re.search(r"면\s*적\s*:\s*([\d,]+)\s*km2", text)
    if m:
        ind.area_km2 = int(m.group(1).replace(",", ""))

    # Population: "인 구 : 약 661만 명"
    m = re.search(r"인\s*구\s*:\s*약\s*([\d,]+)\s*만\s*명", text)
    if m:
        # 만명 -> million
        val_man = int(m.group(1).replace(",", ""))
        # 1만명 = 0.01 million
        ind.population_million = round(val_man * 0.01, 4)

    # Language: "언 어 : 아랍어(영 어도 통용)"
    m = re.search(r"언\s*어\s*:\s*(.+)", text)
    if m:
        ind.language = m.group(1).strip()

    # Religion: "종 교 : ..."
    m = re.search(r"종\s*교\s*:\s*(.+)", text)
    if m:
        ind.religion = m.group(1).strip()

    # Government form: "국가 형태 : 입헌군주국"
    m = re.search(r"국가\s*형태\s*:\s*(.+)", text)
    if m:
        ind.government_form = m.group(1).strip()

    # GDP: "- GDP : 400억 달러(2017)"
    m = re.search(r"GDP\s*:\s*([\d,]+\s*억(?:\s*\d+\s*천만)?)\s*달러\((\d{4})\)", text)
    if m:
        ind.gdp_usd_billion = parse_korean_amount_to_usd_billion(m.group(1))
        ind.gdp_year = int(m.group(2))

    # GDP per capita: "/ 1인당 GDP : 3,980달러(2017, 세계은행)"
    m = re.search(r"1인당\s*GDP\s*:\s*([\d,]+)\s*달\w*\s*\(?(?:(\d{4}))?", text)
    if m:
        ind.gdp_per_capita_usd = int(m.group(1).replace(",", ""))
        if m.group(2):
            ind.gdp_per_capita_year = int(m.group(2))

    # Real GDP growth: "- 실질 GDP 성장률 : 2.14(%2017)"
    m = re.search(r"실질\s*GDP\s*성장률\s*:\s*([\d\.]+)\s*\(%\s*(\d{4})\)", text)
    if not m:
        # fallback pattern: "2.14(%2017)" without spaces
        m = re.search(r"실질\s*GDP\s*성장률\s*:\s*([\d\.]+)\s*\(%(\d{4})\)", text)
    if m:
        ind.real_gdp_growth_pct = safe_float(m.group(1))
        ind.real_gdp_growth_year = int(m.group(2))

    # Trade: "수출 74억 9천만 달러(2017), 수입 204억 6천만 달러(2017)"
    m = re.search(
        r"수출\s*([\d,]+\s*억(?:\s*\d+\s*천만)?)\s*달러\((\d{4})\)\s*,\s*수입\s*([\d,]+\s*억(?:\s*\d+\s*천만)?)\s*달러\((\d{4})\)",
        text
    )
    if m:
        ind.export_usd_billion = parse_korean_amount_to_usd_billion(m.group(1))
        ind.import_usd_billion = parse_korean_amount_to_usd_billion(m.group(3))
        # years should match; keep the first
        ind.trade_year = int(m.group(2))

    # Unemployment: "- 실업률 : 18.5%(2017) (청년실업률은 30%)"
    m = re.search(r"실업률\s*:\s*([\d\.]+)%\((\d{4})\)", text)
    if m:
        ind.unemployment_pct = safe_float(m.group(1))
        ind.unemployment_year = int(m.group(2))
        my = re.search(r"청년실업률[은는]\s*([\d\.]+)%", text)
        if my:
            ind.youth_unemployment_pct = safe_float(my.group(1))

    # Sector shares:
    # "금 융·부동산·통신 및 공공 서비스가 전체 GDP의 약 51%, 제조업은 GDP의 19%, ICT 14%, 농업은 3~4% 차지"
    m = re.search(
        r"전체\s*GDP의\s*약\s*([\d\.]+)%.*?제조업은\s*GDP의\s*([\d\.]+)%\s*,\s*ICT\s*([\d\.]+)%\s*,\s*농업은\s*([0-9~\.\-]+)%",
        text
    )
    if m:
        ind.sector_fin_public_pct = safe_float(m.group(1))
        ind.sector_manufacturing_pct = safe_float(m.group(2))
        ind.sector_ict_pct = safe_float(m.group(3))
        ind.sector_agri_pct_range = m.group(4).strip()

    return ind


def build_kpi_table(ind: JordanIndicators) -> pd.DataFrame:
    rows = [
        ("Country name (국명)", ind.country_name),
        ("Capital (수도)", ind.capital),
        ("Capital population hint (수도 인구 힌트)", ind.capital_population_hint),
        ("Area km² (면적)", ind.area_km2),
        ("Population (million, 인구)", ind.population_million),
        ("Language (언어)", ind.language),
        ("Religion (종교)", ind.religion),
        ("Government form (국가 형태)", ind.government_form),
        ("GDP year", ind.gdp_year),
        ("GDP (USD bn)", ind.gdp_usd_billion),
        ("GDP per capita year", ind.gdp_per_capita_year),
        ("GDP per capita (USD)", ind.gdp_per_capita_usd),
        ("Real GDP growth year", ind.real_gdp_growth_year),
        ("Real GDP growth (%)", ind.real_gdp_growth_pct),
        ("Trade year", ind.trade_year),
        ("Export (USD bn)", ind.export_usd_billion),
        ("Import (USD bn)", ind.import_usd_billion),
        ("Trade balance (USD bn)", ind.trade_balance_usd_billion()),
        ("Unemployment year", ind.unemployment_year),
        ("Unemployment (%)", ind.unemployment_pct),
        ("Youth unemployment (%)", ind.youth_unemployment_pct),
        ("Sector: Fin/RE/Telecom/Public (%)", ind.sector_fin_public_pct),
        ("Sector: Manufacturing (%)", ind.sector_manufacturing_pct),
        ("Sector: ICT (%)", ind.sector_ict_pct),
        ("Sector: Agriculture (% range)", ind.sector_agri_pct_range),
    ]
    return pd.DataFrame(rows, columns=["Item", "Value"])


def plot_trade(ind: JordanIndicators):
    if ind.export_usd_billion is None or ind.import_usd_billion is None:
        st.info("Trade (수출/수입) 값을 추출하지 못해서 그래프를 생략했어요.")
        return

    df = pd.DataFrame(
        {
            "Type": ["Export (수출)", "Import (수입)", "Balance (수지)"],
            "USD_bn": [
                ind.export_usd_billion,
                ind.import_usd_billion,
                ind.trade_balance_usd_billion() or 0.0,
            ],
        }
    )

    fig = plt.figure()
    plt.bar(df["Type"], df["USD_bn"])
    plt.ylabel("USD (billion)")
    plt.title(f"Trade (교역) — {ind.trade_year or 'N/A'}")
    st.pyplot(fig, clear_figure=True)


def plot_sectors(ind: JordanIndicators):
    if (
        ind.sector_fin_public_pct is None
        or ind.sector_manufacturing_pct is None
        or ind.sector_ict_pct is None
        or ind.sector_agri_pct_range is None
    ):
        st.info("Sector share (산업 비중) 값을 추출하지 못해서 그래프를 생략했어요.")
        return

    # Agriculture range -> midpoint for plotting, keep text separately
    agri_mid = None
    m = re.match(r"(\d+(?:\.\d+)?)\s*~\s*(\d+(?:\.\d+)?)", ind.sector_agri_pct_range)
    if m:
        a = float(m.group(1))
        b = float(m.group(2))
        agri_mid = (a + b) / 2.0
    else:
        agri_mid = safe_float(ind.sector_agri_pct_range)

    parts = [
        ("Fin/RE/Telecom/Public (금융·부동산·통신·공공)", ind.sector_fin_public_pct),
        ("Manufacturing (제조업)", ind.sector_manufacturing_pct),
        ("ICT", ind.sector_ict_pct),
        ("Agriculture (농업)", agri_mid if agri_mid is not None else 0.0),
    ]
    total = sum(v for _, v in parts if v is not None)
    other = max(0.0, 100.0 - total)
    parts.append(("Other (기타)", other))

    labels = [p[0] for p in parts]
    values = [p[1] for p in parts]

    fig = plt.figure()
    plt.pie(values, labels=labels, autopct="%1.1f%%")
    plt.title("Sector shares (경제 구조: 비중)")
    st.pyplot(fig, clear_figure=True)

    st.caption(f"Agriculture range in text (농업 비중 원문 범위): {ind.sector_agri_pct_range}%")


# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Jordan 2018 Dashboard", layout="wide")

st.title("Jordan Country Brief Dashboard (요르단 개황 대시보드) — MVP")

with st.sidebar:
    st.header("Input (입력)")
    uploaded = st.file_uploader("PDF 업로드 (선택)", type=["pdf"])
    use_default = st.checkbox("기본 경로 PDF 사용", value=(uploaded is None))
    pdf_path = DEFAULT_PDF_PATH if use_default else None

    st.markdown("---")
    st.subheader("Display options (표시 옵션)")
    show_raw_text = st.checkbox("원문 텍스트 일부 보기", value=False)
    raw_preview_chars = st.slider("원문 미리보기 글자수", 500, 5000, 1500, step=250)

    st.markdown("---")
    st.caption("Tip: PDF가 레이아웃/띄어쓰기 때문에 추출이 불안정할 수 있어요. "
               "그럴 땐 '추출 규칙(정규식)'을 조금 조정하면 안정화됩니다.")


# Load text
file_bytes = uploaded.read() if uploaded is not None else None
text = extract_text_from_pdf(file_bytes=file_bytes, file_path=pdf_path)

if not text.strip():
    st.error("PDF 텍스트를 읽지 못했어요. PDF를 업로드하거나, 기본 경로를 확인해 주세요.")
    st.stop()

# Extract
ind = extract_indicators(text)

# Layout
col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("KPI (핵심 지표)")
    k1, k2, k3, k4 = st.columns(4)

    k1.metric("GDP (USD bn)", format_optional(ind.gdp_usd_billion), help=f"Year: {ind.gdp_year}")
    k2.metric("GDP per capita (USD)", format_optional(ind.gdp_per_capita_usd), help=f"Year: {ind.gdp_per_capita_year}")
    k3.metric("Unemployment (%)", format_optional(ind.unemployment_pct), help=f"Year: {ind.unemployment_year}")
    k4.metric("Trade balance (USD bn)", format_optional(ind.trade_balance_usd_billion()), help=f"Year: {ind.trade_year}")

    st.markdown("### Country profile (국가 프로필)")
    p1, p2, p3 = st.columns(3)
    p1.write(f"**Country (국명):** {ind.country_name or 'N/A'}")
    p1.write(f"**Capital (수도):** {ind.capital or 'N/A'}")
    if ind.capital_population_hint:
        p1.write(f"**Capital hint:** {ind.capital_population_hint}")

    p2.write(f"**Area (면적):** {format_optional(ind.area_km2, ' km²')}")
    p2.write(f"**Population (인구):** {format_optional(ind.population_million, ' million')}")

    p3.write(f"**Language (언어):** {ind.language or 'N/A'}")
    p3.write(f"**Religion (종교):** {ind.religion or 'N/A'}")
    p3.write(f"**Government (체제):** {ind.government_form or 'N/A'}")

    if ind.youth_unemployment_pct is not None:
        st.info(f"Youth unemployment (청년실업률): {ind.youth_unemployment_pct}%")

with col2:
    st.subheader("Charts (차트)")
    st.markdown("#### Trade (교역: 수출/수입/수지)")
    plot_trade(ind)

    st.markdown("#### Sector shares (산업 비중)")
    plot_sectors(ind)

st.markdown("---")
st.subheader("Extracted fields table (추출 결과 테이블)")
df_kpi = build_kpi_table(ind)
st.dataframe(df_kpi, use_container_width=True)

if show_raw_text:
    st.markdown("---")
    st.subheader("Raw text preview (원문 텍스트 미리보기)")
    st.text(text[:raw_preview_chars])
