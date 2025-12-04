import streamlit as st
import pandas as pd
import time
import re

# --- 1. CONFIGURAÇÃO (APP SHELL) ---
st.set_page_config(page_title="Precificador 2026 - V52 Final", layout="centered", page_icon="💎")

# Tenta importar Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# --- 2. ESTADO (MEMORY) ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

# Variáveis
init_state('n_mlb', '') 
init_state('n_sku', '') 
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
init_state('n_frete', 18.86)
init_state('n_taxa', 16.5)
init_state('n_erp', 85.44)
init_state('n_merp', 20.0)

# --- 3. DESIGN SYSTEM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'Inter', sans-serif; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .stTabs [aria-selected="true"] { background-color: #2563EB !important; color: white !important; }

    /* Cards */
    .input-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05); border: 1px solid #EFEFEF; margin-bottom: 20px; }
    .feed-card { background: white; border-radius: 16px; border: 1px solid #DBDBDB; box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin-bottom: 15px; overflow: hidden; }
    .card-header { padding: 15px 20px; border-bottom: 1px solid #F0F0F0; display: flex; justify-content: space-between; align-items: center; }
    .card-body { padding: 20px; text-align: center; }

    /* Tipografia */
    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .price-hero { font-size: 32px; font-weight: 800; letter-spacing: -1px; color: #262626; margin: 5px 0; }
    
    /* Pills */
    .pill { padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }
    .pill-green { background-color: #E6FFFA; color: #047857; border: 1px solid #D1FAE5; }
    .pill-yellow { background-color: #FFFBEB; color: #B45309; border: 1px solid #FCD34D; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FEE2E2; }

    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #E5E5E5 !important; color: #333 !important; border-radius: 8px !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; border-radius: 10px; height: 50px; font-weight: 600; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); border: none; }
    
    /* Search Bar */
    div[data-testid="stSelectbox"] > div > div { background-color: white !important; border: 1px solid #2563EB !important; border-radius: 12px !important; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.1); }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNÇÕES ---
def limpar_valor_dinheiro(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    valor_str = str(valor).strip()
    valor_str = re.sub(r'[^\d,\.-]', '', valor_str)
    if not valor_str: return 0.0
    if ',' in valor_str and '.' in valor_str: valor_str = valor_str.replace('.', '').replace(',', '.') 
    elif ',' in valor_str: valor_str = valor_str.replace(',', '.')
    try: return float(valor_str)
    except: return 0.0

def reiniciar_app():
    time.sleep(0.1)
    if hasattr(st, 'rerun'): st.rerun()
    else: st.experimental_rerun()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("Ajustes")
    imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5)
    with st.expander("Frete ML (<79)", expanded=True):
        taxa_12_29 = st.number_input("12-29", value=6.25)
        taxa_29_50 = st.number_input("29-50", value=6.50)
        taxa_50_79 = st.number_input("50-79", value=6.75)
        taxa_minima = st.number_input("Min", value=3.25)
    st.divider()
    
    # IMPORTAÇÃO MANUAL
    st.markdown("### 📂 Importar")
    uploaded_file = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            xl = pd.ExcelFile(uploaded_file)
            aba_selecionada = st.selectbox("1. Aba:", xl.sheet_names, index=0)
            header_row = st.number_input("2. Linha Cabeçalho:", value=8, min_value=0)
            
            df_preview = xl.parse(aba_selecionada, header=header_row, nrows=5)
            cols = [c for c in df_preview.columns if "Unnamed" not in str(c)]
            
            st.caption("3. Mapear Colunas:")
            def get_idx(opts, keys):
                if isinstance(keys, str): keys = [keys]
                for i, o in enumerate(opts):
                    for k in keys: 
                        if k.lower() in str(o).lower(): return i
                return 0

            c_prod = st.selectbox("Produto", cols, index=get_idx(cols, ["Produto", "Nome"]))
            c_mlb = st.selectbox("MLB", cols, index=get_idx(cols, ["Anúncio", "MLB"]))
            c_sku = st.selectbox("SKU", cols, index=get_idx(cols, ["SKU", "Ref"])) # Adicionado SKU
            c_cmv = st.selectbox("CMV", cols, index=get_idx(cols, "CMV"))
            c_erp = st.selectbox("Preço ERP", cols, index=get_idx(cols, ["ERP", "Base", "GRA"]))
            c_prc = st.selectbox("Preço Venda", cols, index=get_idx(cols, ["Preço", "Venda"]))
            
            # Novos Mapeamentos
            c_desc = st.selectbox("Desconto %", cols, index=get_idx(cols, ["Desconto", "%"]))
            c_bonus = st.selectbox("Rebate/Bônus", cols, index=get_idx(cols, ["Bônus", "Rebate", "Bonus"]))
            
            if st.button("✅ Importar", type="primary"):
                df = xl.parse(aba_selecionada, header=header_row)
                cnt = 0
                st.session_state.lista_produtos = []
                for _, row in df.iterrows():
                    try:
                        p = str(row[c_prod])
                        if not p or p == 'nan': continue
                        
                        # Leitura de Valores
                        cmv = limpar_valor_dinheiro(row[c_cmv])
                        pb = limpar_valor_dinheiro(row[c_prc])
                        erp = limpar_valor_dinheiro(row[c_erp])
                        if erp == 0: erp = pb
                        
                        # Leitura dos novos campos
                        desc = limpar_valor_dinheiro(row[c_desc])
                        bonus = limpar_valor_dinheiro(row[c_bonus])
                        
                        # Regra Decimal (0.03 -> 3.0)
                        if 0 < desc < 1.0: desc = desc * 100
                        
                        sku_val = str(row[c_sku]) if c_sku in row else ""
                        if sku_val == 'nan': sku_val = ""

                        st.session_state.lista_produtos.append({
                            "id": int(time.time()*1000)+_, 
                            "MLB": str(row[c_mlb]), 
                            "SKU": sku_val, 
                            "Produto": p,
                            "CMV": cmv, 
                            "FreteManual": 18.86, 
                            "TaxaML": 16.5, 
                            "Extra": 0.0,
                            "PrecoERP": erp, 
                            "MargemERP": st.session_state.n_merp, 
                            "PrecoBase": pb, 
                            "DescontoPct": desc, 
                            "Bonus": bonus       
                        })
                        cnt += 1
                    except: continue
                
                st.toast(f"{cnt} importados!", icon="🚀")
                time.sleep(1)
                reiniciar_app()
        except Exception as e: st.error(f"Erro: {e}")

# --- 6. LÓGICA ---
def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", taxa_50_79
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", taxa_29_50
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", taxa_12_29
    else: return "Tab. Mínima", taxa_minima

def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_
