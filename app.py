import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import base64
import os

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador PRO - V69 Stable", layout="wide", page_icon="💎")
DB_NAME = 'precificador_v70.db' # Banco Novo

# --- 2. FUNÇÕES AUXILIARES ---
def reiniciar_app():
    time.sleep(0.1)
    if hasattr(st, 'rerun'): st.rerun()
    else: st.experimental_rerun()

# Verifica Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# Planos
PLAN_LIMITS = {
    "Silver": {"product_limit": 50, "collab_limit": 1, "dashboards": False, "price": "R$ 49,90"},
    "Gold": {"product_limit": 999999, "collab_limit": 4, "dashboards": False, "price": "R$ 99,90"},
    "Platinum": {"product_limit": 999999, "collab_limit": 999999, "dashboards": True, "price": "R$ 199,90"}
}
PLANS_ORDER = ["Silver", "Gold", "Platinum"]

# --- 3. BANCO DE DADOS ---
def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db(reset=False):
    if reset:
        if os.path.exists(DB_NAME):
            try: os.remove(DB_NAME)
            except: pass
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            name TEXT,
            plan TEXT,
            is_active BOOLEAN,
            photo_base64 TEXT,
            owner_id INTEGER DEFAULT 0
        )
    ''')
    # Produtos
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            mlb TEXT, sku TEXT, nome TEXT,
            cmv REAL, frete REAL, taxa_ml REAL, extra REAL,
            preco_erp REAL, margem_erp REAL,
            preco_base REAL, desc_pct REAL, bonus REAL
        )
    ''')
    conn.commit()
    conn.close()

# Garante inicialização
if not os.path.exists(DB_NAME): init_db()

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# --- FUNÇÕES CRUD (NOMES UNIFICADOS) ---

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
        if data:
            # 0:id, 1:user, 2:pass, 3:name, 4:plan, 5:active, 6:photo, 7:owner
            if data[5] and check_hashes(password, data[2]):
                return {
                    "id": data[0], "name": data[3], "plan": data[4], 
                    "owner_id": data[7], "photo": data[6], "username": username
                }
    except: pass
    finally: conn.close()
    return None

def carregar_produtos(owner_id):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM products WHERE owner_id = ?", conn, params=(owner_id,))
        lista = []
        for _, row in df.iterrows():
            lista.append({
                "id": row['id'], "MLB": row['mlb'], "SKU": row['sku'], "Produto": row['nome'],
                "CMV": row['cmv'], "FreteManual": row['frete'], "TaxaML": row['taxa_ml'], "Extra": row['extra'],
                "PrecoERP": row['preco_erp'], "MargemERP": row['margem_erp'],
                "PrecoBase": row['preco_base'], "DescontoPct": row['desc_pct'], "Bonus": row['bonus']
            })
        return lista
    except: return []
    finally: conn.close()

def salvar_produto(owner_id, item):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO products (owner_id, mlb, sku, nome, cmv, frete, taxa_ml, extra, preco_erp, margem_erp, preco_base, desc_pct, bonus) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
              (owner_id, item['MLB'], item['SKU'], item['Produto'], item['CMV'], item['FreteManual'], item['TaxaML'], item['Extra'], 
               item['PrecoERP'], item['MargemERP'], item['PrecoBase'], item['DescontoPct'], item['Bonus']))
    conn.commit()
    conn.close()

def atualizar_produto(item_id, campo, valor):
    conn = get_db_connection()
    c = conn.cursor()
    # Mapa de nomes do App -> Colunas do Banco
    mapa = {'PrecoBase': 'preco_base', 'DescontoPct': 'desc_pct', 'Bonus': 'bonus', 'CMV': 'cmv'}
    if campo in mapa:
        c.execute(f"UPDATE products SET {mapa[campo]} = ? WHERE id = ?", (valor, item_id))
        conn.commit()
    conn.close()

def deletar_produto(item_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

# --- 4. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #F5F5F7; font-family: 'Inter', sans-serif; color: #1D1D1F; }
    
    .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.08); }
    .apple-card { background: white; border-radius: 18px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E5E5EA; }
    .product-card { background: white; border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid #E5E5EA; }
    
    div.stButton > button[kind="primary"] { background-color: #0071E3; color: white; border-radius: 12px; height: 48px; border: none; font-weight: 600; width: 100%; }
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #D1D1D6 !important; border-radius: 8px !important; }
    
    .plan-badge { background: #1D1D1F; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .pill { padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }
    .pill-green { background-color: #E6FFFA; color: #047857; }
    .pill-yellow { background-color: #FFFBEB; color: #B45309; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; }
    
    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .price-display { font-size: 14px; color: #1D1D1F; font-weight: 500; }
    
    .card-footer { background-color: #F8F9FA; padding: 10px 20px; border-top: 1px solid #F0F0F0; display: flex; justify-content: space-between; font-size: 11px; color: #666; }
    .margin-box { text-align: center; flex: 1; }
    .margin-val { font-weight: 700; font-size: 12px; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 5. SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = {}
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

def init_var(k, v): 
    if k not in st.session_state: st.session_state[k] = v
init_var('n_nome', ''); init_var('n_cmv', 32.57); init_var('n_extra', 0.0); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0); init_var('n_mlb', ''); init_var('n_sku', '')
init_var('imposto_padrao', 27.0); init_var('taxa_12_29', 6.25); init_var('taxa_29_50', 6.50); init_var('taxa_50_79', 6.75); init_var('taxa_minima', 3.25)

# --- 6. LOGIN ---
if not st.session_state.logged_in:
    with st.sidebar:
        st.header("Suporte")
        if st.button("🚨 RESET TOTAL", type="primary"):
            init_db(reset=True)
            st.success("Sistema resetado.")
            time.sleep(1)
            reiniciar_app()

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center; color:#0071E3;'>Precificador PRO</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
        
        with tab1:
            with st.container(border=True):
                u_login = st.text_input("Usuário", key="login_u")
                p_login = st.text_input("Senha", type="password", key="login_p")
                if st.button("ENTRAR", type="primary"):
                    res = login_user(u_login, p_login)
                    if res:
                        st.session_state.user = res
                        st.session_state.logged_in = True
                        st.session_state.owner_id = res['id'] if res['owner_id'] == 0 else res['owner_id']
                        st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                        reiniciar_app()
                    else: st.error("Erro de login.")
        
        with tab2:
            with st.container(border=True):
                n_name = st.text_input("Nome", key="reg_n")
                n_user = st.text_input("E-mail", key="reg_u")
                n_pass = st.text_input("Senha", type="password", key="reg_p")
                plan_full = st.selectbox("Plano", ["Silver (R$49)", "Gold (R$99)", "Platinum (R$199)"])
                if st.button("CRIAR CONTA", type="primary"):
                    if add_user(n_user, n_pass, n_name, plan_full.split()[0]) > 0:
                        st.success("Criado! Faça login.")
                    else: st.error("Erro ao criar.")
    st.stop()

# ==============================================================================
# ÁREA LOGADA
# ==============================================================================

with st.sidebar:
    u = st.session_state.user
    st.markdown(f"**{u['name']}**")
    st.caption(f"Plano: {u['plan']}")
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

# --- LÓGICA ---
def identificar_frete(p):
    if p >= 79: return 0.0, "Manual"
    if 50 <= p < 79: return st.session_state.taxa_50_79, "Tab 50-79"
    if 29 <= p < 50: return st.session_state.taxa_29_50, "Tab 29-50"
    if 12.5 <= p < 29: return st.session_state.taxa_12_29, "Tab 12-29"
    return st.session_state.taxa_minima, "Mínimo"

def calc_reverso(custo, alvo, t_ml, imp, f_man):
    div = 1 - ((t_ml + imp)/100)
    if div <= 0: return 0
    p1 = (custo + f_man + alvo) / div
    if p1 >= 79: return p1
    for tx in [st.session_state.taxa_50_79, st.session_state.taxa_29_50, st.session_state.taxa_12_29]:
        p = (custo + tx + alvo) / div
        _, lbl = identificar_frete(p)
        if lbl != "Mínimo": return p
    return p1

def add_action():
    if not st.session_state.n_nome: return
    lucro = st.session_state.n_erp * (st.session_state.n_merp / 100)
    p_sug = calc_reverso(st.session_state.n_cmv + st.session_state.n_extra, lucro, st.session_state.n_taxa, st.session_state.imposto_padrao, st.session_state.n_frete)
    
    item = {
        "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv, "FreteManual": st.session_state.n_frete, "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra, "PrecoERP": st.session_state.n_erp, "MargemERP": st.session_state.n_merp,
        "PrecoBase": p_sug, "DescontoPct": 0.0, "Bonus": 0.0
    }
    salvar_produto(st.session_state.owner_id, item)
    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
    st.toast("Salvo!", icon="✅")
    st.session_state.n_mlb = ""; st.session_state.n_sku = ""; st.session_state.n_nome = ""; st.session_state.n_cmv = 0.0

st.title("Área de Trabalho")
abas = ["⚡ Precificador"]
if PLAN_LIMITS[st.session_state.user['plan']]['dashboards']: abas.append("📊 BI")
tabs = st.tabs(abas)

with tabs[0]:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.caption("NOVO PRODUTO")
    c1, c2 = st.columns([1,2])
    c1.text_input("MLB", key="n_mlb")
    c2.text_input("Produto", key="n_nome")
    c3, c4, c5 = st.columns(3)
    c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
    c4.number_input("Frete Manual", step=0.01, format="%.2f", key="n_frete")
    c5.number_input("Extras", step=0.01, format="%.2f", key="n_extra")
    st.markdown("<hr style='margin:10px 0; border-color:#eee'>", unsafe_allow_html=True)
    c6, c7, c8 = st.columns(3)
    c6.number_input("Taxa ML %", step=0.5, format="%.1f", key="n_taxa")
    c7.number_input("Preço ERP", step=0.01, format="%.2f", key="n_erp")
    c8.number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")
    st.write("")
    st.button("CADASTRAR", type="primary", on_click=add_action)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.lista_produtos:
        st.caption(f"{len(st.session_state.lista_produtos)} produtos")
        for item in reversed(st.session_state.lista_produtos):
            pf = item['PrecoBase'] * (1 - item['DescontoPct']/100)
            frete_val, frete_lbl = identificar_frete(pf)
            if frete_lbl == "Manual": frete_val = item['FreteManual']
            
            imp = pf * (st.session_state.imposto_padrao/100)
            com = pf * (item['TaxaML']/100)
            custos = item['CMV'] + item['Extra'] + frete_val + imp + com
            lucro = pf - custos + item['Bonus']
            mrg_venda = (lucro/pf*100) if pf > 0 else 0
            erp_safe = item['PrecoERP'] if item['PrecoERP'] > 0 else 1
            mrg_erp = (lucro/erp_safe*100)
            
            cls = "pill-green"
            if mrg_venda < 8: cls = "pill-red"
            elif mrg_venda < 15: cls = "pill-yellow"
            
            st.markdown(f"""
            <div class="product-card">
                <div class="card-header" style="padding:0; border:none; margin-bottom:10px;">
                    <div><div class="sku-text">{item['MLB']} {item['SKU']}</div><div class="title-text">{item['Produto']}</div></div>
                    <div class="pill {cls}">{mrg_venda:.1f}%</div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="price-display">Venda<br><b>R$ {pf:.2f}</b></div>
                    <div class="price-display" style="text-align:right;">Lucro<br><span style="color:{'#34C759' if lucro>0 else '#FF3B30'}">R$ {lucro:.2f}</span></div>
                </div>
                <div class="card-footer">
                   <div class="margin-box"><div>Margem Venda</div><div class="margin-val">{mrg_venda:.1f}%</div></div>
                   <div class="margin-box" style="border-left: 1px solid #eee;"><div>Margem ERP</div><div class="margin-val">{mrg_erp:.1f}%</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("⚙️ Editar"):
                def update(k, f, i=item['id']):
                    atualizar_produto(i, f, st.session_state[k])
                    for p in st.session_state.lista_produtos:
                        if p['id'] == i: p[f] = st.session_state[k]

                e1, e2, e3 = st.columns(3)
                e1.number_input("Preço", value=float(item['PrecoBase']), key=f"p{item['id']}", on_change=update, args=(f"p{item['id']}", 'PrecoBase'))
                e2.number_input("Desc %", value=float(item['DescontoPct']), key=f"d{item['id']}", on_change=update, args=(f"d{item['id']}", 'DescontoPct'))
                e3.number_input("Bônus", value=float(item['Bonus']), key=f"b{item['id']}", on_change=update, args=(f"b{item['id']}", 'Bonus'))
                
                st.divider()
                st.caption(f"Imposto: R$ {imp:.2f} | ML: R$ {com:.2f} | Frete: R$ {frete_val:.2f}")
                if st.button("Excluir", key=f"del{item['id']}"):
                    deletar_produto(item['id'])
                    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                    st.rerun()

if len(tabs) > 1:
    with tabs[1]:
        if has_plotly and st.session_state.lista_produtos:
            df = pd.DataFrame(st.session_state.lista_produtos)
            df['pf'] = df['PrecoBase'] * (1 - df['DescontoPct']/100)
            df['lucro'] = df.apply(lambda x: x['pf'] - (x['CMV'] + x['Extra'] + (x['pf']*(st.session_state.imposto_padrao+x['TaxaML'])/100)), axis=1)
            fig = px.bar(df, x='Produto', y='lucro', title="Lucro por Produto")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Sem dados ou Plotly ausente.")
