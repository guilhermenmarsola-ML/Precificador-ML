import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import base64
import os
import re

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador PRO - V73 Restaurada", layout="wide", page_icon="💎")
DB_NAME = 'precificador_v73_final.db'

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

# --- 3. BANCO DE DADOS ---
def init_db(reset=False):
    if reset and os.path.exists(DB_NAME):
        try: os.remove(DB_NAME)
        except: pass
        
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
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
    # Produtos (Com TODOS os campos necessários para a lógica antiga)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            mlb TEXT, sku TEXT, nome TEXT,
            cmv REAL, frete_manual REAL, extra REAL,
            taxa_ml REAL,
            preco_erp REAL, margem_erp REAL, -- Meta
            preco_usado REAL, -- O preço que você decidiu praticar
            desc_pct REAL, bonus REAL
        )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_NAME): init_db()

def get_db(): return sqlite3.connect(DB_NAME, check_same_thread=False)
def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- CRUD USER ---
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
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        data = c.fetchone()
        if data and data[5] and check_hashes(password, data[2]):
            return {"id": data[0], "name": data[3], "plan": data[4], "owner_id": data[7], "photo": data[6], "username": username}
    except: pass
    finally: conn.close()
    return None

# --- CRUD PRODUTOS ---
def carregar_produtos(owner_id):
    conn = get_db()
    try:
        df = pd.read_sql_query("SELECT * FROM products WHERE owner_id = ?", conn, params=(owner_id,))
        return df.to_dict('records')
    except: return []
    finally: conn.close()

def salvar_produto(owner_id, item):
    conn = get_db()
    c = conn.cursor()
    # Se ID existe na lista local, tenta update, senão insert (simplificado aqui como insert sempre pra não complicar, mas com delete antes se for edição)
    # Na prática do app, estamos sempre recriando o item ao salvar.
    c.execute('''INSERT INTO products (
        owner_id, mlb, sku, nome, cmv, frete_manual, extra, taxa_ml, 
        preco_erp, margem_erp, preco_usado, desc_pct, bonus
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        owner_id, item['MLB'], item['SKU'], item['Produto'], item['CMV'], item['FreteManual'], item['Extra'], item['TaxaML'],
        item['PrecoERP'], item['MargemERP'], item['PrecoUsado'], item['DescontoPct'], item['Bonus']
    ))
    conn.commit()
    conn.close()

def deletar_produto(item_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def atualizar_campo_db(item_id, campo, valor):
    conn = get_db()
    # Mapa de nomes do App -> Colunas DB
    mapa = {
        'PrecoUsado': 'preco_usado', 'DescontoPct': 'desc_pct', 'Bonus': 'bonus', 
        'CMV': 'cmv', 'PrecoERP': 'preco_erp'
    }
    if campo in mapa:
        conn.execute(f"UPDATE products SET {mapa[campo]} = ? WHERE id = ?", (valor, item_id))
        conn.commit()
    conn.close()

# --- 4. CSS (VISUAL LIMPO E PROFISSIONAL) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #F5F5F7; font-family: 'Inter', sans-serif; color: #1D1D1F; }
    
    .login-container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.08); }
    .apple-card { background: white; border-radius: 18px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E5E5EA; }
    .product-card { background: white; border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid #E5E5EA; }
    
    div.stButton > button[kind="primary"] { background-color: #0071E3; color: white; border-radius: 12px; height: 48px; border: none; font-weight: 600; width: 100%; }
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #D1D1D6 !important; border-radius: 8px !important; }
    
    .pill { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; }
    .pill-green { background: #E6FFFA; color: #047857; }
    .pill-yellow { background: #FFFBEB; color: #B45309; }
    .pill-red { background: #FEF2F2; color: #DC2626; }
    
    /* DRE VISUAL */
    .dre-box { background: #FAFAFA; border: 1px dashed #CCC; border-radius: 8px; padding: 15px; margin-top: 10px; font-size: 13px; }
    .dre-line { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .dre-total { font-weight: bold; border-top: 1px solid #DDD; padding-top: 5px; margin-top: 5px; display: flex; justify-content: space-between;}
</style>
""", unsafe_allow_html=True)

# --- 5. ESTADO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = {}
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

# Inicializa inputs
def init_var(k, v): 
    if k not in st.session_state: st.session_state[k] = v
init_var('n_nome', ''); init_var('n_cmv', 32.57); init_var('n_extra', 0.0); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0); init_var('n_mlb', ''); init_var('n_sku', '')
init_var('imposto_padrao', 27.0); init_var('taxa_12_29', 6.25); init_var('taxa_29_50', 6.50); init_var('taxa_50_79', 6.75); init_var('taxa_minima', 3.25)

# --- 6. TELA DE LOGIN ---
if not st.session_state.logged_in:
    with st.sidebar:
        st.header("Suporte")
        if st.button("🚨 RESET TOTAL", type="primary"):
            init_db(reset=True)
            st.success("Resetado!"); time.sleep(1); reiniciar_app()

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
    
    # Importador Restaurado
    st.divider()
    st.markdown("### Importar")
    uploaded_file = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            aba = st.selectbox("Aba", xl.sheet_names)
            h_row = st.number_input("Linha Header", value=8, min_value=0)
            if st.button("Processar"):
                df = xl.parse(aba, header=h_row)
                # ... (Lógica de importação simplificada para caber, mas mantendo a lógica de limpeza)
                # Assume-se que o usuário mapeia colunas padrão se necessário.
                # Aqui usamos busca aproximada automática para agilizar:
                for _, row in df.iterrows():
                    try:
                        # Busca Flexivel
                        def fcol(k): return next((c for c in df.columns if k.lower() in str(c).lower()), None)
                        prod = row[fcol("Produto")]
                        if not isinstance(prod, str): continue
                        
                        cmv = limpar_valor_dinheiro(row[fcol("CMV")])
                        p_usado = limpar_valor_dinheiro(row[fcol("Preço")]) # Preço Usado
                        erp = limpar_valor_dinheiro(row[fcol("ERP")]) if fcol("ERP") else p_usado
                        frete = limpar_valor_dinheiro(row[fcol("Frete")])
                        if frete == 0: frete = 18.86
                        
                        item = {
                            "MLB": str(row.get(fcol("MLB"), "")), "SKU": "", "Produto": prod,
                            "CMV": cmv, "FreteManual": frete, "TaxaML": 16.5, "Extra": 0.0,
                            "PrecoERP": erp, "MargemERP": 20.0, 
                            "PrecoUsado": p_usado, "DescontoPct": 0.0, "Bonus": 0.0
                        }
                        salvar_produto(st.session_state.owner_id, item)
                    except: pass
                st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                st.success("Importado!")
        except Exception as e: st.error(f"Erro: {e}")

# --- LÓGICA DE NEGÓCIO ---
def identificar_frete(p):
    if p >= 79: return 0.0, "Manual"
    if 50 <= p < 79: return st.session_state.taxa_50_79, "Tab 50-79"
    if 29 <= p < 50: return st.session_state.taxa_29_50, "Tab 29-50"
    if 12.5 <= p < 29: return st.session_state.taxa_12_29, "Tab 12-29"
    return st.session_state.taxa_minima, "Mínimo"

def calc_sugerido(custo, lucro_alvo, t_ml, imp, f_man):
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
    if not st.session_state.n_nome: return
    lucro = st.session_state.n_erp * (st.session_state.n_merp / 100)
    p_sug = calc_sugerido(st.session_state.n_cmv + st.session_state.n_extra, lucro, st.session_state.n_taxa, st.session_state.imposto_padrao, st.session_state.n_frete)
    
    # IMPORTANTE: Ao criar, o Preço Usado começa igual ao Sugerido
    item = {
        "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv, "FreteManual": st.session_state.n_frete, "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra, "PrecoERP": st.session_state.n_erp, "MargemERP": st.session_state.n_merp,
        "PrecoUsado": p_sug, "DescontoPct": 0.0, "Bonus": 0.0
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
    st.caption("NOVO PRODUTO")
    c1, c2 = st.columns([1, 2])
    c1.text_input("SKU/MLB", key="n_mlb")
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

    # LISTA
    if st.session_state.lista_produtos:
        st.caption(f"{len(st.session_state.lista_produtos)} produtos")
        
        for item in reversed(st.session_state.lista_produtos):
            # 1. CÁLCULO BASEADO NO PREÇO USADO (Que você edita)
            # O sistema sugere, mas o que manda é o 'PrecoUsado'
            
            p_venda = item['PrecoUsado'] * (1 - item['DescontoPct']/100)
            
            # Frete Inteligente
            fr_val, fr_lbl = identificar_frete(p_venda)
            if fr_lbl == "Manual": fr_val = item['FreteManual']
            
            imp = p_venda * (st.session_state.imposto_padrao/100)
            com = p_venda * (item['TaxaML']/100)
            custos = item['CMV'] + item['Extra'] + fr_val + imp + com
            lucro = p_venda - custos + item['Bonus']
            
            # Margens
            mrg_venda = (lucro/p_venda*100) if p_venda > 0 else 0
            erp_safe = item['PrecoERP'] if item['PrecoERP'] > 0 else 1
            mrg_erp = (lucro/erp_safe*100)
            
            # Meta de Lucro para Comparação (Base ERP)
            lucro_meta = item['PrecoERP'] * (item['MargemERP'] / 100)
            p_sugerido = calc_sugerido(item['CMV']+item['Extra'], lucro_meta, item['TaxaML'], st.session_state.imposto_padrao, item['FreteManual'])

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
                    <div><div class="sku-text">{item['MLB']} {item['SKU']}</div><div class="title-text">{item['Produto']}</div></div>
                    <div class="pill {cls}">{mrg_venda:.1f}%</div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="price-display">Venda<br><b>R$ {p_venda:.2f}</b></div>
                    <div class="price-display" style="text-align:right;">Lucro<br><span style="color:{'#34C759' if lucro>0 else '#FF3B30'}">R$ {lucro:.2f}</span></div>
                </div>
                <div class="card-footer">
                   <div class="margin-box"><div>Margem Venda</div><div class="margin-val">{mrg_venda:.1f}%</div></div>
                   <div class="margin-box" style="border-left: 1px solid #eee;"><div>Margem ERP</div><div class="margin-val">{mrg_erp:.1f}%</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("⚙️ Editar e DRE"):
                # Callback de Atualização ao Vivo
                def update(k, f, i=item['id']):
                    atualizar_campo_db(i, f, st.session_state[k])
                    for idx, p in enumerate(st.session_state.lista_produtos):
                        if p['id'] == i: st.session_state.lista_produtos[idx][f] = st.session_state[k]

                st.info(f"💡 Sugestão do Sistema (Meta ERP): **R$ {p_sugerido:.2f}**")

                e1, e2, e3 = st.columns(3)
                # AQUI ESTÁ O SEGREDO: Editamos o 'PrecoUsado'
                e1.number_input("Preço de Venda (Usado)", value=float(item['PrecoUsado']), key=f"p{item['id']}", on_change=update, args=(f"p{item['id']}", 'PrecoUsado'))
                e2.number_input("Desc %", value=float(item['DescontoPct']), key=f"d{item['id']}", on_change=update, args=(f"d{item['id']}", 'DescontoPct'))
                e3.number_input("Bônus", value=float(item['Bonus']), key=f"b{item['id']}", on_change=update, args=(f"b{item['id']}", 'Bonus'))
                
                # --- DRE DETALHADA RESTAURADA ---
                st.markdown("##### 🧮 Memória de Cálculo (DRE)")
                st.markdown(f"""
                <div class="dre-box">
                    <div class="dre-line"><span>(+) Preço Praticado</span> <span>R$ {item['PrecoUsado']:.2f}</span></div>
                    <div class="dre-line" style="color:red;"><span>(-) Desconto ({item['DescontoPct']}%)</span> <span>R$ {item['PrecoUsado'] - p_venda:.2f}</span></div>
                    <div class="dre-line" style="font-weight:bold;"><span>(=) VENDA LÍQUIDA</span> <span>R$ {p_venda:.2f}</span></div>
                    <br>
                    <div class="dre-line"><span>(-) Impostos ({st.session_state.imposto_padrao}%)</span> <span>R$ {imp:.2f}</span></div>
                    <div class="dre-line"><span>(-) Comissão ML ({item['TaxaML']}%)</span> <span>R$ {com:.2f}</span></div>
                    <div class="dre-line"><span>(-) Frete ({fr_lbl})</span> <span>R$ {fr_val:.2f}</span></div>
                    <div class="dre-line"><span>(-) Custo CMV</span> <span>R$ {item['CMV']:.2f}</span></div>
                    <div class="dre-line"><span>(-) Extras</span> <span>R$ {item['Extra']:.2f}</span></div>
                    <div class="dre-line" style="color:green;"><span>(+) Bônus</span> <span>R$ {item['Bonus']:.2f}</span></div>
                    <div class="dre-total"><span>RESULTADO</span> <span>R$ {lucro:.2f}</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Excluir", key=f"del{item['id']}"):
                    deletar_produto(item['id'])
                    st.session_state.lista_produtos = carregar_produtos(st.session_state.owner_id)
                    st.rerun()

# === ABA 2: DASHBOARDS (RESTAURADOS) ===
if len(tabs) > 1:
    with tabs[1]:
        if has_plotly and st.session_state.lista_produtos:
            # Prepara Dados
            rows = []
            for item in st.session_state.lista_produtos:
                # Recalcula tudo para o gráfico ficar igual à lista
                pf = item['PrecoUsado'] * (1 - item['DescontoPct']/100)
                fr, _ = identificar_frete(pf)
                if _ == "Manual": fr = item['FreteManual']
                imp = pf * (st.session_state.imposto_padrao/100)
                com = pf * (item['TaxaML']/100)
                luc = pf - (item['CMV'] + item['Extra'] + fr + imp + com) + item['Bonus']
                
                mrg_v = (luc/pf*100) if pf > 0 else 0
                erp_s = item['PrecoERP'] if item['PrecoERP'] > 0 else 1
                mrg_e = (luc/erp_s*100)
                
                status = 'Saudável'
                if mrg_v < 8: status = 'Crítico'
                elif mrg_v < 15: status = 'Atenção'
                
                rows.append({
                    'Produto': item['Produto'], 'Margem Venda': mrg_v, 'Margem ERP': mrg_e,
                    'Lucro': luc, 'Status': status, 'Venda': pf, 
                    'Custo': item['CMV'], 'Imposto': imp, 'Comissão': com, 'Frete': fr
                })
            
            df = pd.DataFrame(rows)
            
            # Seletor de Visão
            visao = st.radio("Base de Análise:", ["Margem Venda", "Margem ERP"], horizontal=True)
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Produtos", len(df))
            k2.metric("Média Margem", f"{df[visao].mean():.1f}%")
            k3.metric("Lucro Total", f"R$ {df['Lucro'].sum():.2f}")
            st.divider()
            
            # Gráfico 1: Semáforo
            fig1 = px.bar(df['Status'].value_counts().reset_index(), x='Status', y='count', color='Status',
                          color_discrete_map={'Crítico': '#EF4444', 'Atenção': '#F59E0B', 'Saudável': '#10B981'}, title="Saúde do Portfolio")
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Dispersão (Preço x Margem)
            st.subheader("Eficiência (Preço x Margem)")
            fig2 = px.scatter(df, x='Venda', y=visao, color='Status', hover_name='Produto',
                              color_discrete_map={'Crítico': '#EF4444', 'Atenção': '#F59E0B', 'Saudável': '#10B981'})
            st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico 3: Decomposição
            st.subheader("Anatomia do Preço (Top 10)")
            df_top = df.sort_values(by='Venda', ascending=False).head(10)
            fig3 = px.bar(df_top, y='Produto', x=['Custo', 'Frete', 'Comissão', 'Imposto', 'Lucro'], orientation='h')
            st.plotly_chart(fig3, use_container_width=True)
            
        else: st.info("Sem dados.")
