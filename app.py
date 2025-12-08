import streamlit as st
import pandas as pd
import time
import sqlite3
import hashlib
import re

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador SaaS - V65", layout="centered", page_icon="💎")

# Verifica Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# --- 2. BANCO DE DADOS (SQLITE) ---
# Cria conexão e tabelas se não existirem
def init_db():
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    # Tabela Usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            plan TEXT
        )
    ''')
    # Tabela Produtos (Ligada ao usuário)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            mlb TEXT, sku TEXT, nome TEXT,
            cmv REAL, frete REAL, taxa_ml REAL, extra REAL,
            preco_erp REAL, margem_erp REAL,
            preco_base REAL, desc_pct REAL, bonus REAL,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÕES DE AUTH E DADOS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return True
    return False

def add_user(username, password, plan):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, plan) VALUES (?,?,?)', 
                  (username, make_hashes(password), plan))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchall()
    conn.close()
    if data:
        if check_hashes(password, data[0][1]):
            return data[0][2] # Retorna o Plano
    return False

def carregar_produtos_usuario(username):
    conn = sqlite3.connect('precificador_saas.db')
    df = pd.read_sql_query("SELECT * FROM products WHERE username = ?", conn, params=(username,))
    conn.close()
    # Converte para lista de dicionários compatível com nosso app
    lista = []
    for _, row in df.iterrows():
        lista.append({
            "id": row['id'], "MLB": row['mlb'], "SKU": row['sku'], "Produto": row['nome'],
            "CMV": row['cmv'], "FreteManual": row['frete'], "TaxaML": row['taxa_ml'], "Extra": row['extra'],
            "PrecoERP": row['preco_erp'], "MargemERP": row['margem_erp'],
            "PrecoBase": row['preco_base'], "DescontoPct": row['desc_pct'], "Bonus": row['bonus']
        })
    return lista

def salvar_produto_db(username, item):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO products (username, mlb, sku, nome, cmv, frete, taxa_ml, extra, preco_erp, margem_erp, preco_base, desc_pct, bonus)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (username, item['MLB'], item['SKU'], item['Produto'], item['CMV'], item['FreteManual'], 
          item['TaxaML'], item['Extra'], item['PrecoERP'], item['MargemERP'], 
          item['PrecoBase'], item['DescontoPct'], item['Bonus']))
    conn.commit()
    conn.close()

def deletar_produto_db(item_id):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def atualizar_produto_db(item_id, campo, valor):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    # Mapeamento de nomes do app para colunas do DB
    mapa = {
        'PrecoBase': 'preco_base', 'DescontoPct': 'desc_pct', 'Bonus': 'bonus', 
        'CMV': 'cmv', 'PrecoERP': 'preco_erp', 'MargemERP': 'margem_erp'
    }
    coluna = mapa.get(campo)
    if coluna:
        c.execute(f"UPDATE products SET {coluna} = ? WHERE id = ?", (valor, item_id))
        conn.commit()
    conn.close()

# --- 3. ESTADO DA SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'plan' not in st.session_state: st.session_state.plan = None
if 'lista_produtos' not in st.session_state: st.session_state.lista_produtos = []

# Variáveis de Input
def init_var(key, val): 
    if key not in st.session_state: st.session_state[key] = val
init_var('n_mlb', ''); init_var('n_sku', ''); init_var('n_nome', '')
init_var('n_cmv', 32.57); init_var('n_extra', 0.00); init_var('n_frete', 18.86)
init_var('n_taxa', 16.5); init_var('n_erp', 85.44); init_var('n_merp', 20.0)

# --- 4. CSS GLOBAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'Inter', sans-serif; }
    
    /* Login Style */
    .login-box {
        background: white; padding: 40px; border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08); text-align: center;
        max-width: 400px; margin: 0 auto;
    }
    
    /* Cards */
    .input-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid #EFEFEF; margin-bottom: 20px; }
    .feed-card { background: white; border-radius: 16px; border: 1px solid #DBDBDB; box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin-bottom: 15px; overflow: hidden; }
    
    /* Pills e Status */
    .pill { padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }
    .pill-green { background-color: #E6FFFA; color: #047857; }
    .pill-yellow { background-color: #FFFBEB; color: #B45309; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; }

    /* Botão */
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; border-radius: 10px; height: 50px; font-weight: 600; }
    
    /* Plano Tag */
    .plan-tag {
        position: fixed; top: 60px; right: 20px; z-index: 999;
        background: #222; color: #fff; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .plan-Silver { background: #BDC3C7; color: #2C3E50; }
    .plan-Gold { background: linear-gradient(45deg, #FFD700, #FDB931); color: #8a6e00; }
    .plan-Platinum { background: linear-gradient(45deg, #2c3e50, #000000); border: 1px solid #444; }

    .header-style { padding: 15px 20px; border-bottom: 1px solid #F0F0F0; display: flex; justify-content: space-between; align-items: center; }
</style>
""", unsafe_allow_html=True)

# --- 5. TELA DE LOGIN / REGISTRO ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_c = st.columns([1,2,1])
    with col_c[1]:
        st.markdown("<h1 style='text-align:center;'>💎 Precificador</h1>", unsafe_allow_html=True)
        tab_login, tab_signup = st.tabs(["Entrar", "Criar Conta"])
        
        with tab_login:
            st.markdown('<div class="input-card">', unsafe_allow_html=True)
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            if st.button("ACESSAR SISTEMA", type="primary", use_container_width=True):
                plan = login_user(username, password)
                if plan:
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.session_state.plan = plan
                    st.session_state.lista_produtos = carregar_produtos_usuario(username)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            st.markdown('</div>', unsafe_allow_html=True)

        with tab_signup:
            st.markdown('<div class="input-card">', unsafe_allow_html=True)
            new_user = st.text_input("Novo Usuário")
            new_pass = st.text_input("Nova Senha", type="password")
            
            st.markdown("---")
            st.caption("Selecione o Plano:")
            new_plan = st.radio("Plano", ["Silver (50 itens)", "Gold (Ilimitado)", "Platinum (Ilimitado + BI)"], index=0)
            
            # Limpa o nome do plano para o DB
            plan_code = new_plan.split(" ")[0]
            
            if st.button("CRIAR CONTA", type="primary", use_container_width=True):
                if add_user(new_user, new_pass, plan_code):
                    st.success("Conta criada! Faça login na aba 'Entrar'.")
                else:
                    st.error("Usuário já existe.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    st.stop() # Para a execução aqui se não estiver logado

# ==============================================================================
# APLICAÇÃO PRINCIPAL (SÓ CARREGA SE LOGADO)
# ==============================================================================

# Mostra a Tag do Plano
st.markdown(f'<div class="plan-tag plan-{st.session_state.plan}">{st.session_state.plan.upper()}</div>', unsafe_allow_html=True)

# Sidebar (Menu e Logout)
with st.sidebar:
    st.title(f"Olá, {st.session_state.user}")
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()
    st.divider()
    
    st.header("Ajustes")
    imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5)
    with st.expander("Tabela Frete ML (<79)"):
        taxa_12_29 = st.number_input("12-29", value=6.25)
        taxa_29_50 = st.number_input("29-50", value=6.50)
        taxa_50_79 = st.number_input("50-79", value=6.75)
        taxa_minima = st.number_input("Min", value=3.25)
    
    # Barra de Progresso do Plano
    qtd_atual = len(st.session_state.lista_produtos)
    if st.session_state.plan == "Silver":
        progresso = min(qtd_atual / 50, 1.0)
        st.divider()
        st.caption(f"Uso do Plano Silver: {qtd_atual}/50")
        st.progress(progresso)
        if qtd_atual >= 50:
            st.error("Limite atingido! Faça upgrade.")

# --- LÓGICA DE NEGÓCIO ---
def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", taxa_50_79
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", taxa_29_50
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", taxa_12_29
    else: return "Tab. Mínima", taxa_minima

def calcular_reverso(custo, alvo, t_ml, imp, f_man):
    custos_1 = custo + f_man
    div = 1 - ((t_ml + imp) / 100)
    if div <= 0: return 0
    p1 = (custos_1 + alvo) / div
    if p1 >= 79: return p1
    
    # Tenta faixas
    for tx, _, pmin, pmax in [(taxa_50_79, "", 50, 79), (taxa_29_50, "", 29, 50), (taxa_12_29, "", 12.5, 29)]:
        p = (custo + tx + alvo) / div
        if pmin <= p < pmax: return p
    return p1

def add_prod():
    # VERIFICA LIMITES DO PLANO
    if st.session_state.plan == "Silver" and len(st.session_state.lista_produtos) >= 50:
        st.toast("Limite do plano Silver atingido!", icon="🔒")
        return

    if not st.session_state.n_nome: return
    
    lucro = st.session_state.n_erp * (st.session_state.n_merp / 100)
    p_sug = calcular_reverso(
        st.session_state.n_cmv + st.session_state.n_extra, lucro,
        st.session_state.n_taxa, imposto_padrao, st.session_state.n_frete
    )
    
    item = {
        "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv, "FreteManual": st.session_state.n_frete, "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra, "PrecoERP": st.session_state.n_erp, "MargemERP": st.session_state.n_merp,
        "PrecoBase": p_sug, "DescontoPct": 0.0, "Bonus": 0.0
    }
    
    # SALVA NO DB
    salvar_produto_db(st.session_state.user, item)
    
    # ATUALIZA LISTA LOCAL
    st.session_state.lista_produtos = carregar_produtos_usuario(st.session_state.user)
    st.toast("Salvo!", icon="✅")
    
    # LIMPA
    st.session_state.n_mlb = ""; st.session_state.n_sku = ""; st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.0

# --- LAYOUT PRINCIPAL ---
st.title("Precificador 2026")

# Definição das Abas conforme o Plano
abas_disponiveis = ["⚡ Operacional"]
if st.session_state.plan == "Platinum":
    abas_disponiveis.append("📊 Dashboards")

tabs = st.tabs(abas_disponiveis)

# === ABA 1: OPERACIONAL ===
with tabs[0]:
    # --- CADASTRO ---
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.caption("NOVO PRODUTO")
    
    col_input1 = st.columns([1,2])
    col_input1[0].text_input("MLB", key="n_mlb")
    col_input1[1].text_input("Produto", key="n_nome")
    
    col_input2 = st.columns(3)
    col_input2[0].number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
    col_input2[1].number_input("Frete Manual", step=0.01, format="%.2f", key="n_frete")
    col_input2[2].text_input("SKU", key="n_sku")
    
    st.markdown("<hr style='margin:10px 0; border-color:#eee;'>", unsafe_allow_html=True)
    
    col_input3 = st.columns(3)
    col_input3[0].number_input("Taxa ML %", step=0.5, format="%.1f", key="n_taxa")
    col_input3[1].number_input("Preço ERP", step=0.01, format="%.2f", key="n_erp")
    col_input3[2].number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")
    
    st.write("")
    if st.session_state.plan == "Silver" and len(st.session_state.lista_produtos) >= 50:
        st.warning("Faça upgrade para Gold para adicionar mais.")
    else:
        st.button("Cadastrar Item", type="primary", use_container_width=True, on_click=add_prod)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- LISTA ---
    if st.session_state.lista_produtos:
        st.caption(f"Gerenciando {len(st.session_state.lista_produtos)} produtos")
        
        for item in reversed(st.session_state.lista_produtos):
            # Cálculos
            pf = item['PrecoBase'] * (1 - item['DescontoPct']/100)
            _, fr = identificar_faixa_frete(pf)
            if _ == "manual": fr = item['FreteManual']
            luc = pf - (item['CMV'] + item['Extra'] + fr + (pf*(imposto_padrao+item['TaxaML'])/100)) + item['Bonus']
            mrg = (luc/pf*100) if pf else 0
            
            erp_safe = item['PrecoERP'] if item['PrecoERP'] > 0 else 1
            mrg_erp = (luc/erp_safe*100)
            
            # Cores
            pill_cls = "pill-green"
            if mrg < 8: pill_cls = "pill-red"
            elif mrg < 15: pill_cls = "pill-yellow"
            
            txt_luc = f"R$ {luc:.2f}"
            if luc > 0: txt_luc = "+ " + txt_luc

            # Card
            st.markdown(f"""
            <div class="feed-card">
                <div class="card-header">
                    <div><div class="sku-text">{item['MLB']} {item['SKU']}</div><div class="title-text">{item['Produto']}</div></div>
                    <div class="{pill_cls} pill">{mrg:.1f}%</div>
                </div>
                <div class="card-body">
                    <div style="font-size: 11px; color:#888; font-weight:600;">PREÇO DE VENDA</div>
                    <div class="price-hero">R$ {pf:.2f}</div>
                    <div style="font-size: 13px; color:#555;">Lucro: <b>{txt_luc}</b></div>
                </div>
                <div class="card-footer">
                   <div class="margin-box"><div>Margem Venda</div><div class="margin-val">{mrg:.1f}%</div></div>
                   <div class="margin-box" style="border-left: 1px solid #eee;"><div>Margem ERP</div><div class="margin-val">{mrg_erp:.1f}%</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("⚙️ Editar"):
                def up_field(k, f, i=item['id']): 
                    atualizar_produto_db(i, f, st.session_state[k])
                    # Atualiza memória local
                    for p in st.session_state.lista_produtos:
                        if p['id'] == i: p[f] = st.session_state[k]

                c1, c2, c3 = st.columns(3)
                c1.number_input("Preço", value=float(item['PrecoBase']), key=f"p{item['id']}", on_change=up_field, args=(f"p{item['id']}", 'PrecoBase'))
                c2.number_input("Desc %", value=float(item['DescontoPct']), key=f"d{item['id']}", on_change=up_f, args=(f"d{item['id']}", 'DescontoPct'))
                c3.number_input("Bônus", value=float(item['Bonus']), key=f"b{item['id']}", on_change=up_f, args=(f"b{item['id']}", 'Bonus'))
                
                st.divider()
                if st.button("Remover", key=f"del{item['id']}"):
                    deletar_produto_db(item['id'])
                    st.session_state.lista_produtos = carregar_produtos_usuario(st.session_state.user)
                    st.rerun()

# === ABA 2: DASHBOARDS (SÓ PLATINUM) ===
if st.session_state.plan == "Platinum" and len(tabs) > 1:
    with tabs[1]:
        if not has_plotly:
            st.error("Instale 'plotly'")
        elif len(st.session_state.lista_produtos) > 0:
            df_dash = pd.DataFrame(st.session_state.lista_produtos)
            # (Lógica de cálculo dos gráficos simplificada para caber)
            # Recalcula colunas necessárias
            df_dash['pf'] = df_dash['PrecoBase'] * (1 - df_dash['DescontoPct']/100)
            df_dash['lucro'] = df_dash.apply(lambda x: x['pf'] - (x['CMV'] + x['Extra'] + (x['pf']*(imposto_padrao+x['TaxaML'])/100)), axis=1)
            
            k1, k2 = st.columns(2)
            k1.metric("Total Produtos", len(df_dash))
            k2.metric("Lucro Estimado", f"R$ {df_dash['lucro'].sum():.2f}")
            
            st.divider()
            st.caption("Visão Exclusiva Platinum")
            # Gráfico Simples
            fig = px.bar(df_dash, x='Produto', y='lucro', title="Lucro por Produto")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados.")
