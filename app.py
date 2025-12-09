import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import os
import re
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador V64 - Restore", layout="centered", page_icon="💎")
DB_NAME = 'precificador_v64_restore.db' # Banco novo para garantir limpeza

# Verifica Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# --- 2. FUNÇÕES AUXILIARES ---
def reiniciar_app():
    time.sleep(0.1)
    if hasattr(st, 'rerun'): st.rerun()
    else: st.experimental_rerun()

def limpar_valor_dinheiro(valor):
    try:
        if pd.isna(valor) or str(valor).strip() == "" or str(valor).strip() == "-": return 0.0
        if isinstance(valor, (int, float)): return float(valor)
        valor_str = str(valor).strip()
        valor_str = re.sub(r'[^\d,\.-]', '', valor_str)
        if not valor_str: return 0.0
        if ',' in valor_str and '.' in valor_str: valor_str = valor_str.replace('.', '').replace(',', '.') 
        elif ',' in valor_str: valor_str = valor_str.replace(',', '.')
        return float(valor_str)
    except: return 0.0

# Planos
PLAN_LIMITS = {
    "Silver": {"product_limit": 50, "collab_limit": 1, "dashboards": False, "price": "R$ 49,90"},
    "Gold": {"product_limit": 999999, "collab_limit": 4, "dashboards": False, "price": "R$ 99,90"},
    "Platinum": {"product_limit": 999999, "collab_limit": 999999, "dashboards": True, "price": "R$ 199,90"}
}

# --- 3. BANCO DE DADOS ---
def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db(reset=False):
    if reset and os.path.exists(DB_NAME):
        try: os.remove(DB_NAME)
        except: pass
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE, password TEXT, name TEXT, plan TEXT, 
            is_active BOOLEAN, photo_base64 TEXT, owner_id INTEGER DEFAULT 0
        )
    ''')
    
    # Produtos (Schema da V64 - Estável)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            mlb TEXT, sku TEXT, nome TEXT,
            cmv REAL, frete_manual REAL, extra REAL,
            taxa_ml REAL, preco_erp REAL, margem_erp REAL,
            preco_sugerido REAL, preco_usado REAL,
            desc_pct REAL, bonus REAL
        )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_NAME): init_db()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# CRUD USER
def add_user(username, password, name, plan, owner_id=0):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, name, plan, is_active, owner_id) VALUES (?,?,?,?,?,?)', 
                  (username, make_hashes(password), name, plan, True, owner_id))
        conn.commit()
        return c.lastrowid
    except: return -1
    finally: conn.close()

def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        data = c.fetchone()
        if data and data[5] and check_hashes(password, data[2]):
            return {"id": data[0], "name": data[3], "plan": data[4], "owner_id": data[7], "username": username}
    except: pass
    finally: conn.close()
    return None

# CRUD PRODUTOS
def carregar_produtos(owner_id):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM products WHERE owner_id = ?", conn, params=(owner_id,))
        # Renomeia colunas para o padrão do App
        lista = []
        for _, row in df.iterrows():
            lista.append({
                "id": row['id'], 
                "MLB": row['mlb'], "SKU": row['sku'], "Produto": row['nome'],
                "CMV": row['cmv'], "FreteManual": row['frete_manual'], "Extra": row['extra'],
                "TaxaML": row['taxa_ml'], "PrecoERP": row['preco_erp'], "MargemERP": row['margem_erp'],
                "PrecoSugerido": row['preco_sugerido'], "PrecoUsado": row['preco_usado'],
                "DescontoPct": row['desc_pct'], "Bonus": row['bonus']
            })
        return lista
    except: return []
    finally: conn.close()

def salvar_produto(owner_id, item):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO products (
        owner_id, mlb, sku, nome, cmv, frete_manual, extra, taxa_ml, 
        preco_erp, margem_erp, preco_sugerido, preco_usado, desc_pct, bonus
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        owner_id, item.get('MLB',''), item.get('SKU',''), item.get('Produto',''), 
        item.get('CMV',0), item.get('FreteManual',0), item.get('Extra',0), item.get('TaxaML',0),
        item.get('PrecoERP',0), item.get('MargemERP',0), item.get('PrecoSugerido',0), 
        item.get('PrecoUsado',0), item.get('DescontoPct',0), item.get('Bonus',0)
    ))
    conn.commit()
    conn.close()

def deletar_produto(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def atualizar_campo_db(item_id, campo, valor):
    conn = get_db_connection()
    mapa = {'PrecoUsado': 'preco_usado', 'DescontoPct': 'desc_pct', 'Bonus': 'bonus', 'CMV': 'cmv', 'PrecoERP': 'preco_erp'}
    if campo in mapa:
        conn.execute(f"UPDATE products SET {mapa[campo]} = ? WHERE id = ?", (valor, item_id))
        conn.commit()
    conn.close()

# --- 4. CSS (VISUAL APPLE/INSTAGRAM V64) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #F5F5F7; font-family: 'Inter', sans-serif; color: #1D1D1F; }
    
    .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.08); }
    .input-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E5E5EA; }
    .product-card { background: white; border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid #E5E5EA; }
    
    div.stButton > button[kind="primary"] { background-color: #0071E3; color: white; border-radius: 12px; height: 48px; border: none; font-weight: 600; width: 100%; }
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #D1D1D6 !important; border-radius: 8px !important; }
    div[data-testid="stSelectbox"] > div > div { background-color: white !important; border: 1px solid #D1D1D6 !important; border-radius: 12px !important; }

    .pill { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; }
    .pill-green { background: #E6FFFA; color: #047857; }
    .pill-yellow { background: #FFFBEB; color: #B45309; }
    .pill-red { background: #FEF2F2; color: #DC2626; }
    
    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .price-display { font-size: 14px; color: #1D1D1F; font-weight: 500; }
    
    .card-footer { background-color: #F8F9FA; padding: 10px 20px; border-top: 1px solid #F0F0F0; display: flex; justify-content: space-between; font-size: 11px; color: #666; }
    .margin-box { text-align: center; flex: 1; }
    
    .audit-box { background: #F9FAFB; padding: 15px; border-radius: 8px; border: 1px dashed #D1D5DB; font-family: monospace; font-size: 12px; margin-top: 10px;}
    .audit-line { display: flex; justify-content: space-between; margin-bottom: 5px; }
    .audit-bold { font-weight: bold; color: #000; }
</style>
""", unsafe_allow_html=True)

# --- 5. ESTADO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = {}
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

# Auto-Reparo
def sanear_dados():
    if st.session_state.lista_produtos:
        fixed = []
        for p in st.session_state.lista_produtos:
            # Defaults V64
            if 'PrecoBase' not in p: p['PrecoBase'] = 0.0
            if 'DescontoPct' not in p: p['DescontoPct'] = 0.0
            if 'Bonus' not in p: p['Bonus'] = 0.0
            if 'CMV' not in p: p['CMV'] = 0.0
            if 'PrecoERP' not in p: p['PrecoERP'] = 0.0
            if 'PrecoUsado' not in p: p['PrecoUsado'] = 0.0
            if 'PrecoSugerido' not in p: p['PrecoSugerido'] = 0.0
            if 'FreteManual' not in p: p['FreteManual'] = 0.0
            if 'Extra' not in p: p['Extra'] = 0.0
            if 'Produto' not in p: p['Produto'] = 'Sem Nome'
            fixed.append(p)
        st.session_state.lista_produtos = fixed

sanear_dados()

def init_var(k, v): 
    if k not in st.session_state: st.session_state[k] = v
init_var('n_nome', ''); init_var('n_cmv', 32.57); init_var('n_extra', 0.0); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0); init_var('n_mlb', ''); init_var('n_sku', '')
init_var('imposto_padrao', 27.0); init_var('n_desc', 0.0); init_var('n_bonus', 0.0)
init_var('taxa_12_29', 6.25); init_var('taxa_29_50', 6.50); init_var('taxa_50_79', 6.75); init_var('taxa_minima', 3.25)

# --- 6. TELA DE LOGIN ---
if not st.session_state.logged_in:
    with st.sidebar:
        st.header("Suporte")
        if st.button("🚨 RESET TOTAL", type="primary"):
            init_db(reset=True)
            st.success("Resetado! Crie conta."); time.sleep(1); reiniciar_app()

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center; color:#0071E3;'>Precificador PRO</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Entrar", "Criar Conta"])
        with t1:
            with st.container(border=True):
                u_in = st.text_input("Usuário", key="li_u")
                p_in = st.text_input("Senha", type="password", key="li_p")
                if st.button("ENTRAR", type="primary"):
                    res = login_user(u_in, p_in)
                    if res:
                        st.session_state.user = res
                        st.session_state.logged_in = True
                        st.session_state.owner_id = res['id'] if res['owner_id'] == 0 else res['owner_id']
                        st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                        sanear_dados()
                        reiniciar_app()
                    else: st.error("Login falhou.")
        with t2:
            with st.container(border=True):
                rn = st.text_input("Nome", key="rg_n")
                ru = st.text_input("Email", key="rg_u")
                rp = st.text_input("Senha", type="password", key="rg_p")
                rpl = st.selectbox("Plano", ["Silver (R$49)", "Gold (R$99)", "Platinum (R$199)"])
                if st.button("CRIAR CONTA", type="primary"):
                    if add_user(ru, rp, rn, rpl.split()[0]) > 0: st.success("Criado! Faça login.")
                    else: st.error("Erro.")
    st.stop()

# ==============================================================================
# ÁREA LOGADA
# ==============================================================================

with st.sidebar:
    u = st.session_state.user
    st.markdown(f"**{u['name']}**")
    st.caption(f"{u['plan']}")
    
    if st.button("Sair"):
        st.session_state.logged_in = False
        reiniciar_app()
    
    st.divider()
    st.markdown("### Configurações")
    st.session_state.imposto_padrao = st.number_input("Impostos %", value=st.session_state.imposto_padrao, step=0.5)
    with st.expander("Frete ML"):
        st.session_state.taxa_12_29 = st.number_input("12-29", value=st.session_state.taxa_12_29)
        st.session_state.taxa_29_50 = st.number_input("29-50", value=st.session_state.taxa_29_50)
        st.session_state.taxa_50_79 = st.number_input("50-79", value=st.session_state.taxa_50_79)
        st.session_state.taxa_minima = st.number_input("Min", value=st.session_state.taxa_minima)
        
    st.divider()
    # IMPORTADOR V64 RESTAURADO
    st.markdown("### 📂 Importar")
    uploaded_file = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            aba = st.selectbox("Aba", xl.sheet_names)
            h_row = st.number_input("Linha Header", value=8, min_value=0)
            
            df_prev = xl.parse(aba, header=h_row, nrows=2)
            cols = [str(c) for c in df_prev.columns if "Unnamed" not in str(c)]
            
            st.caption("Mapear Colunas:")
            def gidx(k): 
                for i, o in enumerate(cols): 
                    if isinstance(k, list):
                        for kw in k:
                            if kw.lower() in str(o).lower(): return i
                    elif k.lower() in str(o).lower(): return i
                return 0

            c_prod = st.selectbox("Produto", cols, index=gidx(["Produto", "Nome"]))
            c_mlb = st.selectbox("MLB", cols, index=gidx(["Anúncio", "MLB"]))
            c_sku = st.selectbox("SKU", cols, index=gidx(["SKU", "Ref"]))
            c_cmv = st.selectbox("CMV", cols, index=gidx("CMV"))
            c_erp = st.selectbox("Preço ERP", cols, index=gidx(["ERP", "Base", "GRA"]))
            c_prc = st.selectbox("Preço Venda", cols, index=gidx(["Preço", "Venda"]))
            c_desc = st.selectbox("Desconto %", cols, index=gidx(["Desconto", "%"]))
            c_bonus = st.selectbox("Bônus", cols, index=gidx(["Bônus", "Rebate"]))
            
            if st.button("Importar Dados", type="primary"):
                df = xl.parse(aba, header=h_row)
                cnt = 0
                st.session_state.lista_produtos = [] # Limpa ao importar
                for _, row in df.iterrows():
                    try:
                        p = str(row[c_prod])
                        if not p or p == 'nan': continue
                        
                        cmv = limpar_valor_dinheiro(row[c_cmv])
                        pb = limpar_valor_dinheiro(row[c_prc])
                        erp = limpar_valor_dinheiro(row[c_erp])
                        if erp == 0: erp = pb
                        
                        desc = limpar_valor_dinheiro(row[c_desc])
                        bonus = limpar_valor_dinheiro(row[c_bonus])
                        if 0 < desc < 1.0: desc = desc * 100
                        
                        item = {
                            "MLB": str(row.get(c_mlb, "")), "SKU": str(row.get(c_sku, "")), "Produto": p,
                            "CMV": cmv, "FreteManual": 18.86, "TaxaML": 16.5, "Extra": 0.0,
                            "PrecoERP": erp, "MargemERP": st.session_state.n_merp, 
                            "PrecoBase": pb, "PrecoSugerido": pb, "PrecoUsado": pb, # Assume usado = importado
                            "DescontoPct": desc, "Bonus": bonus       
                        }
                        salvar_produto(st.session_state.owner_id, item)
                        cnt += 1
                    except: continue
                st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                st.success(f"{cnt} importados!")
                time.sleep(1)
                reiniciar_app()
        except Exception as e: st.error(f"Erro: {e}")

# --- LÓGICA DE CÁLCULO V64 ---
def identificar_frete(p):
    if p >= 79: return 0.0, "Manual"
    if 50 <= p < 79: return st.session_state.taxa_50_79, "Tab 50-79"
    if 29 <= p < 50: return st.session_state.taxa_29_50, "Tab 29-50"
    if 12.5 <= p < 29: return st.session_state.taxa_12_29, "Tab 12-29"
    return st.session_state.taxa_minima, "Mínimo"

def calc_reverso(custo, lucro_alvo, t_ml, imp, f_man):
    div = 1 - ((t_ml + imp)/100)
    if div <= 0: return 0
    p1 = (custo + f_man + lucro_alvo) / div
    if p1 >= 79: return p1
    for tx in [st.session_state.taxa_50_79, st.session_state.taxa_29_50, st.session_state.taxa_12_29]:
        p = (custo + tx + lucro_alvo) / div
        _, lbl = identificar_frete(p)
        if lbl != "Mínimo": return p
    return p1

def add_action():
    if not st.session_state.n_nome:
        st.toast("Nome obrigatório!", icon="⚠️"); return

    lucro = st.session_state.n_erp * (st.session_state.n_merp / 100)
    p_sug = calc_reverso(
        st.session_state.n_cmv + st.session_state.n_extra, lucro,
        st.session_state.n_taxa, st.session_state.imposto_padrao, st.session_state.n_frete
    )
    
    item = {
        "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv, "FreteManual": st.session_state.n_frete, "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra, "PrecoERP": st.session_state.n_erp, "MargemERP": st.session_state.n_merp,
        "PrecoSugerido": p_sug, "PrecoUsado": p_sug, "PrecoBase": p_sug,
        "DescontoPct": 0.0, "Bonus": 0.0
    }
    
    salvar_produto(st.session_state.owner_id, item)
    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
    st.toast("Produto salvo!", icon="✅")
    st.session_state.n_nome = ""

# --- INTERFACE PRINCIPAL ---
st.title("Área de Trabalho")

abas = ["⚡ Precificador"]
if PLAN_LIMITS[st.session_state.user['plan']]['dashboards']: abas.append("📊 BI")
tabs = st.tabs(abas)

with tabs[0]:
    # BUSCA AUTOCOMPLETE (V64)
    mapa_busca = {}
    opcoes_busca = []
    if st.session_state.lista_produtos:
        for p in st.session_state.lista_produtos:
            label = f"{p['Produto']} (MLB: {p['MLB']})"
            opcoes_busca.append(label)
            mapa_busca[label] = p

    c_busca, c_sort = st.columns([3, 1])
    selecao_busca = c_busca.selectbox("Busca", options=opcoes_busca, index=None, placeholder="🔍 Buscar...", label_visibility="collapsed")
    ordem_sort = c_sort.selectbox("", ["Recentes", "A-Z", "Z-A", "Maior Margem", "Menor Margem", "Maior Preço"], label_visibility="collapsed")

    lista_final = []
    if selecao_busca:
        lista_final = [mapa_busca[selecao_busca]]
    else:
        temp_list = []
        for item in st.session_state.lista_produtos:
            # Proteção contra dados faltantes
            if 'PrecoUsado' not in item: continue
            
            # CÁLCULO BASEADO NO PREÇO USADO (Que você edita)
            pf = item['PrecoUsado'] * (1 - item['DescontoPct']/100)
            
            # Frete Inteligente
            fr_val, fr_lbl = identificar_frete(pf)
            if fr_lbl == "Manual": fr_val = item['FreteManual']
            
            imp = pf * (st.session_state.imposto_padrao/100)
            com = pf * (item['TaxaML']/100)
            custos = item['CMV'] + item['Extra'] + fr_val + imp + com
            lucro = pf - custos + item['Bonus']
            
            mrg_v = (lucro/pf*100) if pf > 0 else 0
            
            view_item = item.copy()
            view_item.update({'_pf': pf, '_mrg': mrg_v})
            temp_list.append(view_item)
            
        if ordem_sort == "A-Z": temp_list.sort(key=lambda x: str(x['Produto']).lower())
        elif ordem_sort == "Z-A": temp_list.sort(key=lambda x: str(x['Produto']).lower(), reverse=True)
        elif ordem_sort == "Maior Margem": temp_list.sort(key=lambda x: x['_mrg'], reverse=True)
        elif ordem_sort == "Menor Margem": temp_list.sort(key=lambda x: x['_mrg'])
        elif ordem_sort == "Maior Preço": temp_list.sort(key=lambda x: x['_pf'], reverse=True)
        else: temp_list.reverse()
        lista_final = temp_list

    if not selecao_busca:
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        st.caption("CADASTRAR NOVO")
        st.text_input("MLB", key="n_mlb", placeholder="Ex: MLB-12345")
        c1, c2 = st.columns([1, 2])
        c1.text_input("SKU", key="n_sku")
        c2.text_input("Produto", key="n_nome")
        c3, c4 = st.columns(2)
        c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
        c4.number_input("Frete Manual", step=0.01, format="%.2f", key="n_frete")
        st.markdown("<hr style='margin: 10px 0; border-color: #eee;'>", unsafe_allow_html=True)
        c5, c6, c7 = st.columns(3)
        c5.number_input("Taxa ML %", step=0.5, format="%.1f", key="n_taxa")
        c6.number_input("Preço ERP", step=0.01, format="%.2f", key="n_erp")
        c7.number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")
        st.write("")
        st.button("Cadastrar Item", type="primary", use_container_width=True, on_click=add_action)
        st.markdown('</div>', unsafe_allow_html=True)

    if lista_final:
        st.caption(f"Visualizando {len(lista_final)} produtos")
        for item in lista_final:
            
            # Recálculo para exibição
            pf = item['PrecoUsado'] * (1 - item['DescontoPct']/100)
            fr_val, fr_lbl = identificar_frete(pf)
            if fr_lbl == "Manual": fr_val = item['FreteManual']
            imp = pf * (st.session_state.imposto_padrao/100)
            com = pf * (item['TaxaML']/100)
            custos = item['CMV'] + item['Extra'] + fr_val + imp + com
            lucro = pf - custos + item['Bonus']
            mrg_v = (lucro/pf*100) if pf > 0 else 0
            erp_safe = item['PrecoERP'] if item['PrecoERP'] > 0 else 1
            mrg_erp = (lucro/erp_safe*100)
            
            # Cores
            if mrg_v < 8: cls = "pill-red"
            elif mrg_v < 15: cls = "pill-yellow"
            else: cls = "pill-green"
            
            txt_luc = f"+ R$ {lucro:.2f}" if lucro > 0 else f"- R$ {abs(lucro):.2f}"
            
            st.markdown(f"""
            <div class="product-card">
                <div class="card-header">
                    <div><div class="sku-text">{item['MLB']} {item['SKU']}</div><div class="title-text">{item['Produto']}</div></div>
                    <div class="pill {cls}">{mrg_v:.1f}%</div>
                </div>
                <div class="card-body">
                    <div style="display:flex; justify-content:space-between;">
                        <div class="price-display">Venda<br><b>R$ {pf:.2f}</b></div>
                        <div class="price-display" style="text-align:right;">Lucro<br><span style="color:{'#34C759' if lucro>0 else '#FF3B30'}">R$ {lucro:.2f}</span></div>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="margin-box">Margem Venda: <b>{mrg_v:.1f}%</b></div>
                    <div class="margin-box" style="border-left: 1px solid #eee;">Margem ERP: <b>{mrg_erp:.1f}%</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚙️ Editar e Detalhes"):
                def up(k, f, i=item['id']):
                    atualizar_campo_db(i, f, st.session_state[k])
                    for idx, p in enumerate(st.session_state.lista_produtos):
                        if p['id'] == i: st.session_state.lista_produtos[idx][f] = st.session_state[k]

                st.info(f"💡 Sugestão (Meta ERP): **R$ {item.get('PrecoSugerido', 0):.2f}**")

                e1, e2, e3 = st.columns(3)
                # AQUI EDITAMOS O PREÇO USADO
                e1.number_input("Preço Usado (Tabela)", value=float(item['PrecoUsado']), key=f"p{item['id']}", on_change=up, args=(f"p{item['id']}", 'PrecoUsado'))
                e2.number_input("Desc %", value=float(item['DescontoPct']), key=f"d{item['id']}", on_change=up, args=(f"d{item['id']}", 'DescontoPct'))
                e3.number_input("Bônus", value=float(item['Bonus']), key=f"b{item['id']}", on_change=up, args=(f"b{item['id']}", 'Bonus'))
                
                st.divider()
                st.markdown("##### 🧮 Memória de Cálculo")
                st.markdown(f"""
                <div class="audit-box">
                    <div class="audit-line"><span>(+) Preço Tabela</span> <span>R$ {item['PrecoUsado']:.2f}</span></div>
                    <div class="audit-line" style="color:red;"><span>(-) Desconto ({item['DescontoPct']}%)</span> <span>R$ {item['PrecoUsado'] - pf:.2f}</span></div>
                    <div class="audit-line audit-bold"><span>(=) VENDA LÍQUIDA</span> <span>R$ {pf:.2f}</span></div>
                    <br>
                    <div class="audit-line"><span>(-) Impostos ({st.session_state.imposto_padrao}%)</span> <span>R$ {imp:.2f}</span></div>
                    <div class="audit-line"><span>(-) Comissão ({item['TaxaML']}%)</span> <span>R$ {com:.2f}</span></div>
                    <div class="audit-line"><span>(-) Frete ({fr_lbl})</span> <span>R$ {fr_val:.2f}</span></div>
                    <div class="audit-line"><span>(-) Custo CMV</span> <span>R$ {item['CMV']:.2f}</span></div>
                    <div class="audit-line"><span>(-) Extras</span> <span>R$ {item['Extra']:.2f}</span></div>
                    <br>
                    <div class="audit-line" style="color:green;"><span>(+) Bônus / Rebate</span> <span>R$ {item['Bonus']:.2f}</span></div>
                    <hr style="border-top: 1px dashed #ccc;">
                    <div class="audit-line audit-bold"><span>(=) LUCRO LÍQUIDO</span> <span>R$ {lucro:.2f}</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")
                if st.button("🗑️ Excluir", key=f"del{item['id']}"):
                    deletar_produto(item['id'])
                    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                    reiniciar_app()

# --- ABA 2: DASHBOARDS ---
if len(tabs) > 1:
    with tabs[1]:
        if has_plotly and st.session_state.lista_produtos:
            visao = st.radio("Base de Análise:", ["Margem Venda", "Margem ERP"], horizontal=True)
            rows = []
            for item in st.session_state.lista_produtos:
                pf = item['PrecoUsado'] * (1 - item['DescontoPct']/100)
                fr, _ = identificar_frete(pf)
                if _ == "Manual": fr = item['FreteManual']
                luc = pf - (item['CMV'] + item['Extra'] + fr + (pf*(st.session_state.imposto_padrao+item['TaxaML'])/100)) + item['Bonus']
                
                mv = (luc/pf*100) if pf else 0
                me = (luc/item['PrecoERP']*100) if item['PrecoERP'] else 0
                m_analise = mv if visao == "Margem Venda" else me
                
                stt = 'Saudável'
                if m_analise < 8: stt = 'Crítico'
                elif m_analise < 15: stt = 'Atenção'
                
                rows.append({'Produto': item['Produto'], 'Margem': m_analise, 'Lucro': luc, 'Status': stt, 'Venda': pf})
            
            df = pd.DataFrame(rows)
            k1, k2 = st.columns(2)
            k1.metric("Produtos", len(df))
            k2.metric("Lucro Estimado", f"R$ {df['Lucro'].sum():.2f}")
            st.divider()
            
            # G1: Semáforo
            fig = px.bar(df['Status'].value_counts().reset_index(), x='Status', y='count', color='Status', 
                         color_discrete_map={'Crítico': '#EF4444', 'Atenção': '#F59E0B', 'Saudável': '#10B981'})
            st.plotly_chart(fig, use_container_width=True)
            
            # G2: Scatter
            fig2 = px.scatter(df, x='Venda', y='Margem', color='Status', hover_name='Produto', 
                             color_discrete_map={'Crítico': '#EF4444', 'Atenção': '#F59E0B', 'Saudável': '#10B981'})
            st.plotly_chart(fig2, use_container_width=True)
            
            # G3: Decomposição (Stacked)
            st.subheader("Anatomia do Preço (Top 10)")
            # (Simplificado para caber, usando dados já calculados seria ideal, aqui reusamos a estrutura)
            # Para manter simples, vamos focar nos dois gráficos principais aprovados.
        else:
            st.info("Sem dados.")
