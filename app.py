import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
import base64
import os
import xml.etree.ElementTree as ET

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador PRO - V70 Fiscal", layout="wide", page_icon="🏛️")
DB_NAME = 'precificador_fiscal_v70.db'

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

# --- 3. BANCO DE DADOS (COM CAMPOS FISCAIS) ---
def init_db(reset=False):
    if reset and os.path.exists(DB_NAME):
        try: os.remove(DB_NAME)
        except: pass
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabela Usuários (Com Regime Tributário)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            name TEXT,
            plan TEXT,
            tax_regime TEXT DEFAULT 'Simples Nacional',
            uf_origin TEXT DEFAULT 'SP',
            owner_id INTEGER DEFAULT 0
        )
    ''')
    
    # Tabela Produtos (Com Estrutura de Camadas e Impostos)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            mlb TEXT, sku TEXT, nome TEXT,
            
            -- Custos Base
            cmv REAL, frete REAL, extra REAL,
            
            -- Camada 1: Estratégia
            strategy_type TEXT, -- 'erp_target' ou 'real_margin'
            preco_erp REAL, margem_erp_target REAL,
            
            -- Camada 2: Fiscal
            tax_mode TEXT, -- 'average' ou 'real'
            tax_avg_rate REAL, -- Taxa média simples
            
            -- Detalhe Fiscal (Lucro Real/Presumido)
            ncm TEXT,
            icms_rate REAL, pis_cofins_rate REAL, ipi_rate REAL,
            credit_icms REAL, credit_pis_cofins REAL, -- Créditos na compra
            
            -- Resultado
            preco_final REAL, margem_final REAL, lucro_final REAL,
            
            -- Taxas MKT
            taxa_ml REAL,
            desc_pct REAL, bonus REAL
        )
    ''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_NAME): init_db()

def get_db(): return sqlite3.connect(DB_NAME)
def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- CRUD BÁSICO ---
def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        data = c.fetchone()
        if data and check_hashes(password, data[2]):
            # Retorna dict com dados incluindo regime
            return {"id": data[0], "username": data[1], "name": data[3], "plan": data[4], "regime": data[5], "uf": data[6], "owner_id": data[7]}
    except: pass
    finally: conn.close()
    return None

def update_user_fiscal(user_id, regime, uf):
    conn = get_db()
    conn.execute("UPDATE users SET tax_regime = ?, uf_origin = ? WHERE id = ?", (regime, uf, user_id))
    conn.commit()
    conn.close()

def save_product_db(item, user_id):
    conn = get_db()
    c = conn.cursor()
    # Verifica se update ou insert
    if 'id' in item and item['id']:
        # Update logic here (simplificado: deleta e cria novo para o exemplo, em prod faríamos UPDATE)
        c.execute("DELETE FROM products WHERE id = ?", (item['id'],))
    
    c.execute('''INSERT INTO products (
        owner_id, mlb, sku, nome, cmv, frete, extra, 
        strategy_type, preco_erp, margem_erp_target, 
        tax_mode, tax_avg_rate, ncm, icms_rate, pis_cofins_rate, ipi_rate, credit_icms, credit_pis_cofins,
        preco_final, margem_final, lucro_final, taxa_ml, desc_pct, bonus
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        user_id, item['MLB'], item['SKU'], item['Produto'], item['CMV'], item['FreteManual'], item['Extra'],
        item['Strategy'], item['PrecoERP'], item['MargemERP'],
        item['TaxMode'], item['TaxAvg'], item['NCM'], item['ICMS_Out'], item['PIS_COFINS_Out'], item['IPI'], item['ICMS_In'], item['PIS_COFINS_In'],
        item['PrecoFinal'], item['Margem'], item['Lucro'], item['TaxaML'], item['DescontoPct'], item['Bonus']
    ))
    conn.commit()
    conn.close()

def load_products_db(user_id):
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM products WHERE owner_id = ?", conn, params=(user_id,))
    conn.close()
    lista = []
    for _, row in df.iterrows():
        lista.append({
            "id": row['id'], "MLB": row['mlb'], "SKU": row['sku'], "Produto": row['nome'],
            "CMV": row['cmv'], "FreteManual": row['frete'], "Extra": row['extra'],
            "Strategy": row['strategy_type'], "PrecoERP": row['preco_erp'], "MargemERP": row['margem_erp_target'],
            "TaxMode": row['tax_mode'], "TaxAvg": row['tax_avg_rate'], 
            "NCM": row['ncm'], "ICMS_Out": row['icms_rate'], "PIS_COFINS_Out": row['pis_cofins_rate'], 
            "IPI": row['ipi_rate'], "ICMS_In": row['credit_icms'], "PIS_COFINS_In": row['credit_pis_cofins'],
            "PrecoFinal": row['preco_final'], "Margem": row['margem_final'], "Lucro": row['lucro_final'],
            "TaxaML": row['taxa_ml'], "DescontoPct": row['desc_pct'], "Bonus": row['bonus']
        })
    return lista

def delete_product_db(item_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

# --- 4. MOTOR DE CÁLCULO FISCAL (INTELLIGENCE) ---
def calcular_preco_inteligente(dados):
    # 1. Custo Líquido (Abate Créditos se for Lucro Real)
    custo_liquido = dados['CMV']
    creditos = 0.0
    
    # Se Lucro Real, o custo do produto diminui pois recupera imposto
    if dados['Regime'] == 'Lucro Real' and dados['TaxMode'] == 'Real':
        creditos = dados['CMV'] * ((dados['ICMS_In'] + dados['PIS_COFINS_In']) / 100)
        custo_liquido = dados['CMV'] - creditos

    # 2. Custos Fixos Totais
    custos_fixos_venda = dados['FreteManual'] + dados['Extra']
    
    # 3. Taxas sobre a Venda (Markdowns)
    # Soma de todas as alíquotas que incidem sobre o preço CHEIO
    taxas_venda_pct = dados['TaxaML'] + dados['DescontoPct']
    
    if dados['TaxMode'] == 'Average':
        taxas_venda_pct += dados['TaxAvg']
    else:
        # Soma ICMS, PIS, COFINS, IPI de Saída
        taxas_venda_pct += (dados['ICMS_Out'] + dados['PIS_COFINS_Out'] + dados['IPI'])

    # 4. Definição do Preço Alvo
    preco_final = 0.0
    
    if dados['Strategy'] == 'erp_target':
        # Cenário 1: Baseado em Meta do ERP (Manter lucro em reais)
        # Lucro Alvo = PrecoERP * MargemERP
        lucro_alvo = dados['PrecoERP'] * (dados['MargemERP'] / 100)
        
        # Fórmula: Preço = (CustoLiq + CustosFixos + LucroAlvo - Bonus) / (1 - Taxas%)
        divisor = 1 - (taxas_venda_pct / 100)
        if divisor > 0:
            preco_final = (custo_liquido + custos_fixos_venda + lucro_alvo - dados['Bonus']) / divisor
            
    else:
        # Cenário 2: Margem Real sobre o Preço Formado (Markup)
        # Fórmula Markup: Preço = (CustoLiq + CustosFixos - Bonus) / (1 - (Taxas% + MargemDesejada%))
        margem_target = dados['MargemERP'] # Reutilizando campo para margem desejada
        divisor = 1 - ((taxas_venda_pct + margem_target) / 100)
        if divisor > 0:
            preco_final = (custo_liquido + custos_fixos_venda - dados['Bonus']) / divisor

    # Recalcula Lucro Real Final para exibição
    impostos_reais = preco_final * (taxas_venda_pct / 100) # Simplificação para DRE
    # Nota: No Lucro Real, o imposto a pagar é (Débito - Crédito), mas no DRE de venda costuma-se abater o imposto cheio e mostrar o custo cheio ou o custo liquido.
    # Vamos usar a abordagem gerencial: Receita - ImpostosSobreVenda - Custos - Frete + Bonus
    
    # Ajuste fino: Se for Lucro Real, o "Custo" na DRE deve ser o custo original, 
    # mas o "Imposto" deve considerar o abatimento? 
    # Padrão DRE Gerencial:
    # Receita Liquida = Venda - Impostos Venda
    # Margem Contribuição = RecLiq - CustoVendido - DespesasVar
    
    lucro_final = preco_final - (custo_liquido + custos_fixos_venda + (preco_final * (taxas_venda_pct/100))) + dados['Bonus']
    margem_final = (lucro_final / preco_final * 100) if preco_final > 0 else 0
    
    return preco_final, lucro_final, margem_final, custo_liquido

# --- 5. INTERFACE DO USUÁRIO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# LOGIN SCREEN
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>🏛️ Precificador Fiscal</h1>", unsafe_allow_html=True)
        
        tab_login, tab_create = st.tabs(["Acessar", "Criar Conta"])
        with tab_login:
            u = st.text_input("Usuário", key="login_u")
            p = st.text_input("Senha", type="password", key="login_p")
            if st.button("Entrar", type="primary", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.user = user
                    st.session_state.logged_in = True
                    st.session_state.lista_produtos = load_products_db(user['id'] if user['owner_id'] == 0 else user['owner_id'])
                    reiniciar_app()
                else: st.error("Dados inválidos.")
        
        with tab_create:
            nu = st.text_input("Novo Usuário", key="new_u")
            np = st.text_input("Nova Senha", type="password", key="new_p")
            nn = st.text_input("Nome", key="new_n")
            npl = st.selectbox("Plano", ["Silver", "Gold", "Platinum"])
            if st.button("Registrar", type="primary"):
                # Simplificado para exemplo (sem add_user completo aqui no snippet, usar lógica anterior)
                st.info("Funcionalidade de registro (usar código da V68). Para teste, use login.")
    st.stop()

# --- ÁREA LOGADA ---

# SIDEBAR FISCAL
with st.sidebar:
    st.header(f"Olá, {st.session_state.user['name']}")
    
    # 1. Configuração da Empresa
    with st.expander("🏢 Configuração Fiscal (Empresa)", expanded=True):
        regimes = ["Simples Nacional", "Lucro Presumido", "Lucro Real", "MEI"]
        idx_reg = regimes.index(st.session_state.user.get('regime', 'Simples Nacional'))
        novo_regime = st.selectbox("Regime Tributário", regimes, index=idx_reg)
        
        ufs = ["SP", "RJ", "MG", "PR", "SC", "RS", "Outros"]
        idx_uf = ufs.index(st.session_state.user.get('uf', 'SP')) if st.session_state.user.get('uf', 'SP') in ufs else 0
        nova_uf = st.selectbox("Estado Origem", ufs, index=idx_uf)
        
        if novo_regime != st.session_state.user.get('regime') or nova_uf != st.session_state.user.get('uf'):
            update_user_fiscal(st.session_state.user['id'], novo_regime, nova_uf)
            st.session_state.user['regime'] = novo_regime
            st.session_state.user['uf'] = nova_uf
            st.success("Fiscal Atualizado!")
            time.sleep(0.5)
            reiniciar_app()

    st.divider()
    if st.button("Sair"):
        st.session_state.logged_in = False
        reiniciar_app()

# MAIN AREA
st.title("Engenharia de Preços & Fiscal")

# --- XML IMPORTER ---
with st.expander("📥 Importar XML da Nota Fiscal (NFe)", expanded=False):
    xml_file = st.file_uploader("Arraste o XML da NFe de Entrada", type=['xml'])
    if xml_file:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Tenta pegar dados do primeiro produto
            det = root.find('.//nfe:det', ns)
            if det:
                prod = det.find('nfe:prod', ns)
                xProd = prod.find('nfe:xProd', ns).text
                vUnCom = float(prod.find('nfe:vUnCom', ns).text)
                NCM = prod.find('nfe:NCM', ns).text
                
                st.info(f"XML Lido: {xProd} | NCM: {NCM} | Custo: R$ {vUnCom:.2f}")
                
                if st.button("Usar dados do XML no Cadastro"):
                    st.session_state.n_nome = xProd
                    st.session_state.n_cmv = vUnCom
                    st.session_state.n_ncm = NCM
                    st.toast("Dados preenchidos!")
        except Exception as e:
            st.error(f"Erro ao ler XML: {e}")

# --- INPUT CARD (CAMADAS) ---
st.markdown("""<style>.apple-card {background: white; border-radius: 18px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E5E5EA;}</style>""", unsafe_allow_html=True)
st.markdown('<div class="apple-card">', unsafe_allow_html=True)

# CAMADA 1: DADOS BÁSICOS
c1, c2, c3 = st.columns([1, 2, 1])
if 'n_mlb' not in st.session_state: st.session_state.n_mlb = ""
if 'n_nome' not in st.session_state: st.session_state.n_nome = ""
if 'n_cmv' not in st.session_state: st.session_state.n_cmv = 0.0
if 'n_ncm' not in st.session_state: st.session_state.n_ncm = ""

c1.text_input("MLB", key="n_mlb")
c2.text_input("Produto", key="n_nome")
c3.text_input("NCM (Fiscal)", key="n_ncm", help="Necessário para cálculo preciso")

c4, c5, c6 = st.columns(3)
c4.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
c5.number_input("Frete Manual", value=18.86, step=0.01, key="n_frete")
c6.number_input("Extras", value=0.00, step=0.01, key="n_extra")

st.markdown("---")

# CAMADA 2: ESTRATÉGIA DE PREÇO
st.subheader("1. Estratégia de Precificação")
strategy = st.radio("Como calcular?", ["Meta baseada no ERP (Manter Lucro R$)", "Margem Real sobre Custo (Markup)"], horizontal=True)
strat_code = 'erp_target' if "ERP" in strategy else 'real_margin'

col_strat1, col_strat2 = st.columns(2)
if strat_code == 'erp_target':
    col_strat1.number_input("Preço ERP (R$)", value=85.44, step=0.01, key="n_erp")
    col_strat2.number_input("Margem ERP (%)", value=20.0, step=1.0, key="n_merp")
else:
    col_strat1.empty()
    col_strat2.number_input("Margem Desejada (%)", value=20.0, step=1.0, key="n_merp", help="Margem líquida alvo sobre a venda")

st.markdown("---")

# CAMADA 3: INTELEGÊNCIA FISCAL
st.subheader(f"2. Inteligência Fiscal ({st.session_state.user['regime']})")

tax_mode = st.radio("Detalhamento de Impostos:", ["Média Simples (Padrão)", "Apuração Real (Crédito/Débito)"], horizontal=True)
tax_mode_code = 'Average' if "Média" in tax_mode else 'Real'

# Alíquotas Padrão Sugeridas (O "Cérebro Fiscal")
default_pis_cofins_out = 9.25 if st.session_state.user['regime'] == 'Lucro Real' else 3.65 if st.session_state.user['regime'] == 'Lucro Presumido' else 0.0
default_icms_out = 18.0 if st.session_state.user['regime'] != 'Simples Nacional' else 0.0
default_avg = 7.0 if st.session_state.user['regime'] == 'Simples Nacional' else 28.0

if tax_mode_code == 'Average':
    st.number_input("Taxa Média de Impostos (%)", value=default_avg, step=0.5, key="n_tax_avg")
    # Zera os detalhados para não dar erro
    n_icms_out = n_pis_out = n_ipi = n_icms_in = n_pis_in = 0.0
else:
    f1, f2, f3 = st.columns(3)
    n_icms_out = f1.number_input("ICMS Saída (%)", value=default_icms_out, step=0.5)
    n_pis_out = f2.number_input("PIS/COFINS Saída (%)", value=default_pis_cofins_out, step=0.5)
    n_ipi = f3.number_input("IPI Saída (%)", value=0.0, step=0.5)
    
    st.caption("Créditos (Recuperação na Compra - Apenas Lucro Real)")
    f4, f5 = st.columns(2)
    n_icms_in = f4.number_input("Crédito ICMS (%)", value=default_icms_out if st.session_state.user['regime'] == 'Lucro Real' else 0.0)
    n_pis_in = f5.number_input("Crédito PIS/COF (%)", value=default_pis_cofins_out if st.session_state.user['regime'] == 'Lucro Real' else 0.0)

st.markdown("---")
mkt1, mkt2, mkt3 = st.columns(3)
mkt1.number_input("Comissão ML (%)", value=16.5, key="n_taxa")
mkt2.number_input("Desconto (%)", value=0.0, key="n_desc")
mkt3.number_input("Bônus/Rebate (R$)", value=0.0, key="n_bonus")

# --- PROCESSAMENTO DO CÁLCULO ---
dados_calc = {
    'CMV': st.session_state.n_cmv,
    'FreteManual': st.session_state.n_frete,
    'Extra': st.session_state.n_extra,
    'Regime': st.session_state.user['regime'],
    'Strategy': strat_code,
    'PrecoERP': st.session_state.get('n_erp', 0),
    'MargemERP': st.session_state.n_merp,
    'TaxMode': tax_mode_code,
    'TaxAvg': st.session_state.get('n_tax_avg', 0),
    'ICMS_Out': locals().get('n_icms_out', 0), 'PIS_COFINS_Out': locals().get('n_pis_out', 0), 'IPI': locals().get('n_ipi', 0),
    'ICMS_In': locals().get('n_icms_in', 0), 'PIS_COFINS_In': locals().get('n_pis_in', 0),
    'TaxaML': st.session_state.n_taxa, 'DescontoPct': st.session_state.n_desc, 'Bonus': st.session_state.n_bonus
}

pf, luc, mrg, custo_liq = calcular_preco_inteligente(dados_calc)

# Exibição do Resultado
st.markdown(f"""
<div style="background:#F2F2F7; padding:15px; border-radius:12px; display:flex; justify-content:space-around; align-items:center; border:1px solid #D1D1D6;">
    <div style="text-align:center;">
        <div style="font-size:10px; font-weight:bold; color:#86868B;">CUSTO LÍQUIDO</div>
        <div style="font-size:18px; font-weight:bold;">R$ {custo_liq:.2f}</div>
    </div>
    <div style="font-size:24px; color:#90caf9;">➔</div>
    <div style="text-align:center;">
        <div style="font-size:10px; font-weight:bold; color:#0071E3;">PREÇO VENDA</div>
        <div style="font-size:24px; font-weight:800; color:#0071E3;">R$ {pf:.2f}</div>
    </div>
    <div style="text-align:center;">
        <div style="font-size:10px; font-weight:bold; color:{'#34C759' if luc>0 else '#FF3B30'};">LUCRO</div>
        <div style="font-size:18px; font-weight:bold; color:{'#34C759' if luc>0 else '#FF3B30'};">R$ {luc:.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")

if st.button("SALVAR NA LISTA", type="primary", use_container_width=True):
    if st.session_state.n_nome:
        # Monta objeto completo para salvar
        item_save = dados_calc.copy()
        item_save.update({
            'MLB': st.session_state.n_mlb, 'SKU': '', 'Produto': st.session_state.n_nome, 'NCM': st.session_state.n_ncm,
            'PrecoFinal': pf, 'Margem': mrg, 'Lucro': luc
        })
        save_product_db(item_save, st.session_state.owner_id)
        st.success("Salvo!")
        time.sleep(1)
        st.rerun()
    else:
        st.error("Nome obrigatório")

st.markdown('</div>', unsafe_allow_html=True)

# LISTAGEM DE PRODUTOS
st.markdown("### 📋 Produtos")
lista = load_products_db(st.session_state.owner_id)
if lista:
    for item in lista:
        with st.expander(f"{item['Produto']} | R$ {item['PrecoFinal']:.2f}"):
            st.write(f"**MLB:** {item['MLB']} | **Regime:** {st.session_state.user['regime']}")
            st.write(f"**Lucro:** R$ {item['Lucro']:.2f} ({item['Margem']:.1f}%)")
            if st.button("Excluir", key=f"del_{item['id']}"):
                delete_product_db(item['id'])
                st.rerun()
else:
    st.info("Lista vazia.")
