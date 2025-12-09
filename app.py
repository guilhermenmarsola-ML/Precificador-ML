import streamlit as st
import pandas as pd
import time
import sqlite3
import hashlib

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador SaaS - V65.1", layout="centered", page_icon="💎")

# Verifica Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# --- 2. BANCO DE DADOS (SQLITE) ---
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
    # Tabela Produtos
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            mlb TEXT,
            sku TEXT,
            nome TEXT,
            cmv REAL,
            frete REAL,
            taxa_ml REAL,
            extra REAL,
            preco_erp REAL,
            margem_erp REAL,
            preco_base REAL,
            desc_pct REAL,
            bonus REAL,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 3. AUTH E ACESSO AO DB ---

def make_hashes(password: str) -> str:
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password: str, hashed_text: str) -> bool:
    return make_hashes(password) == hashed_text

def add_user(username: str, password: str, plan: str) -> bool:
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO users(username, password, plan) VALUES (?,?,?)',
            (username, make_hashes(password), plan)
        )
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username: str, password: str):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchall()
    conn.close()
    if data and check_hashes(password, data[0][1]):
        return data[0][2]  # plan
    return False

def carregar_produtos_usuario(username: str):
    conn = sqlite3.connect('precificador_saas.db')
    df = pd.read_sql_query(
        "SELECT * FROM products WHERE username = ?", conn, params=(username,)
    )
    conn.close()
    lista = []
    for _, row in df.iterrows():
        lista.append({
            "id": row["id"],
            "MLB": row["mlb"],
            "SKU": row["sku"],
            "Produto": row["nome"],
            "CMV": row["cmv"],
            "FreteManual": row["frete"],
            "TaxaML": row["taxa_ml"],
            "Extra": row["extra"],
            "PrecoERP": row["preco_erp"],
            "MargemERP": row["margem_erp"],
            "PrecoBase": row["preco_base"],
            "DescontoPct": row["desc_pct"],
            "Bonus": row["bonus"],
        })
    return lista

def salvar_produto_db(username: str, item: dict):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO products (
            username, mlb, sku, nome, cmv, frete, taxa_ml, extra,
            preco_erp, margem_erp, preco_base, desc_pct, bonus
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (
            username,
            item["MLB"],
            item["SKU"],
            item["Produto"],
            item["CMV"],
            item["FreteManual"],
            item["TaxaML"],
            item["Extra"],
            item["PrecoERP"],
            item["MargemERP"],
            item["PrecoBase"],
            item["DescontoPct"],
            item["Bonus"],
        ),
    )
    conn.commit()
    conn.close()

def deletar_produto_db(item_id: int):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def atualizar_produto_db(item_id: int, campo_app: str, valor):
    conn = sqlite3.connect('precificador_saas.db')
    c = conn.cursor()
    mapa = {
        "PrecoBase": "preco_base",
        "DescontoPct": "desc_pct",
        "Bonus": "bonus",
        "CMV": "cmv",
        "PrecoERP": "preco_erp",
        "MargemERP": "margem_erp",
    }
    coluna = mapa.get(campo_app)
    if coluna:
        c.execute(
            f"UPDATE products SET {coluna} = ? WHERE id = ?", (valor, item_id)
        )
        conn.commit()
    conn.close()

# --- 4. ESTADO DE SESSÃO ---

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "plan" not in st.session_state:
    st.session_state.plan = None
if "lista_produtos" not in st.session_state:
    st.session_state.lista_produtos = []

def init_var(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

init_var("n_mlb", "")
init_var("n_sku", "")
init_var("n_nome", "")
init_var("n_cmv", 32.57)
init_var("n_extra", 0.00)
init_var("n_frete", 18.86)
init_var("n_taxa", 16.5)
init_var("n_erp", 85.44)
init_var("n_merp", 20.0)

# --- 5. CSS ---

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'Inter', sans-serif; }

    .input-card {
        background: white; border-radius: 20px; padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid #EFEFEF;
        margin-bottom: 20px;
    }
    .feed-card {
        background: white; border-radius: 16px; border: 1px solid #DBDBDB;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin-bottom: 15px; overflow: hidden;
    }
    .card-header { padding: 15px 20px; border-bottom: 1px solid #F0F0F0;
        display: flex; justify-content: space-between; align-items: center; }
    .card-body { padding: 20px; text-align: center; }
    .card-footer {
        background-color: #F8F9FA; padding: 10px 20px;
        border-top: 1px solid #F0F0F0; display: flex;
        justify-content: space-between; font-size: 11px; color: #666;
    }
    .margin-box { text-align: center; flex: 1; }
    .margin-val { font-weight: 700; font-size: 12px; color: #333; }

    .pill { padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }
    .pill-green { background-color: #E6FFFA; color: #047857; }
    .pill-yellow { background-color: #FFFBEB; color: #B45309; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white;
        border-radius: 10px; height: 50px; font-weight: 600;
    }

    .plan-tag {
        position: fixed; top: 60px; right: 20px; z-index: 999;
        background: #222; color: #fff; padding: 5px 15px;
        border-radius: 20px; font-size: 12px; font-weight: bold;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .plan-Silver { background: #BDC3C7; color: #2C3E50; }
    .plan-Gold { background: linear-gradient(45deg, #FFD700, #FDB931); color: #8a6e00; }
    .plan-Platinum { background: linear-gradient(45deg, #2c3e50, #000000); border: 1px solid #444; }

    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .price-hero { font-size: 32px; font-weight: 800; letter-spacing: -1px; color: #262626; margin: 5px 0; }
</style>
""",
    unsafe_allow_html=True,
)

# --- 6. TELA DE LOGIN / REGISTRO ---

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_c = st.columns([1, 2, 1])
    with col_c[1]:
        st.markdown(
            "<h1 style='text-align:center;'>💎 Precificador</h1>",
            unsafe_allow_html=True,
        )
        tab_login, tab_signup = st.tabs(["Entrar", "Criar Conta"])

        with tab_login:
            st.markdown('<div class="input-card">', unsafe_allow_html=True)
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            if st.button(
                "ACESSAR SISTEMA", type="primary", use_container_width=True
            ):
                plan = login_user(username, password)
                if plan:
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.session_state.plan = plan
                    st.session_state.lista_produtos = carregar_produtos_usuario(
                        username
                    )
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_signup:
            st.markdown('<div class="input-card">', unsafe_allow_html=True)
            new_user = st.text_input("Novo Usuário")
            new_pass = st.text_input("Nova Senha", type="password")
            st.markdown("---")
            st.caption("Selecione o Plano:")
            new_plan = st.radio(
                "Plano",
                [
                    "Silver (50 itens)",
                    "Gold (Ilimitado)",
                    "Platinum (Ilimitado + BI)",
                ],
                index=0,
            )
            plan_code = new_plan.split(" ")[0]  # Silver / Gold / Platinum
            if st.button(
                "CRIAR CONTA", type="primary", use_container_width=True
            ):
                if add_user(new_user, new_pass, plan_code):
                    st.success("Conta criada! Faça login na aba 'Entrar'.")
                else:
                    st.error("Usuário já existe.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# --- 7. APLICAÇÃO PRINCIPAL ---

st.markdown(
    f'<div class="plan-tag plan-{st.session_state.plan}">{st.session_state.plan.upper()}</div>',
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.title(f"Olá, {st.session_state.user}")
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.plan = None
        st.session_state.lista_produtos = []
        st.rerun()

    st.divider()
    st.header("Ajustes")
    imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5)

    with st.expander("Tabela Frete ML (<79)"):
        taxa_12_29 = st.number_input("12-29", value=6.25)
        taxa_29_50 = st.number_input("29-50", value=6.50)
        taxa_50_79 = st.number_input("50-79", value=6.75)
        taxa_minima = st.number_input("Min", value=3.25)

    qtd_atual = len(st.session_state.lista_produtos)
    if st.session_state.plan == "Silver":
        progresso = min(qtd_atual / 50, 1.0)
        st.divider()
        st.caption(f"Uso do Plano Silver: {qtd_atual}/50")
        st.progress(progresso)
        if qtd_atual >= 50:
            st.error("Limite atingido! Faça upgrade.")

# --- 8. LÓGICA DE NEGÓCIO ---

def identificar_faixa_frete(preco: float):
    if preco >= 79.0:
        return "manual", 0.0
    elif 50.0 <= preco < 79.0:
        return "Tab. 50-79", taxa_50_79
    elif 29.0 <= preco < 50.0:
        return "Tab. 29-50", taxa_29_50
    elif 12.5 <= preco < 29.0:
        return "Tab. 12-29", taxa_12_29
    else:
        return "Tab. Mínima", taxa_minima

def calcular_preco_reverso(custo_total, lucro_alvo, t_ml, imp, frete_manual):
    custos_fixos_1 = custo_total + frete_manual
    div = 1 - ((t_ml + imp) / 100)
    if div <= 0:
        return 0.0
    p1 = (custos_fixos_1 + lucro_alvo) / div
    if p1 >= 79.0:
        return p1

    for tx, pmin, pmax in [
        (taxa_50_79, 50.0, 79.0),
        (taxa_29_50, 29.0, 50.0),
        (taxa_12_29, 12.5, 29.0),
    ]:
        p = (custo_total + tx + lucro_alvo) / div
        if pmin <= p < pmax:
            return p
    return p1

def add_prod():
    if (
        st.session_state.plan == "Silver"
        and len(st.session_state.lista_produtos) >= 50
    ):
        st.toast("Limite do plano Silver atingido!", icon="🔒")
        return

    if not st.session_state.n_nome:
        return

    lucro_alvo = st.session_state.n_erp * (st.session_state.n_merp / 100)
    custo_total = st.session_state.n_cmv + st.session_state.n_extra
    p_sug = calcular_preco_reverso(
        custo_total,
        lucro_alvo,
        st.session_state.n_taxa,
        imposto_padrao,
        st.session_state.n_frete,
    )

    item = {
        "MLB": st.session_state.n_mlb,
        "SKU": st.session_state.n_sku,
        "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv,
        "FreteManual": st.session_state.n_frete,
        "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra,
        "PrecoERP": st.session_state.n_erp,
        "MargemERP": st.session_state.n_merp,
        "PrecoBase": p_sug,
        "DescontoPct": 0.0,
        "Bonus": 0.0,
    }

    salvar_produto_db(st.session_state.user, item)
    st.session_state.lista_produtos = carregar_produtos_usuario(
        st.session_state.user
    )
    st.toast("Salvo!", icon="✅")

    st.session_state.n_mlb = ""
    st.session_state.n_sku = ""
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.0

# --- 9. LAYOUT PRINCIPAL ---

st.title("Precificador 2026")

abas = ["⚡ Operacional"]
if st.session_state.plan == "Platinum":
    abas.append("📊 Dashboards")

tabs = st.tabs(abas)

# === ABA OPERACIONAL ===
with tabs[0]:
    # Cadastro
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.caption("NOVO PRODUTO")

    c1 = st.columns([1, 2])
    c1[0].text_input("MLB", key="n_mlb")
    c1[1].text_input("Produto", key="n_nome")

    c2 = st.columns(3)
    c2[0].number_input(
        "Custo (CMV)", step=0.01, format="%.2f", key="n_cmv"
    )
    c2[1].number_input(
        "Frete Manual", step=0.01, format="%.2f", key="n_frete"
    )
    c2[2].text_input("SKU", key="n_sku")

    st.markdown(
        "<hr style='margin:10px 0; border-color:#eee;'>",
        unsafe_allow_html=True,
    )

    c3 = st.columns(3)
    c3[0].number_input(
        "Taxa ML %", step=0.5, format="%.1f", key="n_taxa"
    )
    c3[1].number_input(
        "Preço ERP", step=0.01, format="%.2f", key="n_erp"
    )
    c3[2].number_input(
        "Margem ERP %", step=1.0, format="%.1f", key="n_merp"
    )

    st.write("")
    if (
        st.session_state.plan == "Silver"
        and len(st.session_state.lista_produtos) >= 50
    ):
        st.warning("Faça upgrade para Gold para adicionar mais.")
    else:
        st.button(
            "Cadastrar Item",
            type="primary",
            use_container_width=True,
            on_click=add_prod,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Lista
    if st.session_state.lista_produtos:
        st.caption(
            f"Gerenciando {len(st.session_state.lista_produtos)} produtos"
        )

        for item in reversed(st.session_state.lista_produtos):
            pf = item["PrecoBase"] * (1 - item["DescontoPct"] / 100)
            nome_frete, valor_frete = identificar_faixa_frete(pf)
            if nome_frete == "manual":
                valor_frete = item["FreteManual"]

            imposto_val = pf * (imposto_padrao / 100)
            comissao_val = pf * (item["TaxaML"] / 100)
            custos_totais = (
                item["CMV"]
                + item["Extra"]
                + valor_frete
                + imposto_val
                + comissao_val
            )
            lucro_final = pf - custos_totais + item["Bonus"]

            margem_venda = (lucro_final / pf * 100) if pf > 0 else 0.0
            erp_val = item.get("PrecoERP", 0.0) or 0.0
            margem_erp = (
                (lucro_final / erp_val * 100) if erp_val > 0 else 0.0
            )

            if margem_venda < 8.0:
                pill_cls = "pill-red"
            elif margem_venda < 15.0:
                pill_cls = "pill-yellow"
            else:
                pill_cls = "pill-green"

            txt_luc = (
                f"+ R$ {lucro_final:.2f}"
                if lucro_final > 0
                else f"- R$ {abs(lucro_final):.2f}"
            )

            st.markdown(
                f"""
            <div class="feed-card">
                <div class="card-header">
                    <div>
                        <div class="sku-text">{item['MLB']} {item['SKU']}</div>
                        <div class="title-text">{item['Produto']}</div>
                    </div>
                    <div class="{pill_cls} pill">{margem_venda:.1f}%</div>
                </div>
                <div class="card-body">
                    <div style="font-size: 11px; color:#888; font-weight:600;">PREÇO DE VENDA</div>
                    <div class="price-hero">R$ {pf:.2f}</div>
                    <div style="font-size: 13px; color:#555;">Lucro Líquido: <b>{txt_luc}</b></div>
                </div>
                <div class="card-footer">
                   <div class="margin-box">
                        <div>Margem Venda</div>
                        <div class="margin-val">{margem_venda:.1f}%</div>
                   </div>
                   <div class="margin-box" style="border-left: 1px solid #eee;">
                        <div>Margem ERP</div>
                        <div class="margin-val">{margem_erp:.1f}%</div>
                   </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            with st.expander("⚙️ Editar"):
                def up_field(k, campo, item_id=item["id"]):
                    novo_valor = st.session_state[k]
                    atualizar_produto_db(item_id, campo, novo_valor)
                    # Atualiza na memória local também
                    for p in st.session_state.lista_produtos:
                        if p["id"] == item_id:
                            p[campo] = novo_valor

                c_ed1, c_ed2, c_ed3 = st.columns(3)
                c_ed1.number_input(
                    "Preço",
                    value=float(item["PrecoBase"]),
                    key=f"p{item['id']}",
                    on_change=up_field,
                    args=(f"p{item['id']}", "PrecoBase"),
                )
                c_ed2.number_input(
                    "Desc %",
                    value=float(item["DescontoPct"]),
                    key=f"d{item['id']}",
                    on_change=up_field,
                    args=(f"d{item['id']}", "DescontoPct"),
                )
                c_ed3.number_input(
                    "Bônus",
                    value=float(item["Bonus"]),
                    key=f"b{item['id']}",
                    on_change=up_field,
                    args=(f"b{item['id']}", "Bonus"),
                )

                st.divider()
                if st.button("Remover", key=f"del{item['id']}"):
                    deletar_produto_db(item["id"])
                    st.session_state.lista_produtos = (
                        carregar_produtos_usuario(st.session_state.user)
                    )
                    st.rerun()
    else:
        st.info("Nenhum produto cadastrado ainda.")

# === ABA DASHBOARDS (PLATINUM) ===
if st.session_state.plan == "Platinum" and len(tabs) > 1:
    with tabs[1]:
        if not has_plotly:
            st.error("Instale o pacote 'plotly' para ver os gráficos.")
        elif not st.session_state.lista_produtos:
            st.info("Adicione produtos para visualizar os dashboards.")
        else:
            rows = []
            for item in st.session_state.lista_produtos:
                pf = item["PrecoBase"] * (1 - item["DescontoPct"] / 100)
                nome_frete, valor_frete = identificar_faixa_frete(pf)
                if nome_frete == "manual":
                    valor_frete = item["FreteManual"]
                imposto_val = pf * (imposto_padrao / 100)
                comissao_val = pf * (item["TaxaML"] / 100)
                custos_totais = (
                    item["CMV"]
                    + item["Extra"]
                    + valor_frete
                    + imposto_val
                    + comissao_val
                )
                lucro_final = pf - custos_totais + item["Bonus"]
                margem = (lucro_final / pf * 100) if pf > 0 else 0.0

                status = "Saudável"
                if margem < 8:
                    status = "Crítico"
                elif margem < 15:
                    status = "Atenção"

                rows.append(
                    {
                        "Produto": item["Produto"],
                        "Venda": pf,
                        "Lucro": lucro_final,
                        "Margem": margem,
                        "Status": status,
                    }
                )

            df_dash = pd.DataFrame(rows)

            k1, k2, k3 = st.columns(3)
            k1.metric("Produtos", len(df_dash))
            k2.metric("Margem Média", f"{df_dash['Margem'].mean():.1f}%")
            k3.metric("Lucro Total", f"R$ {df_dash['Lucro'].sum():.2f}")

            st.divider()
            contagem = (
                df_dash["Status"]
                .value_counts()
                .reindex(["Crítico", "Atenção", "Saudável"])
                .fillna(0)
                .reset_index()
            )
            contagem.columns = ["Status", "Qtd"]

            fig1 = px.bar(
                contagem, x="Status", y="Qtd", title="Status de Margem"
            )
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader("Lucro por Produto")
            fig2 = px.bar(
                df_dash, x="Produto", y="Lucro", color="Status"
            )
            st.plotly_chart(fig2, use_container_width=True)
