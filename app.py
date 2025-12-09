import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import base64
import os
import xml.etree.ElementTree as ET
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador PRO - V72 Stable", layout="wide", page_icon="🏛️")
DB_NAME = 'precificador_v72.db'

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
            owner_id INTEGER DEFAULT 0,
            tax_regime TEXT DEFAULT 'Simples Nacional',
            uf_origin TEXT DEFAULT 'SP'
        )
    ''')
    
    # Produtos
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            mlb TEXT, sku TEXT, nome TEXT, ncm TEXT,
            cmv REAL, frete REAL, extra REAL,
            strategy_type TEXT, preco_erp REAL, margem_erp_target REAL,
            tax_mode TEXT, tax_avg_rate REAL, 
            icms_rate REAL, pis_cofins_rate REAL, ipi_rate REAL,
            credit_icms REAL, credit_pis_cofins REAL,
            preco_final REAL, margem_final REAL, lucro_final REAL,
            taxa_ml REAL, desc_pct REAL, bonus REAL
        )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_NAME): init_db()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- CRUD USER ---
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
            if data[5] and check_hashes(password, data[2]):
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
    c = conn.cursor()
    c.execute("UPDATE users SET tax_regime = ?, uf_origin = ? WHERE id = ?", (regime, uf, user_id))
    conn.commit()
    conn.close()

# --- CRUD PRODUTOS ---
def carregar_produtos(owner_id):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM products WHERE owner_id = ?", conn, params=(owner_id,))
        lista = []
        for _, row in df.iterrows():
            lista.append({
                "id": row['id'], 
                "MLB": row['mlb'], 
                "SKU": row['sku'], 
                "Produto": row['nome'], # Aqui garantimos que a coluna 'nome' vira a chave 'Produto'
                "NCM": row['ncm'],
                "CMV": row['cmv'], "FreteManual": row['frete'], "Extra": row['extra'],
                "Strategy": row['strategy_type'], "PrecoERP": row['preco_erp'], "MargemERP": row['margem_erp_target'],
                "TaxMode": row['tax_mode'], "TaxAvg": row['tax_avg_rate'], 
                "ICMS_Out": row['icms_rate'], "PIS_COFINS_Out": row['pis_cofins_rate'], 
                "IPI": row['ipi_rate'], "ICMS_In": row['credit_icms'], "PIS_COFINS_In": row['credit_pis_cofins'],
                "PrecoFinal": row['preco_final'], "Margem": row['margem_final'], "Lucro": row['lucro_final'],
                "TaxaML": row['taxa_ml'], "DescontoPct": row['desc_pct'], "Bonus": row['bonus']
            })
        return lista
    except: return []
    finally: conn.close()

def salvar_produto(owner_id, item):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tratamento de Nulos para evitar erro de banco
    mlb = item.get('MLB', '')
    sku = item.get('SKU', '')
    nome = item.get('Produto', 'Produto Sem Nome')
    
    c.execute('''INSERT INTO products (
        owner_id, mlb, sku, nome, ncm, cmv, frete, extra, 
        strategy_type, preco_erp, margem_erp_target, 
        tax_mode, tax_avg_rate, icms_rate, pis_cofins_rate, ipi_rate, credit_icms, credit_pis_cofins,
        preco_final, margem_final, lucro_final, taxa_ml, desc_pct, bonus
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        owner_id, mlb, sku, nome, item.get('NCM', ''), item.get('CMV', 0), item.get('FreteManual', 0), item.get('Extra', 0),
        item.get('Strategy', 'markup'), item.get('PrecoERP', 0), item.get('MargemERP', 0),
        item.get('TaxMode', 'Average'), item.get('TaxAvg', 0), item.get('ICMS_Out', 0), item.get('PIS_COFINS_Out', 0), item.get('IPI', 0), item.get('ICMS_In', 0), item.get('PIS_COFINS_In', 0),
        item.get('PrecoFinal', 0), item.get('Margem', 0), item.get('Lucro', 0), item.get('TaxaML', 0), item.get('DescontoPct', 0), item.get('Bonus', 0)
    ))
    conn.commit()
    conn.close()

def deletar_produto(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

# --- FUNÇÃO DE CURA DE DADOS (IMPEDE O KEYERROR) ---
def sanear_lista_produtos():
    if st.session_state.lista_produtos:
        nova_lista = []
        for item in st.session_state.lista_produtos:
            # Garante que todas as chaves existam
            safe_item = item.copy()
            if 'Produto' not in safe_item: safe_item['Produto'] = 'Produto Sem Nome'
            if 'MLB' not in safe_item: safe_item['MLB'] = ''
            if 'PrecoERP' not in safe_item: safe_item['PrecoERP'] = 0.0
            # Adiciona o item corrigido
            nova_lista.append(safe_item)
        st.session_state.lista_produtos = nova_lista

# --- 4. MOTOR DE CÁLCULO ---
def calcular_preco_inteligente(dados):
    custo_liquido = dados['CMV']
    creditos = 0.0
    
    if dados['Regime'] == 'Lucro Real' and dados['TaxMode'] == 'Real':
        creditos = dados['CMV'] * ((dados['ICMS_In'] + dados['PIS_COFINS_In']) / 100)
        custo_liquido = dados['CMV'] - creditos

    custos_base = custo_liquido + dados['FreteManual'] + dados['Extra']
    taxas_venda_pct = dados['TaxaML']
    
    if dados['TaxMode'] == 'Average':
        taxas_venda_pct += dados['TaxAvg']
    else:
        taxas_venda_pct += (dados['ICMS_Out'] + dados['PIS_COFINS_Out'] + dados['IPI'])

    preco_final = 0.0
    if dados['Strategy'] == 'erp_target':
        lucro_alvo_reais = dados['PrecoERP'] * (dados['MargemERP'] / 100)
        divisor = 1 - (taxas_venda_pct / 100)
        if divisor > 0:
            preco_final = (custos_base + lucro_alvo_reais - dados['Bonus']) / divisor
    else:
        margem_target = dados['MargemERP']
        divisor = 1 - ((taxas_venda_pct + margem_target) / 100)
        if divisor > 0:
            preco_final = (custos_base - dados['Bonus']) / divisor

    impostos_reais = preco_final * ((taxas_venda_pct - dados['TaxaML']) / 100)
    comissao_reais = preco_final * (dados['TaxaML'] / 100)
    lucro_final = preco_final - (custos_base + impostos_reais + comissao_reais) + dados['Bonus']
    margem_final = (lucro_final / preco_final * 100) if preco_final > 0 else 0
    
    return preco_final, lucro_final, margem_final, custo_liquido

# --- 5. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #F5F5F7; font-family: 'Inter', sans-serif; color: #1D1D1F; }
    .apple-card { background: white; border-radius: 18px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E5E5EA; }
    .product-card { background: white; border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid #E5E5EA; }
    div.stButton > button[kind="primary"] { background-color: #0071E3; color: white; border-radius: 12px; height: 48px; border: none; font-weight: 600; width: 100%; }
    .pill { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; }
    .pill-green { background: #E6FFFA; color: #047857; }
    .pill-yellow { background: #FFFBEB; color: #B45309; }
    .pill-red { background: #FEF2F2; color: #DC2626; }
</style>
""", unsafe_allow_html=True)

# --- 6. ESTADO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = {}
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

# Aplica a cura de dados
sanear_lista_produtos()

def init_var(k, v): 
    if k not in st.session_state: st.session_state[k] = v
init_var('n_nome', ''); init_var('n_cmv', 32.57); init_var('n_extra', 0.0); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0); init_var('n_mlb', ''); init_var('n_sku', '')
init_var('n_ncm', ''); init_var('n_desc', 0.0); init_var('n_bonus', 0.0)

# --- 7. LOGIN ---
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
                        sanear_lista_produtos() # Garante integridade ao carregar
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
    st.caption(f"{u['plan']} | {u.get('regime', 'Simples Nacional')}")
    
    if st.button("Sair"):
        st.session_state.logged_in = False
        reiniciar_app()
    
    st.divider()
    
    with st.expander("🏢 Configuração da Empresa", expanded=True):
        regimes = ["Simples Nacional", "Lucro Presumido", "Lucro Real", "MEI"]
        try: idx = regimes.index(u.get('regime', 'Simples Nacional'))
        except: idx = 0
        novo_regime = st.selectbox("Regime", regimes, index=idx)
        
        ufs = ["SP", "RJ", "MG", "PR", "SC", "RS", "Outros"]
        try: idx_uf = ufs.index(u.get('uf', 'SP'))
        except: idx_uf = 0
        nova_uf = st.selectbox("Estado", ufs, index=idx_uf)
        
        if novo_regime != u.get('regime') or nova_uf != u.get('uf'):
            update_user_fiscal(u['id'], novo_regime, nova_uf)
            st.session_state.user['regime'] = novo_regime
            st.session_state.user['uf'] = nova_uf
            st.toast("Fiscal atualizado!")
            time.sleep(1)
            reiniciar_app()

    with st.expander("Frete ML"):
        st.session_state.taxa_50_79 = st.number_input("50-79", value=6.75)

# --- CALLBACKS E AÇÕES ---
def adicionar_produto_fiscal():
    if not st.session_state.n_nome: return

    regime = st.session_state.user['regime']
    
    tax_mode = st.session_state.n_tax_mode
    if tax_mode == 'Average':
        tax_avg = st.session_state.n_tax_avg
        icms_out = pis_out = ipi = icms_in = pis_in = 0.0
    else:
        tax_avg = 0.0
        icms_out = st.session_state.n_icms_out
        pis_out = st.session_state.n_pis_out
        ipi = st.session_state.n_ipi
        icms_in = st.session_state.n_icms_in
        pis_in = st.session_state.n_pis_in

    dados_calc = {
        'CMV': st.session_state.n_cmv, 'FreteManual': st.session_state.n_frete, 'Extra': st.session_state.n_extra,
        'Regime': regime, 'Strategy': 'erp_target' if st.session_state.n_strat == 'Meta ERP' else 'markup',
        'PrecoERP': st.session_state.n_erp, 'MargemERP': st.session_state.n_merp,
        'TaxMode': tax_mode, 'TaxAvg': tax_avg,
        'ICMS_Out': icms_out, 'PIS_COFINS_Out': pis_out, 'IPI': ipi, 'ICMS_In': icms_in, 'PIS_COFINS_In': pis_in,
        'TaxaML': st.session_state.n_taxa, 'DescontoPct': st.session_state.n_desc, 'Bonus': st.session_state.n_bonus
    }
    
    pf, luc, mrg, custo_liq = calcular_preco_inteligente(dados_calc)
    
    item = {
        'MLB': st.session_state.n_mlb, 'SKU': st.session_state.n_sku, 'Produto': st.session_state.n_nome, 'NCM': st.session_state.n_ncm,
        'CMV': st.session_state.n_cmv, 'FreteManual': st.session_state.n_frete, 'Extra': st.session_state.n_extra,
        'Strategy': dados_calc['Strategy'], 'PrecoERP': dados_calc['PrecoERP'], 'MargemERP': dados_calc['MargemERP'],
        'TaxMode': dados_calc['TaxMode'], 'TaxAvg': dados_calc['TaxAvg'],
        'ICMS_Out': dados_calc['ICMS_Out'], 'PIS_COFINS_Out': dados_calc['PIS_COFINS_Out'], 'IPI': dados_calc['IPI'],
        'ICMS_In': dados_calc['ICMS_In'], 'PIS_COFINS_In': dados_calc['PIS_COFINS_In'],
        'PrecoFinal': pf, 'Margem': mrg, 'Lucro': luc, 
        'TaxaML': dados_calc['TaxaML'], 'DescontoPct': dados_calc['DescontoPct'], 'Bonus': dados_calc['Bonus']
    }
    
    salvar_produto(st.session_state.owner_id, item)
    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
    st.toast("Produto salvo!", icon="✅")
    st.session_state.n_nome = ""; st.session_state.n_mlb = ""; st.session_state.n_sku = ""; st.session_state.n_cmv = 0.0

st.title("Área de Trabalho")
abas = ["⚡ Precificador"]
if PLAN_LIMITS[st.session_state.user['plan']]['dashboards']: abas.append("📊 BI")
tabs = st.tabs(abas)

with tabs[0]:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    
    # DADOS CADASTRAIS
    st.caption("1. DADOS DO PRODUTO")
    c1, c2, c3 = st.columns([1, 2, 1])
    c1.text_input("MLB/SKU", key="n_mlb")
    c2.text_input("Nome do Produto", key="n_nome")
    c3.text_input("NCM", key="n_ncm")
    
    c4, c5, c6 = st.columns(3)
    c4.number_input("Custo (CMV)", step=0.01, key="n_cmv")
    c5.number_input("Frete Manual", step=0.01, key="n_frete")
    c6.number_input("Outros Custos", step=0.01, key="n_extra")
    
    st.markdown("---")
    
    # ESTRATÉGIA
    st.caption("2. ESTRATÉGIA DE PREÇO")
    cols_strat = st.columns([2, 1, 1])
    strat_sel = cols_strat[0].radio("Modo:", ["Meta ERP (Reverso)", "Markup (Direto)"], horizontal=True, key="n_strat")
    cols_strat[1].number_input("Preço ERP", step=0.01, key="n_erp")
    cols_strat[2].number_input("Margem Alvo %", step=1.0, key="n_merp")
    
    st.markdown("---")
    
    # FISCAL
    st.caption(f"3. TRIBUTAÇÃO ({st.session_state.user.get('regime')})")
    
    tax_sel = st.radio("Cálculo Fiscal:", ["Média Simples (Padrão)", "Detalhado (Real)"], horizontal=True, key="n_tax_mode")
    tax_code = 'Average' if 'Média' in tax_sel else 'Real'
    
    if tax_code == 'Average':
        st.number_input("Taxa Média de Impostos (%)", value=7.0 if st.session_state.user.get('regime') == 'Simples Nacional' else 18.0, key="n_tax_avg")
        st.session_state.n_icms_out = 0.0; st.session_state.n_pis_out = 0.0; st.session_state.n_ipi = 0.0
        st.session_state.n_icms_in = 0.0; st.session_state.n_pis_in = 0.0
    else:
        ft1, ft2, ft3 = st.columns(3)
        ft1.number_input("ICMS Saída %", step=0.5, key="n_icms_out")
        ft2.number_input("PIS/COFINS Saída %", step=0.5, key="n_pis_out")
        ft3.number_input("IPI %", step=0.5, key="n_ipi")
        
        st.caption("Créditos")
        fc1, fc2 = st.columns(2)
        fc1.number_input("Crédito ICMS %", step=0.5, key="n_icms_in")
        fc2.number_input("Crédito PIS/COF %", step=0.5, key="n_pis_in")
        st.session_state.n_tax_avg = 0.0

    st.markdown("---")
    
    # MARKETPLACE
    st.caption("4. MARKETPLACE")
    cm1, cm2, cm3 = st.columns(3)
    cm1.number_input("Comissão ML %", value=16.5, key="n_taxa")
    cm2.number_input("Desconto Campanha %", value=0.0, key="n_desc")
    cm3.number_input("Bônus/Rebate R$", value=0.0, key="n_bonus")
    
    st.write("")
    st.button("CALCULAR E SALVAR", type="primary", on_click=adicionar_produto_fiscal)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # LISTA
    if st.session_state.lista_produtos:
        st.markdown("### 📋 Produtos")
        for item in reversed(st.session_state.lista_produtos):
            # Safe Get
            nome = item.get('Produto', 'Sem Nome')
            mlb = item.get('MLB', '-')
            luc = item.get('Lucro', 0.0)
            mrg = item.get('Margem', 0.0)
            pf = item.get('PrecoFinal', 0.0)
            
            st.markdown(f"""
            <div class="product-card">
                <div class="card-header">
                    <div><b>{nome}</b> <span style="font-size:12px; color:#888;">{mlb}</span></div>
                    <div class="pill {'pill-green' if luc>0 else 'pill-red'}">{mrg:.1f}%</div>
                </div>
                <div class="card-body" style="display:flex; justify-content:space-between;">
                    <div>Venda: <b>R$ {pf:.2f}</b></div>
                    <div>Lucro: <b>R$ {luc:.2f}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Detalhes"):
                st.write(f"Regime: {st.session_state.user.get('regime')}")
                if st.button("Excluir", key=f"del_{item['id']}"):
                    deletar_produto(item['id'])
                    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                    st.rerun()

# --- ABA 2: DASHBOARDS ---
if len(tabs) > 1:
    with tabs[1]:
        if st.session_state.lista_produtos:
            df = pd.DataFrame(st.session_state.lista_produtos)
            if has_plotly:
                # Trata possíveis nulos antes do gráfico
                df['Lucro'] = df['Lucro'].fillna(0)
                df['Produto'] = df['Produto'].fillna('Sem Nome')
                fig = px.bar(df, x='Produto', y='Lucro', color='Margem')
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Sem Plotly")
        else: st.info("Sem dados")
