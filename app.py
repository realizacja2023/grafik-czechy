import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import date
import pandas as pd
import json

st.set_page_config(page_title="Grafik Pracy & Pracomierz", page_icon="📅", layout="wide")

st.title("📅 Grafik Pracy i Pracomierz — Czechy")
st.markdown("---")

# Inicjalizacja Firebase (Lokalnie lub z Chmury Streamlit)
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            # Odczyt klucza z ustawień w chmurze
            key_dict = json.loads(st.secrets["firebase"]["json"])
            cred = credentials.Certificate(key_dict)
        else:
            # Odczyt klucza z pliku lokalnego
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Błąd inicjalizacji Firebase: {e}")
        st.stop()

db = firestore.client()

# Sidebar - Formularz
st.sidebar.header("➕ Dodaj / Edytuj Zmianę")
user = st.sidebar.selectbox("Osoba", ["Piotr", "Basia"])
selected_date = st.sidebar.date_input("Data", date.today())
shift_type = st.sidebar.selectbox(
    "Rodzaj zmiany / Aktywność", 
    [
        "Rano (6:00 - 14:00)", 
        "Popołudnie (14:00 - 22:00)", 
        "Noc (22:00 - 6:00)", 
        "Wolne / Dom", 
        "Wyjazd / Zakupy / Odbiór"
    ]
)

hours = st.sidebar.number_input("Godziny podstawowe", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
overtime = st.sidebar.number_input("Nadgodziny", min_value=0.0, max_value=12.0, value=0.0, step=0.5)
hourly_rate = st.sidebar.number_input("Stawka godzinowa (CZK)", min_value=0, value=180, step=5)
notes = st.sidebar.text_input("Uwagi / Podział zadań")

if st.sidebar.button("💾 Zapisz w Firestore", use_container_width=True):
    shift_id = f"{user.lower()}_{selected_date.strftime('%Y%m%d')}"
    gross_earnings = (hours + (overtime * 1.25)) * hourly_rate
    
    doc_ref = db.collection("shifts").document(shift_id)
    doc_ref.set({
        "user_id": user,
        "date": str(selected_date),
        "shift_type": shift_type,
        "hours_worked": hours,
        "overtime_hours": overtime,
        "gross_earnings_czk": gross_earnings,
        "notes": notes,
        "updated_at": firestore.SERVER_TIMESTAMP
    })
    st.sidebar.success(f"Zapisano wpis dla {user}!")

# Odczyt danych
try:
    shifts_ref = db.collection("shifts").order_by("date", direction=firestore.Query.DESCENDING)
    docs = shifts_ref.stream()
    data = [doc.to_dict() for doc in docs]
except Exception as e:
    st.error(f"❌ Błąd podczas pobierania danych z Firestore: {e}")
    data = []

if data:
    df = pd.DataFrame(data)
    tab1, tab2 = st.tabs(["📊 Wszystkie wpisy", "👤 Podsumowanie wg Osoby"])
    
    with tab1:
        st.subheader("Wspólny Grafik")
        display_df = df[["date", "user_id", "shift_type", "hours_worked", "overtime_hours", "gross_earnings_czk", "notes"]].copy()
        display_df.columns = ["Data", "Osoba", "Zmiana", "Godziny", "Nadgodziny", "Brutto (CZK)", "Uwagi"]
        st.dataframe(display_df, use_container_width=True)
        
    with tab2:
        st.subheader("Miesięczne Podsumowanie Pracy")
        col_piotr, col_basia = st.columns(2)
        
        df_piotr = df[df["user_id"] == "Piotr"]
        df_basia = df[df["user_id"] == "Basia"]
        
        with col_piotr:
            st.markdown("### 👨‍🔧 Piotr")
            hrs_p = df_piotr["hours_worked"].sum() + df_piotr["overtime_hours"].sum() if not df_piotr.empty else 0
            czk_p = df_piotr["gross_earnings_czk"].sum() if not df_piotr.empty else 0
            st.metric("Łącznie godzin", f"{hrs_p:.1f} h")
            st.metric("Szacowane brutto", f"{czk_p:,.0f} CZK")
            
        with col_basia:
            st.markdown("### 👩‍💼 Basia")
            hrs_b = df_basia["hours_worked"].sum() + df_basia["overtime_hours"].sum() if not df_basia.empty else 0
            czk_b = df_basia["gross_earnings_czk"].sum() if not df_basia.empty else 0
            st.metric("Łącznie godzin", f"{hrs_b:.1f} h")
            st.metric("Szacowane brutto", f"{czk_b:,.0f} CZK")
else:
    st.info("Baza Firestore jest pusta. Dodaj pierwszy wpis w panelu po lewej stronie.")
