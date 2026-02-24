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
    "Hana": {"pin": "1111", "limit": 3000000},
    "Tuje": {"pin": "2222", "limit": 3000000},
    "Icha": {"pin": "3333", "limit": 2200000},
    "Fikri": {"pin": "4444", "limit": 1900000},
    "Iki": {"pin": "5555", "limit": 1600000},
    "Lia": {"pin": "6666", "limit": 1500000},
    "Dhafa": {"pin": "7777", "limit": 1500000},
}

OWNER_PASSWORD = "owner123"

# ================= PERIODE FUNCTION =================
def get_periode(tgl):
    tgl = pd.to_datetime(tgl)
    if tgl.day >= 25:
        start = datetime(tgl.year, tgl.month, 25)
        end = (start + pd.DateOffset(months=1)).replace(day=24)
    else:
        start = (tgl - pd.DateOffset(months=1)).replace(day=25)
        end = tgl.replace(day=24)
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

    role = st.selectbox("Login sebagai", ["Karyawan", "Owner"], key="role_login")

    if role == "Karyawan":
        nama = st.selectbox("Pilih Nama", list(karyawan_data.keys()), key="nama_login")
        pin = st.text_input("PIN", type="password", key="pin_login")

        if st.button("Login Karyawan", key="btn_login_karyawan"):
            if pin == karyawan_data[nama]["pin"]:
                st.session_state.login = ("karyawan", nama)
                st.rerun()
            else:
                st.error("PIN salah")

    else:
        pwd = st.text_input("Password Owner", type="password", key="pwd_owner")

        if st.button("Login Owner", key="btn_login_owner"):
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

    tanggal = st.date_input("Tanggal Kasbon", value=date.today(), key="tgl_kasbon")
    nominal = st.selectbox("Nominal", [50000,100000,150000,200000,250000,300000], key="nominal_kasbon")
    keterangan = st.text_area("Keterangan", key="ket_kasbon")

    df = load_data()
    total = df[df["nama"] == nama]["nominal"].sum() if not df.empty else 0
    sisa = limit - total

    st.info(f"Sisa Limit Anda: Rp {sisa:,.0f}")

    if st.button("Ajukan Kasbon", key="btn_ajukan"):
        if nominal <= sisa:
            response = supabase.table("kasbon").insert({
                "id": str(uuid.uuid4()),
                "tanggal": tanggal.strftime("%Y-%m-%d"),
                "nama": nama,
                "nominal": nominal,
                "keterangan": keterangan,
                "periode": get_periode(tanggal)
            }).execute()

            if response.data:
                st.success("Kasbon berhasil disimpan")
                st.rerun()
            else:
                st.error("Gagal menyimpan ke database")
        else:
            st.error("Melebihi limit")

    st.markdown("---")
    st.subheader("📜 Riwayat Kasbon Anda")

    if not df.empty:
        df_user = df[df["nama"] == nama].sort_values("tanggal", ascending=False)
        if not df_user.empty:
            st.dataframe(
                df_user[["tanggal", "nominal", "keterangan", "periode"]],
                use_container_width=True,
                key="df_user"
            )
        else:
            st.info("Belum ada kasbon")
    else:
        st.info("Belum ada data")

    if st.button("Logout", key="logout_karyawan"):
        st.session_state.login = None
        st.rerun()

# ================= OWNER =================
else:

    st.header("📊 Dashboard Owner")

    df = load_data()

    if df.empty:
        st.info("Belum ada data kasbon")
    else:

        summary = df.groupby("nama")["nominal"].sum().reset_index()

        st.subheader("📌 Rekap Total Per Karyawan")
        st.dataframe(summary, use_container_width=True, key="rekap_summary")

        st.subheader("🔎 Detail Riwayat Per Karyawan")
        pilih_nama = st.selectbox("Pilih Karyawan", summary["nama"], key="select_detail")

        df_nama = df[df["nama"] == pilih_nama].sort_values("tanggal", ascending=False)

        st.dataframe(
            df_nama[["tanggal", "nominal", "keterangan", "periode"]],
            use_container_width=True,
            key="df_detail"
        )

        st.subheader("📊 Grafik Total Kasbon")
        fig = px.bar(summary, x="nama", y="nominal", color="nama")
        st.plotly_chart(fig, use_container_width=True, key="grafik_owner")

        st.subheader("🗑 Hapus Data")

        pilih_id = st.selectbox("Hapus Per Transaksi", df["id"], key="hapus_id")
        if st.button("Hapus Transaksi", key="btn_hapus_id"):
            supabase.table("kasbon").delete().eq("id", pilih_id).execute()
            st.rerun()

        pilih_nama_delete = st.selectbox("Hapus Semua Per Karyawan", df["nama"].unique(), key="hapus_nama")
        if st.button("Hapus Semua Data Karyawan", key="btn_hapus_nama"):
            supabase.table("kasbon").delete().eq("nama", pilih_nama_delete).execute()
            st.rerun()

        if st.checkbox("⚠ Saya yakin ingin hapus SEMUA data", key="checkbox_reset"):
            if st.button("Hapus Semua Data", key="btn_reset"):
                supabase.table("kasbon").delete().neq("id", "").execute()
                st.rerun()

    if st.button("Logout", key="logout_owner"):
        st.session_state.login = None
        st.rerun()

