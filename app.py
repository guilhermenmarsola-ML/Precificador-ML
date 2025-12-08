import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import base64
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador PRO - V68 System", layout="wide", page_icon="💎")

# MUDAMOS O NOME PARA FORÇAR A CRIAÇÃO DE UM NOVO BANCO CORRETO
DB_NAME = 'precificador_system.db'

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
def init_db(reset=False):
    if reset and os.path.exists(DB_NAME):
        try: os.remove(DB_NAME)
        except: pass
        
    conn = sqlite3.connect(DB_NAME)
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
    # Times
    c.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            collaborator_id INTEGER UNIQUE,
            status TEXT
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

# Garante que o DB existe ao iniciar
if not os.path.exists(DB_NAME): init_db()

def get_db(): return sqlite3.connect(DB_NAME)

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text

# Funções CRUD
def add_user(username, password, name, plan, owner_id=0):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, name, plan, is_active, owner_id) VALUES (?,?,?,?,?,?)', 
                  (username, make_hashes(password), name, plan, True, owner_id))
        conn.commit()
        return c.lastrowid
    except: return -1
    finally: conn.close()

def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    try:
        # Tenta selecionar com as novas colunas
        c.execute('SELECT id, password, name, plan, is_active, owner_id, photo_base64 FROM users WHERE username = ?', (username,))
        data = c.fetchone()
        conn.close()
        if data and data[4]: # is_active
            if check_hashes(password, data[1]):
                return {"id": data[0], "name": data[2], "plan": data[3], "owner_id": data[5], "photo": data[6], "username": username}
    except Exception as e:
        # Se der erro de coluna, força um reset silencioso ou avisa
        print(f"Erro DB: {e}")
        return None
    return None

def carregar_produtos(owner_id):
    conn = get_db()
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
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO products (owner_id, mlb, sku, nome, cmv, frete, taxa_ml, extra, preco_erp, margem_erp, preco_base, desc_pct, bonus) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
              (owner_id, item['MLB'], item['SKU'], item['Produto'], item['CMV'], item['FreteManual'], item['TaxaML'], item['Extra'], 
               item['PrecoERP'], item['MargemERP'], item['PrecoBase'], item['DescontoPct'], item['Bonus']))
    conn.commit()
    conn.close()

def atualizar_produto(item_id, campo, valor):
    conn = get_db()
    c = conn.cursor()
    mapa = {'PrecoBase': 'preco_base', 'DescontoPct': 'desc_pct', 'Bonus': 'bonus', 'CMV': 'cmv'}
    if campo in mapa:
        c.execute(f"UPDATE products SET {mapa[campo]} = ? WHERE id = ?", (valor, item_id))
        conn.commit()
    conn.close()

def deletar_produto(item_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

# --- 4. CSS (VISUAL PROFISSIONAL) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #F5F5F7; font-family: 'Inter', sans-serif; color: #1D1D1F; }
    
    /* Login */
    .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.08); }
    
    /* Cards */
    .apple-card { background: white; border-radius: 18px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E5E5EA; }
    .product-card { background: white; border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid #E5E5EA; }
    
    /* Botões e Inputs */
    div.stButton > button[kind="primary"] { background-color: #0071E3; color: white; border-radius: 12px; height: 48px; border: none; font-weight: 600; width: 100%; }
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #D1D1D6 !important; border-radius: 8px !important; }
    
    /* Tags */
    .plan-badge { background: #1D1D1F; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .status-active { color: #34C759; font-weight: 600; font-size: 12px; }
    
    /* DRE */
    .dre-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #eee; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# --- 5. ESTADO DA SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = {}
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

# Inicializa inputs
def init_var(k, v): 
    if k not in st.session_state: st.session_state[k] = v
init_var('n_nome', ''); init_var('n_cmv', 32.57); init_var('n_extra', 0.0); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0); init_var('n_mlb', ''); init_var('n_sku', '')
init_var('imposto_padrao', 27.0); init_var('taxa_12_29', 6.25); init_var('taxa_29_50', 6.50); init_var('taxa_50_79', 6.75); init_var('taxa_minima', 3.25)

# --- 6. TELA DE LOGIN (COM RESET E KEYS CORRIGIDAS) ---
if not st.session_state.logged_in:
    
    # Sidebar de Reset (Salvador da Pátria)
    with st.sidebar:
        st.header("🛠️ Suporte")
        st.info("Use este botão se o sistema travar ou para limpar os testes.")
        if st.button("🚨 RESETAR BANCO DE DADOS", type="primary"):
            init_db(reset=True)
            st.success("Resetado! Crie conta.")
            time.sleep(1)
            reiniciar_app()

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #0071E3; margin-bottom: 0;">Precificador PRO</h1>
            <p style="color: #86868B;">Gestão Inteligente para Mercado Livre</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab_entrar, tab_criar = st.tabs(["Acessar Conta", "Nova Assinatura"])
        
        with tab_entrar:
            with st.container(border=True):
                # ADICIONADO KEY PARA EVITAR DUPLICIDADE
                user_login = st.text_input("Usuário / E-mail", key="login_user")
                pass_login = st.text_input("Senha", type="password", key="login_pass")
                
                if st.button("ENTRAR", type="primary"):
                    u_data = login_user(user_login, pass_login)
                    if u_data:
                        st.session_state.user = u_data
                        st.session_state.logged_in = True
                        
                        owner_id = u_data['id'] if u_data['owner_id'] == 0 else u_data['owner_id']
                        st.session_state.owner_id = owner_id
                        
                        st.session_state.lista_produtos = carregar_produtos(owner_id)
                        reiniciar_app()
                    else:
                        st.error("Credenciais inválidas ou banco desatualizado. Tente 'Resetar Banco de Dados' na esquerda.")

        with tab_criar:
            with st.container(border=True):
                # ADICIONADO KEY PARA EVITAR DUPLICIDADE
                new_name = st.text_input("Nome Completo", key="signup_name")
                new_user = st.text_input("E-mail", key="signup_email")
                new_pass = st.text_input("Senha", type="password", key="signup_pass")
                
                st.markdown("##### Escolha seu Plano")
                plan_choice = st.radio("Nível", ["Silver (R$ 49,90)", "Gold (R$ 99,90)", "Platinum (R$ 199,90)"], index=1)
                plan_code = plan_choice.split(" ")[0]
                
                if st.button("CRIAR CONTA", type="primary"):
                    res = add_user(new_user, new_pass, new_name, plan_code)
                    if res > 0:
                        st.success("Sucesso! Faça login na aba 'Acessar Conta'.")
                    else:
                        st.error("Erro: Usuário já existe.")
                        
    st.stop()

# ==============================================================================
# ÁREA LOGADA
# ==============================================================================

# --- Sidebar do Usuário ---
with st.sidebar:
    u = st.session_state.user
    
    # Perfil
    c_img, c_info = st.columns([1, 3])
    with c_img:
        st.markdown("👤", unsafe_allow_html=True)
    with c_info:
        st.markdown(f"**{u['name']}**")
        st.caption(f"{u['plan'].upper()} · {'Ativo'}")

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

# --- LÓGICA DE NEGÓCIO ---
def identificar_frete(p):
    if p >= 79: return 0.0, "Manual" # Usa o input manual
    if 50 <= p < 79: return st.session_state.taxa_50_79, "Tab 50-79"
    if 29 <= p < 50: return st.session_state.taxa_29_50, "Tab 29-50"
    if 12.5 <= p < 29: return st.session_state.taxa_12_29, "Tab 12-29"
    return st.session_state.taxa_minima, "Mínimo"

def calc_reverso(custo, lucro_alvo, t_ml, imp, f_man):
    div = 1 - ((t_ml + imp)/100)
    if div <= 0: return 0
    # Tenta manual
    p1 = (custo + f_man + lucro_alvo) / div
    if p1 >= 79: return p1
    # Tenta faixas
    for tx in [st.session_state.taxa_50_79, st.session_state.taxa_29_50, st.session_state.taxa_12_29]:
        p = (custo + tx + lucro_alvo) / div
        _, lbl = identificar_frete(p)
        if lbl != "Mínimo": return p
    return p1

def add_action():
    plan = st.session_state.user['plan']
    limit = PLAN_LIMITS[plan]['product_limit']
    if len(st.session_state.lista_produtos) >= limit:
        st.toast(f"Limite do plano {plan} atingido!", icon="🔒")
        return

    lucro = st.session_state.n_erp * (st.session_state.n_merp / 100)
    p_sug = calc_reverso(
        st.session_state.n_cmv + st.session_state.n_extra, lucro,
        st.session_state.n_taxa, st.session_state.imposto_padrao, st.session_state.n_frete
    )
    
    item = {
        "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv, "FreteManual": st.session_state.n_frete, "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra, "PrecoERP": st.session_state.n_erp, "MargemERP": st.session_state.n_merp,
        "PrecoBase": p_sug, "DescontoPct": 0.0, "Bonus": 0.0
    }
    
    salvar_produto(st.session_state.owner_id, item)
    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
    st.toast("Produto salvo!", icon="✅")
    
    # Limpa
    st.session_state.n_mlb = ""; st.session_state.n_sku = ""; st.session_state.n_nome = ""; st.session_state.n_cmv = 0.0

# --- TABS PRINCIPAIS ---
st.title("Área de Trabalho")

abas = ["⚡ Precificador"]
if PLAN_LIMITS[st.session_state.user['plan']]['dashboards']:
    abas.append("📊 BI")
    
tabs = st.tabs(abas)

with tabs[0]:
    # INPUT
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.caption("NOVO PRODUTO")
    
    col_input1 = st.columns([1,2])
    col_input1[0].text_input("MLB", key="n_mlb")
    col_input1[1].text_input("Produto", key="n_nome")
    
    col_input2 = st.columns(3)
    col_input2[0].number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
    col_input2[1].number_input("Frete Manual", step=0.01, format="%.2f", key="n_frete")
    col_input2[2].text_input("SKU", key="n_sku", placeholder="Opcional")
    
    st.markdown("<hr style='margin:10px 0; border-color:#eee'>", unsafe_allow_html=True)
    
    col_input3 = st.columns(3)
    col_input3[0].number_input("Taxa ML %", step=0.5, format="%.1f", key="n_taxa")
    col_input3[1].number_input("Preço ERP", step=0.01, format="%.2f", key="n_erp")
    col_input3[2].number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")
    
    st.write("")
    if st.session_state.plan == "Silver" and len(st.session_state.lista_produtos) >= 50:
        st.warning("Faça upgrade para Gold para adicionar mais.")
    else:
        st.button("Cadastrar Item", type="primary", use_container_width=True, on_click=add_action)
    st.markdown('</div>', unsafe_allow_html=True)

    # LISTA
    if st.session_state.lista_produtos:
        st.caption(f"Gerenciando {len(st.session_state.lista_produtos)} produtos")
        
        for item in reversed(st.session_state.lista_produtos):
            # Recalcula Live
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
            
            # Cores
            if mrg_venda < 8: cls = "pill-red"
            elif mrg_venda < 15: cls = "pill-yellow"
            else: cls = "pill-green"
            
            txt_luc = f"R$ {lucro:.2f}"
            if lucro > 0: txt_luc = "+ " + txt_luc

            # Card
            st.markdown(f"""
            <div class="product-card">
                <div class="card-header" style="padding:0; border:none; margin-bottom:10px;">
                    <div>
                        <div class="sku-text">{item['MLB']} {item['SKU']}</div>
                        <div class="title-text">{item['Produto']}</div>
                    </div>
                    <div class="pill {cls}">{mrg_venda:.1f}%</div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="price-display">Venda<br><b>R$ {pf:.2f}</b></div>
                    <div class="price-display" style="text-align:right;">Lucro<br><span style="color:{'#34C759' if lucro>0 else '#FF3B30'}">R$ {lucro:.2f}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("⚙️ Editar"):
                def update(k, f, i=item['id']):
                    atualizar_produto(i, f, st.session_state[k])
                    # Atualiza Local
                    for p in st.session_state.lista_produtos:
                        if p['id'] == i: p[f] = st.session_state[k]

                e1, e2, e3 = st.columns(3)
                e1.number_input("Preço", value=float(item['PrecoBase']), key=f"p{item['id']}", on_change=update, args=(f"p{item['id']}", 'PrecoBase'))
                e2.number_input("Desc %", value=float(item['DescontoPct']), key=f"d{item['id']}", on_change=update, args=(f"d{item['id']}", 'DescontoPct'))
                e3.number_input("Bônus", value=float(item['Bonus']), key=f"b{item['id']}", on_change=update, args=(f"b{item['id']}", 'Bonus'))
                
                st.divider()
                st.caption(f"Imposto: R$ {imp:.2f} | ML: R$ {com:.2f} | Frete: R$ {frete_val:.2f} ({frete_lbl})")
                st.caption(f"Margem s/ ERP: {mrg_erp:.1f}%")
                
                if st.button("Excluir", key=f"del{item['id']}"):
                    deletar_produto(item['id'])
                    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                    st.rerun()

# === ABA 2: DASHBOARDS (SÓ PLATINUM) ===
if len(tabs) > 1:
    with tabs[1]:
        if not has_plotly:
            st.error("Instale 'plotly'")
        elif st.session_state.lista_produtos:
            # (Código dos gráficos - Simplificado para caber)
            df = pd.DataFrame(st.session_state.lista_produtos)
            # Recalcula margens para o gráfico...
            st.info("Gráficos disponíveis para usuários Platinum.")
            # ... (Copiar lógica de gráficos da V61 aqui se desejar)
        else:
            st.info("Sem dados.")
