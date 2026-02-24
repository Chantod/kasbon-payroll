import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import uuid
import plotly.express as px
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
import shutil

st.set_page_config(page_title="Kasbon Payroll Enterprise", layout="wide")

# ================= CONFIG =================

OWNER_PASSWORD = "owner123"

EMPLOYEES = {
    "Budi": {"pin": "1111", "limit": 2000000},
    "Andi": {"pin": "2222", "limit": 1500000},
    "Siti": {"pin": "3333", "limit": 1000000},
}

DATA_FILE = "kasbon_data.csv"
BACKUP_FILE = "kasbon_backup.csv"

# ================= SAFE LOAD DATA =================

def safe_load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
        except:
            st.error("File CSV rusak. Membuat file baru.")
            return pd.DataFrame(columns=["ID","Tanggal","Nama","Nominal","Keterangan"])
    else:
        return pd.DataFrame(columns=["ID","Tanggal","Nama","Nominal","Keterangan"])

    # Pastikan kolom wajib ada
    required_cols = ["ID","Tanggal","Nama","Nominal","Keterangan"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Convert tanggal aman
    df["Tanggal"] = pd.to_datetime(
        df["Tanggal"],
        format="mixed",
        errors="coerce"
    )

    # Hapus baris tanggal rusak
    df = df.dropna(subset=["Tanggal"])

    # Convert nominal aman
    df["Nominal"] = pd.to_numeric(df["Nominal"], errors="coerce").fillna(0)

    return df

def backup_data():
    if os.path.exists(DATA_FILE):
        shutil.copy(DATA_FILE, BACKUP_FILE)

df = safe_load_data()

# ================= UTIL =================

def format_rp(x):
    return f"Rp {x:,.0f}".replace(",", ".")

def get_periode(tanggal):
    tanggal = pd.to_datetime(tanggal)

    if tanggal.day >= 25:
        start = tanggal.replace(day=25)
        end = (start + pd.DateOffset(months=1)).replace(day=24)
    else:
        start = (tanggal - pd.DateOffset(months=1)).replace(day=25)
        end = tanggal.replace(day=24)

    return f"{start.strftime('%Y-%m-%d')} s/d {end.strftime('%Y-%m-%d')}"

# ================= SESSION =================

if "role" not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# ================= LOGIN =================

if st.session_state.role is None:

    st.title("🔐 Sistem Kasbon Payroll Enterprise")

    mode = st.radio("Login sebagai:", ["Karyawan", "Owner"])

    if mode == "Karyawan":
        nama = st.selectbox("Nama", list(EMPLOYEES.keys()))
        pin = st.text_input("PIN", type="password")

        if st.button("Login"):
            if EMPLOYEES[nama]["pin"] == pin:
                st.session_state.role = "karyawan"
                st.session_state.user = nama
                st.rerun()
            else:
                st.error("PIN salah")

    if mode == "Owner":
        password = st.text_input("Password Owner", type="password")
        if st.button("Login Owner"):
            if password == OWNER_PASSWORD:
                st.session_state.role = "owner"
                st.rerun()
            else:
                st.error("Password salah")

# ================= KARYAWAN =================

elif st.session_state.role == "karyawan":

    nama = st.session_state.user
    limit = EMPLOYEES[nama]["limit"]

    st.title(f"💳 Kasbon - {nama}")

    tanggal = st.date_input(
        "Tanggal Kasbon",
        value=date.today(),
        max_value=date.today()
    )

    periode_ini = get_periode(tanggal)

    pilihan_nominal = list(range(50000, 300001, 50000))
    nominal = st.selectbox(
        "Nominal",
        pilihan_nominal,
        format_func=lambda x: format_rp(x)
    )

    keterangan = st.text_area("Keterangan")

    if not df.empty:
        df["Periode"] = df["Tanggal"].apply(get_periode)
        total_periode = df[
            (df["Nama"] == nama) &
            (df["Periode"] == periode_ini)
        ]["Nominal"].sum()
    else:
        total_periode = 0

    sisa = limit - total_periode

    st.info(f"Periode: {periode_ini}")
    st.write(f"Limit: {format_rp(limit)}")
    st.write(f"Terpakai: {format_rp(total_periode)}")
    st.write(f"Sisa: {format_rp(sisa)}")

    if st.button("Simpan Kasbon"):

        if nominal > sisa:
            st.error("Melebihi limit periode ini")
        else:
            backup_data()

            new_row = {
                "ID": str(uuid.uuid4())[:8],
                "Tanggal": str(tanggal),
                "Nama": nama,
                "Nominal": nominal,
                "Keterangan": keterangan
            }

            df.loc[len(df)] = new_row
            df.to_csv(DATA_FILE, index=False)
            st.success("Kasbon berhasil disimpan")
            st.rerun()

    st.divider()

    if not df.empty:
        st.subheader("Riwayat Periode Ini")
        st.dataframe(
            df[
                (df["Nama"] == nama) &
                (df["Tanggal"].apply(get_periode) == periode_ini)
            ].sort_values("Tanggal", ascending=False),
            use_container_width=True
        )

    if st.button("Logout"):
        st.session_state.role = None
        st.session_state.user = None
        st.rerun()

# ================= OWNER =================

elif st.session_state.role == "owner":

    st.title("📊 Dashboard Payroll Owner")

    if df.empty:
        st.info("Belum ada data kasbon")
    else:

        df["Periode"] = df["Tanggal"].apply(get_periode)

        pilih_periode = st.selectbox(
            "Pilih Periode Payroll",
            sorted(df["Periode"].unique())
        )

        df_periode = df[df["Periode"] == pilih_periode]

        col1, col2 = st.columns(2)
        col1.metric("Total Kasbon", format_rp(df_periode["Nominal"].sum()))
        col2.metric("Jumlah Transaksi", len(df_periode))

        st.divider()

        grafik = df_periode.groupby("Nama")["Nominal"].sum().reset_index()

        if not grafik.empty:
            fig = px.bar(
                grafik,
                x="Nama",
                y="Nominal",
                color="Nama",
                text="Nominal",
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("Rekap Limit")

        data_limit = []
        for nama in EMPLOYEES:
            total = df_periode[df_periode["Nama"] == nama]["Nominal"].sum()
            limit = EMPLOYEES[nama]["limit"]
            sisa = limit - total

            data_limit.append({
                "Nama": nama,
                "Limit": format_rp(limit),
                "Terpakai": format_rp(total),
                "Sisa": format_rp(sisa)
            })

        st.dataframe(pd.DataFrame(data_limit), use_container_width=True)

        st.divider()

        st.subheader("Cetak Slip")
        slip_id = st.text_input("Masukkan ID")

        if slip_id:
            slip = df[df["ID"] == slip_id]
            if not slip.empty:
                s = slip.iloc[0]
                pdf_path = f"slip_{slip_id}.pdf"

                doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                elements = []
                styles = getSampleStyleSheet()

                elements.append(Paragraph("SLIP KASBON", styles["Title"]))
                elements.append(Spacer(1, 0.5 * inch))
                elements.append(Paragraph(f"ID: {s['ID']}", styles["Normal"]))
                elements.append(Paragraph(f"Nama: {s['Nama']}", styles["Normal"]))
                elements.append(Paragraph(f"Tanggal: {s['Tanggal']}", styles["Normal"]))
                elements.append(Paragraph(f"Nominal: {format_rp(s['Nominal'])}", styles["Normal"]))
                elements.append(Paragraph(f"Keterangan: {s['Keterangan']}", styles["Normal"]))

                doc.build(elements)

                with open(pdf_path, "rb") as f:
                    st.download_button("Download Slip PDF", f, file_name=pdf_path)

        st.divider()

        st.dataframe(df_periode.sort_values("Tanggal", ascending=False),
                     use_container_width=True)

    if st.button("Logout"):
        st.session_state.role = None
        st.rerun()