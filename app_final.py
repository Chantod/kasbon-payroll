import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date
import plotly.express as px
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from supabase import create_client

st.set_page_config(page_title="Kasbon Payroll Enterprise", layout="wide")

# ================== SUPABASE ==================
url = st.secrets["https://rcvljirmzgiwikflcafj.supabase.co"]
key = st.secrets["sb_publishable_7ZaOZM35gyZ4eVw4HIbXAg_Dtlc7xgx"]
supabase = create_client(url, key)

# ================== DATA KARYAWAN ==================
karyawan_data = {
    "Hana": {"pin": "1234", "limit": 3000000},
    "Tuje": {"pin": "2222", "limit": 3000000},
    "Icha": {"pin": "3333", "limit": 2500000},
    "Fikri": {"pin": "4444", "limit": 1900000},
    "Iki": {"pin": "5555", "limit": 1600000},
    "Lia": {"pin": "6666", "limit": 1500000},
    "Dhafa": {"pin": "7777", "limit": 1500000},
}

OWNER_PASSWORD = "torch123"

# ================== FUNGSI PERIODE ==================
def get_periode(tgl):
    tgl = pd.to_datetime(tgl)
    if tgl.day >= 25:
        start = datetime(tgl.year, tgl.month, 25)
        if tgl.month == 12:
            end = datetime(tgl.year + 1, 1, 24)
        else:
            end = datetime(tgl.year, tgl.month + 1, 24)
    else:
        if tgl.month == 1:
            start = datetime(tgl.year - 1, 12, 25)
        else:
            start = datetime(tgl.year, tgl.month - 1, 25)
        end = datetime(tgl.year, tgl.month, 24)
    return f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}"

# ================== LOAD DATA ==================
def load_data():
    data = supabase.table("kasbon").select("*").execute()
    df = pd.DataFrame(data.data)
    if not df.empty:
        df["Tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    return df

# ================== LOGIN ==================
if "login" not in st.session_state:
    st.session_state.login = None

st.title("💰 Sistem Kasbon Payroll Enterprise")

if st.session_state.login is None:
    role = st.selectbox("Login sebagai", ["Karyawan", "Owner"])

    if role == "Karyawan":
        nama = st.selectbox("Pilih Nama", list(karyawan_data.keys()))
        pin = st.text_input("PIN", type="password")

        if st.button("Login"):
            if pin == karyawan_data[nama]["pin"]:
                st.session_state.login = ("karyawan", nama)
                st.rerun()
            else:
                st.error("PIN salah")

    else:
        pwd = st.text_input("Password Owner", type="password")
        if st.button("Login"):
            if pwd == OWNER_PASSWORD:
                st.session_state.login = ("owner", "OWNER")
                st.rerun()
            else:
                st.error("Password salah")

# ================== KARYAWAN ==================
elif st.session_state.login[0] == "karyawan":

    nama = st.session_state.login[1]
    limit = karyawan_data[nama]["limit"]

    st.header(f"Kasbon - {nama}")

    tanggal = st.date_input("Tanggal Kasbon", value=date.today())
    nominal = st.selectbox("Nominal", [50000,100000,150000,200000,250000,300000])
    keterangan = st.text_area("Keterangan")

    df = load_data()

    if not df.empty:
        df_periode = df[(df["nama"] == nama)]
        total = df_periode["nominal"].sum()
    else:
        total = 0

    sisa = limit - total
    st.info(f"Sisa Limit Anda: Rp {sisa:,.0f}")

    if st.button("Ajukan Kasbon"):
        if nominal <= sisa:
            supabase.table("kasbon").insert({
                "id": str(uuid.uuid4()),
                "tanggal": tanggal.strftime("%Y-%m-%d"),
                "nama": nama,
                "nominal": nominal,
                "keterangan": keterangan,
                "periode": get_periode(tanggal)
            }).execute()
            st.success("Kasbon berhasil disimpan")
            st.rerun()
        else:
            st.error("Melebihi limit")

    if st.button("Logout"):
        st.session_state.login = None
        st.rerun()

# ================== OWNER ==================
else:

    st.header("📊 Dashboard Owner")

    df = load_data()

    if not df.empty:

        st.subheader("Ringkasan")

        summary = df.groupby("nama")["nominal"].sum().reset_index()

        for i, row in summary.iterrows():
            limit = karyawan_data[row["nama"]]["limit"]
            sisa = limit - row["nominal"]
            st.write(f"{row['nama']} → Total: Rp {row['nominal']:,.0f} | Sisa: Rp {sisa:,.0f}")

        st.subheader("Grafik Kasbon")
        fig = px.bar(summary, x="nama", y="nominal", color="nama")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Data Lengkap")
        st.dataframe(df)

        # ===== PDF Slip =====
        st.subheader("Cetak Slip")

        pilih = st.selectbox("Pilih ID Kasbon", df["id"])

        if st.button("Cetak PDF"):
            row = df[df["id"] == pilih].iloc[0]

            file_name = "slip_kasbon.pdf"
            doc = SimpleDocTemplate(file_name, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("SLIP KASBON", styles["Title"]))
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph(f"Nama: {row['nama']}", styles["Normal"]))
            elements.append(Paragraph(f"Tanggal: {row['tanggal']}", styles["Normal"]))
            elements.append(Paragraph(f"Nominal: Rp {row['nominal']:,.0f}", styles["Normal"]))
            elements.append(Paragraph(f"Keterangan: {row['keterangan']}", styles["Normal"]))
            elements.append(Paragraph(f"Periode: {row['periode']}", styles["Normal"]))

            doc.build(elements)

            with open(file_name, "rb") as f:
                st.download_button("Download Slip PDF", f, file_name)

    else:
        st.info("Belum ada data kasbon")

    if st.button("Logout"):
        st.session_state.login = None
        st.rerun()
