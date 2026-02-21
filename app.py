import streamlit as st
import pandas as pd
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from typer import style
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import plotly.express as px

st.set_page_config(page_title="Scraper Multi-DB", layout="wide")

# ---------------------------
# STYLE CSS MODERNE
# ---------------------------
st.markdown("""
<style>
/* Sidebar clair */
[data-testid="stSidebar"] {background-color: #f7f9fc; display: flex; flex-direction: column;}
/* Titres */
.big-font {font-size:28px !important; font-weight:bold; color:#0B3D91; margin-bottom:15px;}
/* Metrics */
.stMetricValue {color: #1E81B0; font-weight:bold;}
.stMetricLabel {color: #0B3D91; font-weight:bold;}
/* Cards produits */
.card {background-color:#ffffff; padding:15px; border-radius:12px; box-shadow: 0 4px 8px rgba(0,0,0,0.15); margin-bottom:15px;}
.card-title {font-size:16px; font-weight:bold; color:#0B3D91;}
.card-text {font-size:14px; color:#333;}
/* Boutons */
.stButton>button {background-color:#1E81B0; color:white; font-weight:bold; border-radius:8px; padding:10px 25px;}

</style>
            
<style>
div.stButton > button:first-child {
    background-color: #003366;
    color: white;
    border-radius: 4px;
    padding: 8px 20px;
    border: none;
    font-size: 15px;
}
div.stButton > button:first-child:hover {
    background-color: #0055a5;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# CONFIG BASES
# ---------------------------
db_config = {
    "Article1.db": {"table": "IM_table", "col1": "type_habits", "url": "https://sn.coinafrique.com/categorie/vetements-homme"},
    "Article2.db": {"table": "IM_table2", "col1": "type_chaussures", "url": "https://sn.coinafrique.com/categorie/chaussures-homme"},
    "Article3.db": {"table": "IM_table3", "col1": "type_habits", "url": "https://sn.coinafrique.com/categorie/vetements-enfants"},
    "Article4.db": {"table": "IM_table4", "col1": "type_chaussures", "url": "https://sn.coinafrique.com/categorie/chaussures-enfants"}
}

# ---------------------------
# INIT DATABASES
# ---------------------------
def init_db():
    for db_name, cfg in db_config.items():
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        col1 = cfg["col1"]
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {cfg['table']}(
                {col1} TEXT,
                prix TEXT,
                adresse TEXT,
                image_lien TEXT
            )
        """)
        conn.commit()
        conn.close()

init_db()

# ---------------------------
# DRIVER
# ---------------------------
def get_driver():
    options = Options()
    options.add_argument("--headless")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ---------------------------
# SCRAPER LOGIC
# ---------------------------
def scrape_logic(nb_pages, url, col1):
    driver = get_driver()
    data = []
    try:
        for p in range(1, nb_pages + 1):
            driver.get(f"{url}?page={p}")
            time.sleep(2)
            containers = driver.find_elements(By.CSS_SELECTOR, 'div.ad__card')
            for container in containers:
                try: type_item = container.find_element(By.CSS_SELECTOR, 'a[title]').get_attribute("title")
                except: type_item = ""
                try: prix = container.find_element(By.CSS_SELECTOR, 'p.ad__card-price').text
                except: prix = ""
                try: adresse = container.find_element(By.CSS_SELECTOR, 'p.ad__card-location').text
                except: adresse = ""
                try: image_lien = container.find_element(By.CSS_SELECTOR, 'img.ad__card-img').get_attribute("src")
                except: image_lien = ""
                data.append((type_item, prix, adresse, image_lien))
    finally:
        driver.quit()
    return pd.DataFrame(data, columns=[col1, "prix", "adresse", "image_lien"])

# ---------------------------
# SIDEBAR - MENU BOUTONS
# ---------------------------
with st.sidebar:
    st.markdown("## Navigation")
    st.markdown("---")

    # Initialiser la session si vide
    if "choice" not in st.session_state:
        st.session_state.choice = "Scraper Live"

    # Boutons menu
    if st.button("Scraper Live", use_container_width=True):
        st.session_state.choice = "Scraper Live"

    if st.button("Upload Web Scraper", use_container_width=True):
        st.session_state.choice = "Upload Web Scraper"

    if st.button("Dashboard", use_container_width=True):
        st.session_state.choice = "Dashboard"

    if st.button("Évaluation", use_container_width=True):
        st.session_state.choice = "Évaluation"

    st.markdown("---")

    db_choice = st.selectbox(
        "Choisir la base",
        list(db_config.keys())
    )

# Récupération du choix actif
choice = st.session_state.choice

table = db_config[db_choice]['table']
col1 = db_config[db_choice]['col1']


# ---------------------------
# SCRAPER LIVE MODERNE
# ---------------------------
if choice == "Scraper Live":
    st.markdown('<p class="big-font">🌍 CoinAfrique Scraper Live</p>', unsafe_allow_html=True)

    with st.expander("Paramètres du scraping", expanded=True):
        nb_pages = st.number_input("Nombre de pages à scraper", min_value=1, max_value=5, value=1, step=1)

        if st.button("Lancer le scraping"):
            url = db_config[db_choice]["url"]
            
            placeholder = st.empty()
            progress_text = st.empty()
            progress_bar = st.progress(0)

            data_all = pd.DataFrame()
            for i in range(1, nb_pages + 1):
                progress_text.text(f"Scraping page {i}/{nb_pages} ...")
                df_page = scrape_logic(1, f"{url}?page={i}", col1)
                data_all = pd.concat([data_all, df_page], ignore_index=True)
                progress_bar.progress(int(i/nb_pages*100))
                time.sleep(0.5)  # pour visualiser la progression

            conn = sqlite3.connect(db_choice)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            existing_cols = [row[1] for row in cursor.fetchall()]
            for col in data_all.columns:
                if col not in existing_cols:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
            conn.commit()
            data_all.to_sql(table, conn, if_exists='append', index=False)
            conn.close()

            placeholder.success(f"Scraping terminé : {len(data_all)} éléments ajoutés dans la base {db_choice} !")
            st.dataframe(data_all.head(), use_container_width=True)
            progress_bar.empty()
            progress_text.empty()


# ---------------------------
# UPLOAD WEB SCRAPER
# ---------------------------
elif choice == "Upload Web Scraper":
    uploaded_file = st.file_uploader("Choisir un fichier CSV", type="csv")
    if uploaded_file:
        try:
            # Lecture CSV sécurisée, ignore les lignes mal formées
            df_raw = pd.read_csv(uploaded_file, on_bad_lines='skip', sep=None, engine='python')
            st.success(f"CSV chargé avec succès : {df_raw.shape[0]} lignes, {df_raw.shape[1]} colonnes")
        except Exception as e:
            st.error(f"Erreur lors du chargement du CSV : {e}")
            df_raw = None

        if df_raw is not None:
            st.dataframe(df_raw.head(), use_container_width=True)

            if st.button("Nettoyer et sauvegarder"):
                df_clean = df_raw.dropna().drop_duplicates()
                
                # Renommer les colonnes automatiquement si possible
                col_mapping = {}
                if df_clean.shape[1] >= 4:
                    col_mapping = {df_clean.columns[0]: col1,
                                   df_clean.columns[1]: 'prix',
                                   df_clean.columns[2]: 'adresse',
                                   df_clean.columns[3]: 'image_lien'}
                df_final = df_clean.rename(columns=col_mapping)
                df_final['source'] = "Web Scraper Ext"
                df_final = df_final.loc[:, ~df_final.columns.duplicated()]

                # Connexion DB
                conn = sqlite3.connect(db_choice)
                cursor = conn.cursor()
                
                # créer table si pas existante
                columns_sql = ", ".join([f"{col} TEXT" for col in df_final.columns])
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns_sql})")
                
                # vérifier colonnes existantes
                cursor.execute(f"PRAGMA table_info({table})")
                existing_cols = [row[1] for row in cursor.fetchall()]
                for col in df_final.columns:
                    if col not in existing_cols:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                conn.commit()
                df_final.to_sql(table, conn, if_exists='append', index=False)
                conn.close()

                st.success(f"Données intégrées avec succès : {len(df_final)} lignes ajoutées !")
# ---------------------------
# DASHBOARD MODERNE
# ---------------------------
elif choice == "Dashboard":
    conn = sqlite3.connect(db_choice)
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()

    if df.empty:
        st.warning("Base vide")
    else:
        # Nettoyage prix
        df['prix_num'] = (df['prix'].astype(str)
                          .str.replace(r'[^\d]', '', regex=True)
                          .replace('', '0')
                          .astype(float))

        st.markdown('<p class="big-font">Dashboard Produits</p>', unsafe_allow_html=True)

        # Filtre par type
        type_unique = df[col1].dropna().unique()
        selected_type = st.selectbox(f"Filtrer par {col1}", ["Tous"] + list(type_unique))
        if selected_type != "Tous":
            df = df[df[col1] == selected_type]

        # Metrics générales
        colA, colB, colC = st.columns(3)
        colA.metric("Prix min", f"{df['prix_num'].min():,.0f} FCFA")
        colB.metric("Prix max", f"{df['prix_num'].max():,.0f} FCFA")
        colC.metric("Prix moyen", f"{df['prix_num'].mean():,.0f} FCFA")

        st.markdown("---")

        # Répartition par type
        st.subheader(f"Répartition par {col1}")
        df_counts = df[col1].value_counts().reset_index()
        df_counts.columns = [col1, 'Count']
        fig_type = px.bar(df_counts, x=col1, y='Count', color='Count', 
                          color_continuous_scale=px.colors.sequential.Teal)
        st.plotly_chart(fig_type, use_container_width=True)

        # Top 10 adresses
        st.subheader("Répartition par adresses")
        df_addr = df['adresse'].value_counts().reset_index()
        df_addr.columns = ['Adresse', 'Count']
        df_addr = df_addr.head(10)
        fig_addr = px.bar(df_addr, x='Adresse', y='Count', color='Count', 
                          color_continuous_scale=px.colors.sequential.Plasma)
        st.plotly_chart(fig_addr, use_container_width=True)

        # Top 10 produits avec images et infos
        st.subheader("Top 10 produits")
        df_top = df.head(10).reset_index(drop=True)
        for i in range(len(df_top)):
            with st.container():
                st.markdown("<hr>", unsafe_allow_html=True)
                col_img, col_info = st.columns([1,3])
                with col_img:
                    if pd.notna(df_top.loc[i,'image_lien']):
                        st.image(df_top.loc[i,'image_lien'], width=150)
                with col_info:
                    st.markdown(f"**Type :** {df_top.loc[i, col1]}")
                    st.markdown(f"**Prix :** {df_top.loc[i, 'prix']}")
                    st.markdown(f"**Adresse :** {df_top.loc[i, 'adresse']}")


# ---------------------------
# ÉVALUATION
# ---------------------------
elif choice == "Évaluation":

    # CSS personnalisé
    st.markdown("""
        <style>
        .eval-title {
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 30px;
            color: #0b3d91;
        }

        .stLinkButton > a {
            display: inline-block;
            padding: 14px 28px;
            border-radius: 8px;
            font-weight: 600;
            text-align: center;
            transition: all 0.3s ease;
            background-color: #0b3d91;
            color: white;
            border: none;
        }

        .stLinkButton > a:hover {
            background-color: #072c66;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="big-font">Votre avis nous intéresse</p>', unsafe_allow_html=True)


    
    col1, col2 = st.columns(2)

    with col1:
        st.link_button("📋 Formulaire Kobo", "https://ee.kobotoolbox.org/x/mDA0mZRs")

    with col2:
        st.link_button("📋 Formulaire Google Forms", "https://forms.gle/pap2BDj6Eab9d9zC7")
