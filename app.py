import streamlit as st
import pandas as pd
import time
import re
import sqlite3
import hashlib
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO (APP SHELL) ---
st.set_page_config(page_title="Precificador PRO - V77 Stable", layout="wide", page_icon="💎")
DB_NAME = 'precificador_v77.db' # Banco Novo para garantir estrutura limpa

# Verifica Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# --- 2. SISTEMA SAAS (BANCO DE DADOS E LOGIN) ---

PLAN_LIMITS = {
    "Silver": {"limit": 50, "dash": False, "desc": "Até 50 produtos"},
    "Gold": {"limit": 999999, "dash": False, "desc": "Produtos Ilimitados"},
    "Platinum": {"limit": 999999, "dash": True, "desc": "Ilimitado + Dashboards BI"}
}

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE, password TEXT, name TEXT, plan TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            MLB TEXT, SKU TEXT, Produto TEXT,
            CMV REAL, FreteManual REAL, Extra REAL,
            TaxaML REAL, PrecoERP REAL, MargemERP REAL,
            PrecoBase REAL, DescontoPct REAL, Bonus REAL,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_NAME): init_db()

def get_db(): return sqlite3.connect(DB_NAME, check_same_thread=False)
def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# CRUD Usuários
def create_user(user, pw, name, plan):
    conn = get_db(); c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, name, plan) VALUES (?,?,?,?)', 
                  (user, make_hashes(pw), name, plan))
        conn.commit()
        return c.lastrowid
    except: return -1
    finally: conn.close()

def login_user(user, pw):
    conn = get_db(); c = conn.cursor()
    try:
        c.execute('SELECT * FROM users WHERE username = ?', (user,))
        data = c.fetchone()
        if data and check_hashes(pw, data[2]):
            return {"id": data[0], "username": data[1], "name": data[3], "plan": data[4]}
    except: pass
    finally: conn.close()
    return None

# CRUD Produtos
def load_products(user_id):
    conn = get_db()
    try:
        df = pd.read_sql_query("SELECT * FROM products WHERE owner_id = ?", conn, params=(user_id,))
        return df.to_dict('records')
    except: return []
    finally: conn.close()

def save_product(user_id, item):
    conn = get_db(); c = conn.cursor()
    c.execute('''INSERT INTO products (owner_id, MLB, SKU, Produto, CMV, FreteManual, Extra, TaxaML, PrecoERP, MargemERP, PrecoBase, DescontoPct, Bonus)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
              (user_id, item.get('MLB',''), item.get('SKU',''), item.get('Produto',''), item.get('CMV',0), item.get('FreteManual',0), item.get('Extra',0), 
               item.get('TaxaML',0), item.get('PrecoERP',0), item.get('MargemERP',0), item.get('PrecoBase',0), item.get('DescontoPct',0), item.get('Bonus',0)))
    conn.commit(); conn.close()

def update_product_field(prod_id, field, value):
    conn = get_db(); c = conn.cursor()
    valid_fields = ['PrecoBase', 'DescontoPct', 'Bonus', 'CMV', 'FreteManual', 'TaxaML', 'PrecoERP', 'MargemERP']
    if field in valid_fields:
        c.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, prod_id))
        conn.commit()
    conn.close()

def delete_product(prod_id):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit(); conn.close()

# --- 3. ESTADO E FUNÇÕES ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = {}
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

def reiniciar_app():
    time.sleep(0.1)
    if hasattr(st, 'rerun'): st.rerun()
    else: st.experimental_rerun()

def init_var(key, value):
    if key not in st.session_state: st.session_state[key] = value

init_var('n_mlb', ''); init_var('n_sku', ''); init_var('n_nome', '')
init_var('n_cmv', 32.57); init_var('n_extra', 0.00); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0)
init_var('imposto_padrao', 27.0) 
init_var('taxa_12_29', 6.25); init_var('taxa_29_50', 6.50); init_var('taxa_50_79', 6.75); init_var('taxa_minima', 3.25)

# --- FUNÇÃO DE AUTO-REPARO (CORREÇÃO DO KEYERROR) ---
def sanear_dados():
    """Garante que todo produto tenha todas as chaves necessárias"""
    if st.session_state.lista_produtos:
        fixed_list = []
        for p in st.session_state.lista_produtos:
            # Preenche defaults se faltar
            if 'PrecoBase' not in p: p['PrecoBase'] = 0.0
            if 'DescontoPct' not in p: p['DescontoPct'] = 0.0
            if 'Bonus' not in p: p['Bonus'] = 0.0
            if 'CMV' not in p: p['CMV'] = 0.0
            if 'PrecoERP' not in p: p['PrecoERP'] = 0.0
            if 'MargemERP' not in p: p['MargemERP'] = 0.0
            if 'TaxaML' not in p: p['TaxaML'] = 16.5
            if 'FreteManual' not in p: p['FreteManual'] = 0.0
            if 'Extra' not in p: p['Extra'] = 0.0
            if 'Produto' not in p: p['Produto'] = 'Sem Nome'
            if 'MLB' not in p: p['MLB'] = ''
            if 'SKU' not in p: p['SKU'] = ''
            fixed_list.append(p)
        st.session_state.lista_produtos = fixed_list

# Roda saneamento ao iniciar
sanear_dados()

# --- 4. TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("""<style>.login-box {background:white;padding:40px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.05);border:1px solid #eee;}.stApp {background-color:#F5F5F7;}</style>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align:center; color:#1D1D1F;'>Precificador <span style='color:#0071E3'>PRO</span></h1>", unsafe_allow_html=True)
        tab_login, tab_sign = st.tabs(["Acessar", "Criar Conta"])
        with tab_login:
            with st.container(border=True):
                u = st.text_input("Email", key="l_u")
                p = st.text_input("Senha", type="password", key="l_p")
                if st.button("Entrar", type="primary", use_container_width=True):
                    user = login_user(u, p)
                    if user:
                        st.session_state.user = user
                        st.session_state.logged_in = True
                        st.session_state.lista_produtos = load_products(user['id'])
                        sanear_dados() # Garante integridade pós-login
                        reiniciar_app()
                    else: st.error("Dados incorretos.")
        with tab_sign:
            with st.container(border=True):
                nu = st.text_input("Seu Email", key="r_u")
                nn = st.text_input("Seu Nome", key="r_n")
                np = st.text_input("Crie uma Senha", type="password", key="r_p")
                npl = st.selectbox("Escolha o Plano", ["Silver", "Gold", "Platinum"])
                if st.button("Começar Agora", type="primary", use_container_width=True):
                    if create_user(nu, np, nn, npl.split()[0]) > 0: st.success("Criado! Faça login.")
                    else: st.error("Erro ao criar.")
    st.stop()

# ==============================================================================
# APLICAÇÃO LOGADA
# ==============================================================================

# --- CSS (VISUAL APROVADO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'Inter', sans-serif; }
    .input-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05); border: 1px solid #EFEFEF; margin-bottom: 20px; }
    .feed-card { background: white; border-radius: 16px; border: 1px solid #DBDBDB; box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin-bottom: 15px; overflow: hidden; }
    .card-header { padding: 15px 20px; border-bottom: 1px solid #F0F0F0; display: flex; justify-content: space-between; align-items: center; }
    .card-body { padding: 20px; text-align: center; }
    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .price-hero { font-size: 32px; font-weight: 800; letter-spacing: -1px; color: #262626; margin: 5px 0; }
    .pill { padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }
    .pill-green { background-color: #E6FFFA; color: #047857; border: 1px solid #D1FAE5; }
    .pill-yellow { background-color: #FFFBEB; color: #B45309; border: 1px solid #FCD34D; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FEE2E2; }
    .audit-box { background-color: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 8px; padding: 15px; font-family: 'Courier New', monospace; font-size: 12px; color: #333; margin-top: 10px; }
    .audit-line { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .audit-bold { font-weight: bold; color: #000; }
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #E5E5E5 !important; color: #333 !important; border-radius: 8px !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; border-radius: 10px; height: 50px; border: none; font-weight: 600; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); }
    .plan-badge { background: #1D1D1F; color: white; padding: 4px 10px; border-radius: 4px; font-size: 10px; font-weight: bold; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE CÁLCULO ---
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

def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0, "Acima de 79 (Manual)"
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", st.session_state.taxa_50_79, "Faixa R$ 50-79"
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", st.session_state.taxa_29_50, "Faixa R$ 29-50"
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", st.session_state.taxa_12_29, "Faixa R$ 12-29"
    else: return "Tab. Mínima", st.session_state.taxa_minima, "Abaixo de R$ 12.50"

def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_ml_pct, imposto_pct, frete_manual):
    custos_fixos_1 = custo_base + frete_manual
    divisor = 1 - ((taxa_ml_pct + imposto_pct) / 100)
    if divisor <= 0: return 0.0, "Erro"
    preco_est_1 = (custos_fixos_1 + lucro_alvo_reais) / divisor
    if preco_est_1 >= 79.00: return preco_est_1, "Frete Manual"
    for taxa, nome, p_min, p_max in [
        (st.session_state.taxa_50_79, "Tab. 50-79", 50, 79), 
        (st.session_state.taxa_29_50, "Tab. 29-50", 29, 50), 
        (st.session_state.taxa_12_29, "Tab. 12-29", 12.5, 29)
    ]:
        custos = custo_base + taxa
        preco = (custos + lucro_alvo_reais) / divisor
        if p_min <= preco < p_max: return preco, nome
    return preco_est_1, "Frete Manual"

def adicionar_produto_action():
    plano_atual = st.session_state.user['plan']
    limit = PLAN_LIMITS[plano_atual]['limit']
    if len(st.session_state.lista_produtos) >= limit:
        st.toast(f"Limite do plano atingido!", icon="🔒")
        return

    if not st.session_state.n_nome:
        st.toast("Nome obrigatório!", icon="⚠️")
        return
    lucro_alvo = st.session_state.n_erp * (st.session_state.n_merp / 100)
    preco_sug, _ = calcular_preco_sugerido_reverso(
        st.session_state.n_cmv + st.session_state.n_extra, lucro_alvo,
        st.session_state.n_taxa, st.session_state.imposto_padrao, st.session_state.n_frete
    )
    
    item = {
        "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, 
        "Produto": st.session_state.n_nome, "CMV": st.session_state.n_cmv, 
        "FreteManual": st.session_state.n_frete, "TaxaML": st.session_state.n_taxa, 
        "Extra": st.session_state.n_extra, "PrecoERP": st.session_state.n_erp, 
        "MargemERP": st.session_state.n_merp, 
        "PrecoBase": preco_sug, "DescontoPct": 0.0, "Bonus": 0.0
    }
    
    save_product(st.session_state.user['id'], item)
    st.session_state.lista_produtos = load_products(st.session_state.user['id'])
    
    st.toast("Salvo!", icon="✅")
    st.session_state.n_mlb = ""; st.session_state.n_sku = ""; st.session_state.n_nome = ""; st.session_state.n_cmv = 0.0

# --- SIDEBAR (USUÁRIO) ---
with st.sidebar:
    u = st.session_state.user
    st.markdown(f"### Olá, {u['name']}")
    st.markdown(f"<span class='plan-badge'>{u['plan'].upper()}</span>", unsafe_allow_html=True)
    if st.button("Sair", key="logout"):
        st.session_state.logged_in = False
        reiniciar_app()
    
    st.divider()
    st.header("Ajustes")
    st.session_state.imposto_padrao = st.number_input("Impostos (%)", value=st.session_state.imposto_padrao, step=0.5)
    with st.expander("Frete ML (<79)", expanded=True):
        st.session_state.taxa_12_29 = st.number_input("12-29", value=st.session_state.taxa_12_29)
        st.session_state.taxa_29_50 = st.number_input("29-50", value=st.session_state.taxa_29_50)
        st.session_state.taxa_50_79 = st.number_input("50-79", value=st.session_state.taxa_50_79)
        st.session_state.taxa_minima = st.number_input("Min", value=st.session_state.taxa_minima)
    st.divider()
    
    # IMPORTAÇÃO (Simplificada)
    st.markdown("### 📂 Importar")
    uploaded_file = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
    if uploaded_file and st.button("Importar"):
        try:
            xl = pd.ExcelFile(uploaded_file)
            df = xl.parse(0)
            cols = [str(c).lower() for c in df.columns]
            for _, row in df.iterrows():
                try:
                    # Busca simplificada
                    def find_col(k): return next((c for c in df.columns if k.lower() in str(c).lower()), None)
                    p = row[find_col("Produto")]
                    c = limpar_valor_dinheiro(row[find_col("CMV")])
                    pb = limpar_valor_dinheiro(row[find_col("Preço")])
                    
                    item = {
                        "MLB": str(row.get(find_col("MLB"), "")), "SKU": "", "Produto": p,
                        "CMV": c, "FreteManual": 18.86, "TaxaML": 16.5, "Extra": 0.0,
                        "PrecoERP": pb, "MargemERP": 20.0, "PrecoBase": pb, "DescontoPct": 0.0, "Bonus": 0.0
                    }
                    save_product(st.session_state.user['id'], item)
                except: pass
            st.session_state.lista_produtos = load_products(st.session_state.user['id'])
            st.success("Importado!")
        except: st.error("Erro no arquivo")

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================

st.markdown('<div style="text-align:center; padding-bottom:10px;">', unsafe_allow_html=True)
st.title("Precificador 2026")
st.markdown('</div>', unsafe_allow_html=True)

# Lógica de Abas conforme Plano
abas = ["⚡ Operacional"]
if PLAN_LIMITS[st.session_state.user['plan']]['dash']:
    abas.append("📊 Dashboards")
    
tab_op, tab_bi = st.tabs(abas) if len(abas) > 1 else (st.tabs(abas)[0], None)

# --- ABA 1: OPERACIONAL ---
with tab_op:
    
    # BUSCA AUTOCOMPLETE
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
            if 'PrecoBase' not in item: continue
            
            pf = item['PrecoBase'] * (1 - item['DescontoPct']/100)
            _, fr, _ = identificar_faixa_frete(pf)
            if _ == "manual": fr = item['FreteManual']
            luc = pf - (item['CMV'] + item['Extra'] + fr + (pf*(st.session_state.imposto_padrao+item['TaxaML'])/100)) + item['Bonus']
            mrg = (luc/pf*100) if pf else 0
            
            view_item = item.copy()
            view_item.update({'_pf': pf, '_mrg': mrg})
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
        st.button("Cadastrar Item", type="primary", use_container_width=True, on_click=adicionar_produto_action)
        st.markdown('</div>', unsafe_allow_html=True)

    if lista_final:
        st.caption(f"Visualizando {len(lista_final)} produtos")
        for item in lista_final:
            
            # CÁLCULO
            pf = item['PrecoBase'] * (1 - item['DescontoPct']/100)
            
            nome_frete_real, valor_frete_real, motivo_frete = identificar_faixa_frete(pf)
            if nome_frete_real == "manual": valor_frete_real = item['FreteManual']
            
            imposto_val = pf * (st.session_state.imposto_padrao / 100)
            comissao_val = pf * (item['TaxaML'] / 100)
            custos_totais = item['CMV'] + item['Extra'] + valor_frete_real + imposto_val + comissao_val
            lucro_final = pf - custos_totais + item['Bonus']
            margem_final = (lucro_final / pf * 100) if pf > 0 else 0
            
            # Cores
            if margem_final < 8.0: pill_cls = "pill-red"
            elif 8.0 <= margem_final < 15.0: pill_cls = "pill-yellow"
            else: pill_cls = "pill-green"

            txt_pill = f"{margem_final:.1f}%"
            txt_luc = f"+ R$ {lucro_final:.2f}" if lucro_final > 0 else f"- R$ {abs(lucro_final):.2f}"
            sku_show = item.get('SKU', '')
            
            st.markdown(f"""
            <div class="feed-card">
                <div class="card-header">
                    <div><div class="sku-text">{item['MLB']} {sku_show}</div><div class="title-text">{item['Produto']}</div></div>
                    <div class="{pill_cls} pill">{txt_pill}</div>
                </div>
                <div class="card-body">
                    <div style="font-size: 11px; color:#888; font-weight:600;">PREÇO DE VENDA</div>
                    <div class="price-hero">R$ {pf:.2f}</div>
                    <div style="font-size: 13px; color:#555;">Lucro Líquido: <b>{txt_luc}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚙️ Editar e Detalhes"):
                # Callback de Edição (Salva no DB)
                def up(k, f, i=item['id']): 
                    update_product_field(i, f, st.session_state[k])
                    # Atualiza Local
                    for idx, p in enumerate(st.session_state.lista_produtos):
                        if p['id'] == i: st.session_state.lista_produtos[idx][f] = st.session_state[k]

                e1, e2, e3 = st.columns(3)
                e1.number_input("Preço Tabela (Usado)", value=float(item['PrecoBase']), key=f"p{item['id']}", on_change=up, args=(f"p{item['id']}", 'PrecoBase'))
                e2.number_input("Desc %", value=float(item['DescontoPct']), key=f"d{item['id']}", on_change=up, args=(f"d{item['id']}", 'DescontoPct'))
                e3.number_input("Bônus", value=float(item['Bonus']), key=f"b{item['id']}", on_change=up, args=(f"b{item['id']}", 'Bonus'))
                
                st.divider()
                
                # --- DRE V64 (APROVADA) ---
                st.markdown("##### 🧮 Memória de Cálculo")
                st.markdown(f"""
                <div class="audit-box">
                    <div class="audit-line"><span>(+) Preço Tabela</span> <span>R$ {item['PrecoBase']:.2f}</span></div>
                    <div class="audit-line" style="color:red;"><span>(-) Desconto ({item['DescontoPct']}%)</span> <span>R$ {item['PrecoBase'] - pf:.2f}</span></div>
                    <div class="audit-line audit-bold"><span>(=) VENDA FINAL</span> <span>R$ {pf:.2f}</span></div>
                    <br>
                    <div class="audit-line"><span>(-) Impostos ({st.session_state.imposto_padrao}%)</span> <span>R$ {imposto_val:.2f}</span></div>
                    <div class="audit-line"><span>(-) Comissão ({item['TaxaML']}%)</span> <span>R$ {comissao_val:.2f}</span></div>
                    <div class="audit-line"><span>(-) Frete ({nome_frete_real})</span> <span>R$ {valor_frete_real:.2f}</span></div>
                    <div class="audit-line" style="font-size:10px; color:#888;">&nbsp;&nbsp;&nbsp;↳ {motivo_frete}</div>
                    <div class="audit-line"><span>(-) Custo CMV</span> <span>R$ {item['CMV']:.2f}</span></div>
                    <div class="audit-line"><span>(-) Extras</span> <span>R$ {item['Extra']:.2f}</span></div>
                    <br>
                    <div class="audit-line" style="color:green;"><span>(+) Bônus / Rebate</span> <span>R$ {item['Bonus']:.2f}</span></div>
                    <hr style="border-top: 1px dashed #ccc;">
                    <div class="audit-line audit-bold"><span>(=) LUCRO LÍQUIDO</span> <span>R$ {lucro_final:.2f}</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")
                if st.button("🗑️ Excluir", key=f"del{item['id']}"):
                    delete_product(item['id'])
                    st.session_state.lista_produtos = load_products(st.session_state.user['id'])
                    reiniciar_app()
        
        st.markdown("---")
        col_d, col_c = st.columns([2, 1])
        
        # CSV Export
        csv_data = []
        for it in st.session_state.lista_produtos:
            pf = it['PrecoBase'] * (1 - it['DescontoPct']/100)
            _, fr, _ = identificar_faixa_frete(pf)
            if _ == "manual": fr = it['FreteManual']
            luc = pf - (it['CMV'] + it['Extra'] + fr + (pf*(st.session_state.imposto_padrao+it['TaxaML'])/100)) + it['Bonus']
            mrg = (luc/pf*100) if pf else 0
            csv_data.append({
                "MLB": it['MLB'], "SKU": it.get('SKU', ''), "Produto": it['Produto'],
                "Preco Venda": pf, "Lucro": luc, "Margem %": mrg
            })
        
        df_export = pd.DataFrame(csv_data)
        csv_file = df_export.to_csv(index=False).encode('utf-8')
        col_d.download_button("📥 Baixar Relatório", csv_file, "precificacao.csv", "text/csv")
        
        def limpar_tudo_action(): 
            for i in st.session_state.lista_produtos: delete_product(i['id'])
            st.session_state.lista_produtos = []
            reiniciar_app()
            
        col_c.button("🗑️ LIMPAR TUDO", on_click=limpar_tudo_action, type="secondary")
    else:
        if not selecao_busca: st.info("Lista vazia.")

# --- ABA 2: DASHBOARDS (Só Platinum) ---
if len(tabs) > 1:
    with tabs[1]:
        if has_plotly and st.session_state.lista_produtos:
            df = pd.DataFrame(st.session_state.lista_produtos)
            
            # Recalculo para dataframe
            def calc_row(x):
                pf = x['PrecoBase'] * (1 - x['DescontoPct']/100)
                fr, _, _ = identificar_faixa_frete(pf)
                if _ == "Manual": fr = x['FreteManual']
                imp = pf * (st.session_state.imposto_padrao/100)
                com = pf * (x['TaxaML']/100)
                luc = pf - (x['CMV'] + x['Extra'] + fr + imp + com) + x['Bonus']
                mrg = (luc/pf*100) if pf else 0
                return pd.Series([luc, mrg])
            
            df[['lucro_real', 'margem_real']] = df.apply(calc_row, axis=1)
            
            k1, k2 = st.columns(2)
            k1.metric("Total Produtos", len(df))
            k2.metric("Lucro Estimado", f"R$ {df['lucro_real'].sum():.2f}")
            
            st.divider()
            fig = px.bar(df, x='Produto', y='lucro_real', color='margem_real', title="Lucro por Produto", color_continuous_scale='RdYlGn')
            st.plotly_chart(fig, use_container_width=True)
            
            fig2 = px.scatter(df, x='PrecoBase', y='margem_real', color='margem_real', hover_name='Produto', title="Preço x Margem", color_continuous_scale='RdYlGn')
            st.plotly_chart(fig2, use_container_width=True)
            
        else:
            st.info("Sem dados.")
