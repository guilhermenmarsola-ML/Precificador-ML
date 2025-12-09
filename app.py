import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import base64
import os
import re

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador PRO - V74 Fiscal Final", layout="wide", page_icon="🏛️")
DB_NAME = 'precificador_v74_fiscal.db' # Banco Novo para garantir estrutura correta

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

# Verifica Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# Planos
PLAN_LIMITS = {
    "Silver": {"product_limit": 50, "collab_limit": 1, "dashboards": False},
    "Gold": {"product_limit": 999999, "collab_limit": 4, "dashboards": False},
    "Platinum": {"product_limit": 999999, "collab_limit": 999999, "dashboards": True}
}

# --- 3. BANCO DE DADOS (SCHEMA COMPLETO) ---
def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db(reset=False):
    if reset and os.path.exists(DB_NAME):
        try: os.remove(DB_NAME)
        except: pass
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Usuários (Com Campos Fiscais)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE, password TEXT, name TEXT, plan TEXT, is_active BOOLEAN, photo_base64 TEXT, owner_id INTEGER DEFAULT 0,
            tax_regime TEXT DEFAULT 'Simples Nacional', uf_origin TEXT DEFAULT 'SP'
        )
    ''')
    
    # Produtos (Com TODOS os campos: Fiscais, Estratégia, Preço Usado)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            mlb TEXT, sku TEXT, nome TEXT, ncm TEXT,
            cmv REAL, frete_manual REAL, extra REAL,
            
            -- Estratégia e Preços
            strategy_type TEXT, -- 'erp_target' ou 'markup'
            preco_erp REAL, margem_erp_target REAL,
            preco_sugerido REAL, -- O que o sistema calculou
            preco_usado REAL,    -- O que o usuário decidiu usar
            
            -- Fiscal Avançado
            tax_mode TEXT, -- 'Average' ou 'Real'
            tax_avg REAL,
            icms_out REAL, pis_out REAL, ipi_out REAL,
            icms_in REAL, pis_in REAL, -- Créditos
            
            -- MKT
            taxa_ml REAL, desc_pct REAL, bonus REAL
        )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_NAME): init_db()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- CRUD ---
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
            # Mapeia colunas
            return {
                "id": data[0], "name": data[3], "plan": data[4], 
                "owner_id": data[7], "photo": data[6], "username": username,
                "regime": data[8], "uf": data[9]
            }
    except: pass
    finally: conn.close()
    return None

def update_user_fiscal(user_id, regime, uf):
    conn = get_db_connection()
    conn.execute("UPDATE users SET tax_regime = ?, uf_origin = ? WHERE id = ?", (regime, uf, user_id))
    conn.commit()
    conn.close()

def carregar_produtos(owner_id):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM products WHERE owner_id = ?", conn, params=(owner_id,))
        return df.to_dict('records')
    except: return []
    finally: conn.close()

def salvar_produto(owner_id, item):
    conn = get_db_connection()
    c = conn.cursor()
    # Tratamento de Nulos
    c.execute('''INSERT INTO products (
        owner_id, mlb, sku, nome, ncm, cmv, frete_manual, extra,
        strategy_type, preco_erp, margem_erp_target, preco_sugerido, preco_usado,
        tax_mode, tax_avg, icms_out, pis_out, ipi_out, icms_in, pis_in,
        taxa_ml, desc_pct, bonus
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        owner_id, item.get('MLB',''), item.get('SKU',''), item.get('Produto',''), item.get('NCM',''), 
        item.get('CMV',0), item.get('FreteManual',0), item.get('Extra',0),
        item.get('Strategy','markup'), item.get('PrecoERP',0), item.get('MargemERP',0), item.get('PrecoSugerido',0), item.get('PrecoUsado',0),
        item.get('TaxMode','Average'), item.get('TaxAvg',0), item.get('ICMS_Out',0), item.get('PIS_Out',0), item.get('IPI_Out',0), item.get('ICMS_In',0), item.get('PIS_In',0),
        item.get('TaxaML',0), item.get('DescontoPct',0), item.get('Bonus',0)
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
    # Mapa do Session State -> Coluna DB
    mapa = {
        'PrecoUsado': 'preco_usado', 'DescontoPct': 'desc_pct', 'Bonus': 'bonus', 
        'CMV': 'cmv', 'PrecoERP': 'preco_erp'
    }
    if campo in mapa:
        conn.execute(f"UPDATE products SET {mapa[campo]} = ? WHERE id = ?", (valor, item_id))
        conn.commit()
    conn.close()

# --- 4. MOTOR DE CÁLCULO FISCAL (Restaurado da V70) ---
def calcular_resultados_reais(item, imposto_padrao_user=0.0):
    # Recupera dados
    regime = st.session_state.user.get('regime', 'Simples Nacional')
    cmv = item['cmv']
    
    # 1. Créditos (Se Lucro Real)
    creditos = 0.0
    if regime == 'Lucro Real' and item['tax_mode'] == 'Real':
        creditos = cmv * ((item['icms_in'] + item['pis_in']) / 100)
    
    custo_liquido = cmv - creditos
    
    # 2. Preço de Venda Efetivo (Baseado no Preço USADO, com desconto)
    p_tabela = item['preco_usado']
    p_venda = p_tabela * (1 - item['desc_pct']/100)
    
    # 3. Impostos de Saída
    taxa_imposto = 0.0
    if item['tax_mode'] == 'Average':
        taxa_imposto = item['tax_avg'] # Usa o do produto ou o global se 0? Vamos usar o do produto que salvamos
        if taxa_imposto == 0: taxa_imposto = imposto_padrao_user
    else:
        taxa_imposto = item['icms_out'] + item['pis_out'] + item['ipi_out']
        
    valor_imposto = p_venda * (taxa_imposto / 100)
    
    # 4. Outros Custos
    valor_comissao = p_venda * (item['taxa_ml'] / 100)
    
    # Frete Inteligente (Recalcula com base no preço final)
    frete_real = item['frete_manual']
    faixa_frete = "Manual"
    if p_venda < 79:
        if 50 <= p_venda < 79: frete_real = 6.75; faixa_frete = "50-79"
        elif 29 <= p_venda < 50: frete_real = 6.50; faixa_frete = "29-50"
        elif 12.5 <= p_venda < 29: frete_real = 6.25; faixa_frete = "12-29"
        else: frete_real = 3.25; faixa_frete = "Mínimo"
    
    custo_total = custo_liquido + item['extra'] + frete_real + valor_imposto + valor_comissao
    lucro = p_venda - custo_total + item['bonus']
    
    margem_venda = (lucro / p_venda * 100) if p_venda > 0 else 0
    
    # Margem ERP
    erp_base = item['preco_erp'] if item['preco_erp'] > 0 else 1
    margem_erp = (lucro / erp_base * 100)
    
    return {
        'PV': p_venda, 'Lucro': lucro, 'MargemV': margem_venda, 'MargemE': margem_erp,
        'ImpVal': valor_imposto, 'ComVal': valor_comissao, 'FreteVal': frete_real, 'FreteLbl': faixa_frete,
        'CustoLiq': custo_liquido, 'ImpPct': taxa_imposto
    }

# --- 5. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #F5F5F7; font-family: 'Inter', sans-serif; color: #1D1D1F; }
    
    .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.08); }
    .apple-card { background: white; border-radius: 18px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E5E5EA; }
    .product-card { background: white; border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid #E5E5EA; }
    
    div.stButton > button[kind="primary"] { background-color: #0071E3; color: white; border-radius: 12px; height: 48px; border: none; font-weight: 600; width: 100%; }
    
    .pill { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; }
    .pill-green { background: #E6FFFA; color: #047857; }
    .pill-yellow { background: #FFFBEB; color: #B45309; }
    .pill-red { background: #FEF2F2; color: #DC2626; }
    
    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .card-footer { background-color: #F8F9FA; padding: 10px 20px; border-top: 1px solid #F0F0F0; display: flex; justify-content: space-between; font-size: 11px; color: #666; }
    
    .audit-box { background: #F9FAFB; padding: 15px; border-radius: 8px; border: 1px dashed #D1D5DB; font-family: monospace; font-size: 12px; margin-top: 10px;}
    .audit-line { display: flex; justify-content: space-between; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 6. ESTADO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = {}
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

def init_var(k, v): 
    if k not in st.session_state: st.session_state[k] = v
init_var('n_nome', ''); init_var('n_cmv', 32.57); init_var('n_extra', 0.0); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0); init_var('n_mlb', ''); init_var('n_sku', ''); init_var('n_ncm', '')
init_var('imposto_padrao', 27.0); init_var('n_desc', 0.0); init_var('n_bonus', 0.0)

# --- 7. TELA DE LOGIN ---
if not st.session_state.logged_in:
    with st.sidebar:
        st.header("Suporte")
        if st.button("🚨 RESET TOTAL", type="primary"):
            init_db(reset=True)
            st.success("Resetado!"); time.sleep(1); reiniciar_app()

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center; color:#0071E3;'>Precificador Fiscal</h1>", unsafe_allow_html=True)
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
    
    with st.expander("🏢 Configuração Fiscal", expanded=True):
        regimes = ["Simples Nacional", "Lucro Presumido", "Lucro Real", "MEI"]
        try: idx = regimes.index(u.get('regime', 'Simples Nacional'))
        except: idx = 0
        novo_regime = st.selectbox("Regime", regimes, index=idx)
        
        if novo_regime != u.get('regime'):
            update_user_fiscal(u['id'], novo_regime, u.get('uf', 'SP'))
            st.session_state.user['regime'] = novo_regime
            st.toast("Regime atualizado!")
            time.sleep(0.5); reiniciar_app()

    if st.button("Sair"):
        st.session_state.logged_in = False
        reiniciar_app()

# --- LÓGICA DE CÁLCULO E ADIÇÃO ---
def add_action():
    if not st.session_state.n_nome: return
    
    # 1. Calcula Preço Sugerido (Meta ERP)
    custo_base = st.session_state.n_cmv + st.session_state.n_extra + st.session_state.n_frete
    lucro_alvo = st.session_state.n_erp * (st.session_state.n_merp / 100)
    
    # Taxas
    if st.session_state.n_tax_mode == 'Average':
        impostos = st.session_state.imposto_padrao
    else:
        impostos = st.session_state.n_icms_out + st.session_state.n_pis_out + st.session_state.n_ipi
        
    div = 1 - ((st.session_state.n_taxa + impostos) / 100)
    p_sug = 0.0
    if div > 0:
        p_sug = (custo_base + lucro_alvo) / div
    
    # 2. Salva (Preço Usado começa igual ao Sugerido)
    item = {
        'MLB': st.session_state.n_mlb, 'SKU': st.session_state.n_sku, 'Produto': st.session_state.n_nome, 'NCM': st.session_state.n_ncm,
        'CMV': st.session_state.n_cmv, 'FreteManual': st.session_state.n_frete, 'Extra': st.session_state.n_extra,
        'Strategy': 'erp_target' if st.session_state.n_strat == 'Meta ERP' else 'markup',
        'PrecoERP': st.session_state.n_erp, 'MargemERP': st.session_state.n_merp, 
        'PrecoSugerido': p_sug, 'PrecoUsado': p_sug, # <-- Importante
        'TaxMode': st.session_state.n_tax_mode, 'TaxAvg': st.session_state.imposto_padrao,
        'ICMS_Out': st.session_state.get('n_icms_out',0), 'PIS_Out': st.session_state.get('n_pis_out',0), 'IPI_Out': st.session_state.get('n_ipi',0),
        'ICMS_In': st.session_state.get('n_icms_in',0), 'PIS_In': st.session_state.get('n_pis_in',0),
        'TaxaML': st.session_state.n_taxa, 'DescontoPct': st.session_state.n_desc, 'Bonus': st.session_state.n_bonus
    }
    
    salvar_produto(st.session_state.owner_id, item)
    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
    st.toast("Salvo!", icon="✅")
    st.session_state.n_nome = ""

st.title("Área de Trabalho")
abas = ["⚡ Precificador"]
if PLAN_LIMITS[st.session_state.user['plan']]['dashboards']: abas.append("📊 BI")
tabs = st.tabs(abas)

with tabs[0]:
    # INPUT
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    c1.text_input("MLB/SKU", key="n_mlb")
    c2.text_input("Produto", key="n_nome")
    c3.text_input("NCM", key="n_ncm")
    
    c4, c5, c6 = st.columns(3)
    c4.number_input("Custo (CMV)", step=0.01, key="n_cmv")
    c5.number_input("Frete Manual", step=0.01, key="n_frete")
    c6.number_input("Extras", step=0.01, key="n_extra")
    
    st.markdown("---")
    st.caption("ESTRATÉGIA")
    cs1, cs2, cs3 = st.columns(3)
    cs1.radio("Modo", ["Meta ERP", "Markup"], horizontal=True, key="n_strat")
    cs2.number_input("Preço ERP", step=0.01, key="n_erp")
    cs3.number_input("Margem Alvo %", step=1.0, key="n_merp")
    
    st.markdown("---")
    st.caption("FISCAL")
    tm = st.radio("Impostos", ["Média Simples", "Detalhado (Real)"], horizontal=True, key="n_tax_mode")
    tax_code = 'Average' if 'Média' in tm else 'Real'
    
    if tax_code == 'Average':
        st.number_input("Média Impostos %", value=st.session_state.imposto_padrao, key="imposto_padrao")
    else:
        ft1, ft2, ft3 = st.columns(3)
        ft1.number_input("ICMS Saída", key="n_icms_out")
        ft2.number_input("PIS/COF Saída", key="n_pis_out")
        ft3.number_input("IPI", key="n_ipi")
        st.caption("Créditos")
        fc1, fc2 = st.columns(2)
        fc1.number_input("Crédito ICMS", key="n_icms_in")
        fc2.number_input("Crédito PIS", key="n_pis_in")

    st.markdown("---")
    st.caption("MARKETPLACE")
    m1, m2, m3 = st.columns(3)
    m1.number_input("Comissão %", value=16.5, key="n_taxa")
    m2.number_input("Desc %", value=0.0, key="n_desc")
    m3.number_input("Bônus R$", value=0.0, key="n_bonus")

    st.write("")
    st.button("CADASTRAR", type="primary", on_click=add_action)
    st.markdown('</div>', unsafe_allow_html=True)

    # LISTA
    if st.session_state.lista_produtos:
        for item in reversed(st.session_state.lista_produtos):
            # CÁLCULO AO VIVO
            res = calcular_resultados_reais(item, st.session_state.imposto_padrao)
            
            # Cores
            if res['MargemV'] < 8: cls = "pill-red"
            elif res['MargemV'] < 15: cls = "pill-yellow"
            else: cls = "pill-green"
            
            luc_fmt = f"+ R$ {res['Lucro']:.2f}" if res['Lucro'] > 0 else f"- R$ {abs(res['Lucro']):.2f}"

            st.markdown(f"""
            <div class="product-card">
                <div class="card-header">
                    <div><b>{item['Produto']}</b> <span style="font-size:12px; color:#888;">{item['MLB']}</span></div>
                    <div class="pill {cls}">{res['MargemV']:.1f}%</div>
                </div>
                <div class="card-body" style="display:flex; justify-content:space-between;">
                    <div>Venda: <b>R$ {res['PV']:.2f}</b></div>
                    <div>Lucro: <b>{luc_fmt}</b></div>
                </div>
                <div class="card-footer">
                    <div class="margin-box">Margem Venda: <b>{res['MargemV']:.1f}%</b></div>
                    <div class="margin-box">Margem ERP: <b>{res['MargemE']:.1f}%</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚙️ Editar & DRE"):
                # Callbacks
                def up(k, f, i=item['id']):
                    atualizar_campo_db(i, f, st.session_state[k])
                    # Atualiza Local
                    for idx, p in enumerate(st.session_state.lista_produtos):
                        if p['id'] == i: st.session_state.lista_produtos[idx][f] = st.session_state[k]

                st.info(f"💡 Sugestão (Meta): R$ {item['preco_sugerido']:.2f}")

                e1, e2, e3 = st.columns(3)
                e1.number_input("Preço Usado", value=float(item['preco_usado']), key=f"p{item['id']}", on_change=up, args=(f"p{item['id']}", 'PrecoUsado'))
                e2.number_input("Desc %", value=float(item['desc_pct']), key=f"d{item['id']}", on_change=up, args=(f"d{item['id']}", 'DescontoPct'))
                e3.number_input("Bônus", value=float(item['bonus']), key=f"b{item['id']}", on_change=up, args=(f"b{item['id']}", 'Bonus'))
                
                st.divider()
                st.markdown("##### 🧮 Memória de Cálculo (DRE)")
                st.markdown(f"""
                <div class="audit-box">
                    <div class="audit-line"><span>(+) Preço Tabela</span> <span>R$ {item['preco_usado']:.2f}</span></div>
                    <div class="audit-line" style="color:red;"><span>(-) Desconto ({item['desc_pct']}%)</span> <span>R$ {item['preco_usado'] - res['PV']:.2f}</span></div>
                    <div class="audit-line audit-bold"><span>(=) VENDA LÍQUIDA</span> <span>R$ {res['PV']:.2f}</span></div>
                    <br>
                    <div class="audit-line"><span>(-) Impostos ({res['ImpPct']}%)</span> <span>R$ {res['ImpVal']:.2f}</span></div>
                    <div class="audit-line"><span>(-) Comissão ({item['taxa_ml']}%)</span> <span>R$ {res['ComVal']:.2f}</span></div>
                    <div class="audit-line"><span>(-) Frete ({res['FreteLbl']})</span> <span>R$ {res['FreteVal']:.2f}</span></div>
                    <div class="audit-line"><span>(-) Custo Líquido</span> <span>R$ {res['CustoLiq']:.2f}</span></div>
                    <div class="audit-line"><span>(-) Extras</span> <span>R$ {item['extra']:.2f}</span></div>
                    <br>
                    <div class="audit-line" style="color:green;"><span>(+) Bônus</span> <span>R$ {item['bonus']:.2f}</span></div>
                    <hr style="border-top:1px dashed #ccc">
                    <div class="audit-line audit-bold"><span>(=) LUCRO REAL</span> <span>R$ {res['Lucro']:.2f}</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")
                if st.button("Excluir", key=f"del{item['id']}"):
                    deletar_produto(item['id'])
                    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                    reiniciar_app()

if len(tabs) > 1:
    with tabs[1]:
        if st.session_state.lista_produtos and has_plotly:
            df = pd.DataFrame([calcular_resultados_reais(i, st.session_state.imposto_padrao) for i in st.session_state.lista_produtos])
            df['Produto'] = [i['nome'] for i in st.session_state.lista_produtos]
            fig = px.bar(df, x='Produto', y='Lucro', color='MargemV', title="Lucro por Produto")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Sem dados")
