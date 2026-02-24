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

# ================= SUPABASE =================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ================= DATA KARYAWAN =================
karyawan_data = {
    "Hana": {"pin": "1234", "limit": 3000000},
    "Tuje": {"pin": "2222", "limit": 3000000},
    "Icha": {"pin": "3333", "limit": 2500000},
    "Fikri": {"pin": "4444", "limit": 1900000},
    "Iki": {"pin": "5555", "limit": 1600000},
    "Lia": {"pin": "6666", "limit": 1500000},
    "Dhafa": {"pin": "7777", "limit": 1500000},
}

OWNER_PASSWORD = "owner123"

# ================= FUNGSI PERIODE =================
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

# ================= LOAD DATA =================
def load_data():
    response = supabase.table("kasbon").select("*").execute()
    if response.data:
        df = pd.DataFrame(response.data)
        df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
        return df
    return pd.DataFrame()

# ================= LOGIN STATE =================
if "login" not in st.session_state:
    st.session_state.login = None

st.title("💰 Sistem Kasbon Payroll Enterprise")

# ================= LOGIN =================
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

# ================= KARYAWAN =================
elif st.session_state.login[0] == "karyawan":

    nama = st.session_state.login[1]
    limit = karyawan_data[nama]["limit"]

    st.header(f"Kasbon - {nama}")

    tanggal = st.date_input("Tanggal Kasbon", value=date.today())
    nominal = st.selectbox("Nominal", [50000,100000,150000,200000,250000,300000])
    keterangan = st.text_area("Keterangan")

    df = load_data()
    total = df[df["nama"] == nama]["nominal"].sum() if not df.empty else 0
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

    st.markdown("---")
    st.subheader("📜 Riwayat Kasbon Anda")

    if not df.empty:
        df_user = df[df["nama"] == nama].sort_values("tanggal", ascending=False)
        if not df_user.empty:
            st.dataframe(
                df_user[["tanggal", "nominal", "keterangan", "periode"]],
                use_container_width=True
            )
        else:
            st.info("Belum ada kasbon")
    else:
        st.info("Belum ada data")

    if st.button("Logout"):
        st.session_state.login = None
        st.rerun()

# ================= OWNER =================
else:

    st.header("📊 Dashboard Owner")

df = load_data()

if df.empty:
    st.info("Belum ada data kasbon")
else:

    # ================= REKAP TOTAL PER NAMA =================
    st.subheader("📌 Rekap Total Kasbon Per Karyawan")

    summary = df.groupby("nama")["nominal"].sum().reset_index()
    summary = summary.sort_values("nominal", ascending=False)

    st.dataframe(summary, use_container_width=True)

    # ================= PILIH NAMA UNTUK DETAIL =================
    st.markdown("---")
    st.subheader("🔎 Detail Riwayat Per Karyawan")

    pilih_nama = st.selectbox("Pilih Karyawan", summary["nama"])

    df_nama = df[df["nama"] == pilih_nama].sort_values("tanggal", ascending=False)

    if not df_nama.empty:
        st.dataframe(
            df_nama[["tanggal", "nominal", "keterangan", "periode"]],
            use_container_width=True
        )

        total_nama = df_nama["nominal"].sum()
        st.success(f"Total Kasbon {pilih_nama}: Rp {total_nama:,.0f}")

        # ================= REKAP PER PERIODE =================
        st.markdown("### 📆 Rekap Per Periode")
        periode_summary = df_nama.groupby("periode")["nominal"].sum().reset_index()
        st.dataframe(periode_summary, use_container_width=True)

    else:
        st.info("Belum ada data untuk karyawan ini")

    # ================= GRAFIK =================
    st.markdown("---")
    st.subheader("📊 Grafik Total Kasbon")

    fig = px.bar(summary, x="nama", y="nominal", color="nama")
    st.plotly_chart(fig, use_container_width=True)

    if df.empty:
        st.info("Belum ada data kasbon")
    else:

        summary = df.groupby("nama")["nominal"].sum().reset_index()

        st.subheader("Ringkasan per Karyawan")
        for i, row in summary.iterrows():
            limit = karyawan_data[row["nama"]]["limit"]
            sisa = limit - row["nominal"]
            st.write(f"{row['nama']} → Total: Rp {row['nominal']:,.0f} | Sisa: Rp {sisa:,.0f}")

        st.subheader("Grafik Kasbon")
        fig = px.bar(summary, x="nama", y="nominal", color="nama")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Data Lengkap")
        st.dataframe(df)

        # HAPUS PER TRANSAKSI
        st.subheader("🗑 Hapus Data")
        pilih_id = st.selectbox("Hapus Per Transaksi", df["id"])
        if st.button("Hapus Transaksi"):
            supabase.table("kasbon").delete().eq("id", pilih_id).execute()
            st.success("Berhasil dihapus")
            st.rerun()

        # HAPUS PER KARYAWAN
        pilih_nama = st.selectbox("Hapus Semua Per Karyawan", df["nama"].unique())
        if st.button("Hapus Semua Data Karyawan"):
            supabase.table("kasbon").delete().eq("nama", pilih_nama).execute()
            st.success("Semua data dihapus")
            st.rerun()

        # RESET SEMUA
        if st.checkbox("⚠ Saya yakin ingin hapus SEMUA data"):
            if st.button("Hapus Semua Data"):
                supabase.table("kasbon").delete().neq("id", "").execute()
                st.success("Semua data berhasil dihapus")
                st.rerun()

        # CETAK PDF
        st.subheader("Cetak Slip PDF")
        pilih = st.selectbox("Pilih ID Slip", df["id"])
        if st.button("Buat PDF"):
            row = df[df["id"] == pilih].iloc[0]
            file_name = "slip_kasbon.pdf"
            doc = SimpleDocTemplate(file_name, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("SLIP KASBON", styles["Title"]))
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph(f"Nama: {row['nama']}", styles["Normal"]))
            elements.append(Paragraph(f"Tanggal: {row['tanggal'].strftime('%d-%m-%Y')}", styles["Normal"]))
            elements.append(Paragraph(f"Nominal: Rp {row['nominal']:,.0f}", styles["Normal"]))
            elements.append(Paragraph(f"Keterangan: {row['keterangan']}", styles["Normal"]))
            elements.append(Paragraph(f"Periode: {row['periode']}", styles["Normal"]))

            doc.build(elements)

            with open(file_name, "rb") as f:
                st.download_button("Download Slip PDF", f, file_name)

    if st.button("Logout"):
        st.session_state.login = None
        st.rerun()

