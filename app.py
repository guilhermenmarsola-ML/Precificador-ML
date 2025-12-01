import streamlit as st
import pandas as pd
import time

# --- 1. CONFIGURAÇÃO DO APP (APP SHELL) ---
st.set_page_config(page_title="Precificador 2026", layout="centered", page_icon="✨")

# --- 2. GERENCIAMENTO DE ESTADO (MEMORY) ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# Inicializa variáveis
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

# Variáveis Temporárias (Cadastro)
init_state('n_mlb', '')
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
# Variáveis Persistentes (Config)
init_state('n_frete', 18.86)
init_state('n_taxa', 16.5)
init_state('n_erp', 85.44)
init_state('n_merp', 20.0)

# --- 3. DESIGN SYSTEM (INSTAGRAM STYLE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');

    /* Reset Geral */
    .stApp {
        background-color: #FAFAFA; /* Fundo Instagram */
        font-family: 'Inter', sans-serif;
    }
    
    /* Remove Padding excessivo do Streamlit */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 700px; /* Largura de App Mobile */
    }

    /* CARD DE INPUT (Novo Post) */
    .input-card {
        background: white;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 10px 40px -10px rgba(0,0,0,0.08);
        margin-bottom: 30px;
        border: 1px solid #EFEFEF;
    }

    /* CARD DO PRODUTO (O "Post") */
    .feed-card {
        background: white;
        border-radius: 16px;
        padding: 0;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        border: 1px solid #DBDBDB;
        overflow: hidden;
    }
    
    .card-header {
        padding: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #FAFAFA;
    }
    
    .card-body {
        padding: 20px;
        text-align: center;
    }
    
    .card-footer {
        background-color: #FAFAFA;
        padding: 12px;
        border-top: 1px solid #EFEFEF;
    }

    /* TIPOGRAFIA */
    .sku-tag { font-size: 11px; color: #8E8E8E; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .prod-title { font-size: 16px; font-weight: 600; color: #262626; margin-top: 4px; }
    
    .price-hero { font-size: 32px; font-weight: 800; letter-spacing: -1px; margin: 10px 0; }
    .profit-pill { 
        font-size: 13px; font-weight: 600; padding: 6px 12px; border-radius: 20px; 
        display: inline-block;
    }
    .pill-green { background-color: #E3F9E5; color: #108A29; }
    .pill-red { background-color: #FFEBEB; color: #E02424; }

    /* DRE VISUAL (Estilo Recibo Apple Wallet) */
    .wallet-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        font-size: 14px;
        color: #555;
        border-bottom: 1px dashed #eee;
    }
    .wallet-total {
        display: flex;
        justify-content: space-between;
        padding-top: 12px;
        margin-top: 5px;
        font-weight: 700;
        font-size: 16px;
        color: #000;
        border-top: 2px solid #000;
    }

    /* BOTÕES */
    div.stButton > button {
        border-radius: 12px;
        font-weight: 600;
        border: none;
        transition: transform 0.1s;
    }
    div.stButton > button:active { transform: scale(0.98); }
    
    /* Botão Principal (Gradiente Instagram/Moderno) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4);
        color: white;
        height: 50px;
        font-size: 16px;
    }

    /* Inputs Limpos */
    div[data-testid="stNumberInput"] input {
        background-color: #FAFAFA;
        border: 1px solid #DBDBDB;
        border-radius: 8px;
        color: #262626;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR (CONFIGURAÇÕES) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
    st.markdown("### Ajustes do Sistema")
    
    with st.expander("📊 Taxas & Impostos", expanded=True):
        imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5)
    
    with st.expander("🚚 Tabela de Frete (<79)", expanded=True):
        taxa_12_29 = st.number_input("Faixa 12-29", value=6.25)
        taxa_29_50 = st.number_input("Faixa 29-50", value=6.50)
        taxa_50_79 = st.number_input("Faixa 50-79", value=6.75)
        taxa_minima = st.number_input("Mínimo", value=3.25)

# --- 5. LÓGICA DE NEGÓCIO ---
def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", taxa_50_79
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", taxa_29_50
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", taxa_12_29
    else: return "Tab. Mínima", taxa_minima

def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_ml_pct, imposto_pct, frete_manual):
    custos_fixos_1 = custo_base + frete_manual
    divisor = 1 - ((taxa_ml_pct + imposto_pct) / 100)
    if divisor <= 0: return 0.0, "Erro"
    
    preco_est_1 = (custos_fixos_1 + lucro_alvo_reais) / divisor
    if preco_est_1 >= 79.00: return preco_est_1, "Frete Manual"
    
    for taxa, nome, p_min, p_max in [
        (taxa_50_79, "Tab. 50-79", 50, 79),
        (taxa_29_50, "Tab. 29-50", 29, 50),
        (taxa_12_29, "Tab. 12-29", 12.5, 29)
    ]:
        custos = custo_base + taxa
        preco = (custos + lucro_alvo_reais) / divisor
        if p_min <= preco < p_max: return preco, nome
        
    return preco_est_1, "Frete Manual"

# --- 6. CALLBACKS (LÓGICA DOS BOTÕES) ---
def adicionar_produto_action():
    if not st.session_state.n_nome:
        st.toast("⚠️ Digite o nome do produto!")
        return

    # Calcula Sugestão
    lucro_alvo = st.session_state.n_erp * (st.session_state.n_merp / 100)
    preco_sug, _ = calcular_preco_sugerido_reverso(
        st.session_state.n_cmv + st.session_state.n_extra,
        lucro_alvo,
        st.session_state.n_taxa,
        imposto_padrao,
        st.session_state.n_frete
    )

    novo_item = {
        "id": int(time.time() * 1000),
        "MLB": st.session_state.n_mlb,
        "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv,
        "FreteManual": st.session_state.n_frete,
        "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra,
        "PrecoERP": st.session_state.n_erp,
        "MargemERP": st.session_state.n_merp,
        "PrecoBase": preco_sug,
        "DescontoPct": 0.0,
        "Bonus": 0.0,
    }
    st.session_state.lista_produtos.append(novo_item)
    st.toast("Adicionado ao Feed!", icon="🎉")

    # Limpa APENAS dados do produto, mantém configurações
    st.session_state.n_mlb = ""
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00
    st.session_state.n_extra = 0.00

# ==============================================================================
# 7. INTERFACE PRINCIPAL
# ==============================================================================

# Cabeçalho Limpo
col_h1, col_h2 = st.columns([3, 1])
col_h1.title("Precificador")
col_h2.markdown(f"<div style='text-align:right; color:#8E8E8E; padding-top:15px;'>{len(st.session_state.lista_produtos)} itens</div>", unsafe_allow_html=True)

# --- INPUT CARD (O CRIADOR DE POSTS) ---
st.markdown('<div class="input-card">', unsafe_allow_html=True)

# Linha 1: Identificação
c1, c2 = st.columns([1, 2])
c1.text_input("Código", key="n_mlb", placeholder="MLB...")
c2.text_input("Produto", key="n_nome", placeholder="O que vamos vender?")

# Linha 2: Custos
c3, c4 = st.columns(2)
c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
c4.number_input("Frete (>79)", step=0.01, format="%.2f", key="n_frete")

# Divider Minimalista
st.markdown("<div style='height: 1px; background-color: #EFEFEF; margin: 15px 0;'></div>", unsafe_allow_html=True)

# Linha 3: Estratégia (Labels menores)
c5, c6, c7 = st.columns(3)
c5.number_input("Comissão %", step=0.5, format="%.1f", key="n_taxa")
c6.number_input("Preço ERP", step=0.01, format="%.2f", key="n_erp")
c7.number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")

st.write("")
st.button("✨ Precificar e Adicionar", type="primary", use_container_width=True, on_click=adicionar_produto_action)
st.markdown('</div>', unsafe_allow_html=True)

# --- FEED DE PRODUTOS ---
if st.session_state.lista_produtos:
    
    # Loop Reverso (Mais novo em cima)
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        # --- MOTOR DE CÁLCULO (LIVE) ---
        preco_base_calc = item['PrecoBase']
        desc_calc = item['DescontoPct']
        preco_final_calc = preco_base_calc * (1 - (desc_calc / 100))
        
        nome_frete_real, valor_frete_real = identificar_faixa_frete(preco_final_calc)
        if nome_frete_real == "manual": valor_frete_real = item['FreteManual']
        
        imposto_val = preco_final_calc * (imposto_padrao / 100)
        comissao_val = preco_final_calc * (item['TaxaML'] / 100)
        custos_totais = item['CMV'] + item['Extra'] + valor_frete_real + imposto_val + comissao_val
        lucro_final = preco_final_calc - custos_totais + item['Bonus']
        margem_final = (lucro_final / preco_final_calc * 100) if preco_final_calc > 0 else 0
        
        # Cores Dinâmicas
        cor_valor = "#262626"
        classe_pill = "pill-green"
        txt_lucro = f"+ R$ {lucro_final:.2f}"
        
        if lucro_final < 0:
            cor_valor = "#E02424"
            classe_pill = "pill-red"
            txt_lucro = f"- R$ {abs(lucro_final):.2f}"

        # --- ESTRUTURA DO CARD ---
        st.markdown(f"""
        <div class="feed-card">
            <div class="card-header">
                <div>
                    <div class="sku-tag">{item['MLB']}</div>
                    <div class="prod-title">{item['Produto']}</div>
                </div>
                <div class="profit-pill {classe_pill}">{txt_lucro}</div>
            </div>
            <div class="card-body">
                <div style="font-size: 12px; color: #8E8E8E; font-weight: 500;">PREÇO DE VENDA</div>
                <div class="price-hero" style="color: {cor_valor}">R$ {preco_final_calc:.2f}</div>
                <div style="font-size: 12px; color: #8E8E8E;">Margem Líquida: <b>{margem_final:.1f}%</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- ÁREA DE AÇÃO (EXPANDER) ---
        # Não colocamos dentro do HTML para que os Inputs do Streamlit funcionem
        with st.expander("⚙️ Editar & Detalhes Financeiros"):
            
            # 1. Inputs de Edição
            ec1, ec2, ec3 = st.columns(3)
            
            def update_item(idx=i, key_id=item['id'], field=None, key_st=None):
                st.session_state.lista_produtos[idx][field] = st.session_state[key_st]

            ec1.number_input("Preço Tabela", value=float(item['PrecoBase']), step=0.5, key=f"pb_{item['id']}", 
                             on_change=update_item, args=(i, item['id'], 'PrecoBase', f"pb_{item['id']}"))
            
            ec2.number_input("Desconto %", value=float(item['DescontoPct']), step=0.5, key=f"dc_{item['id']}", 
                             on_change=update_item, args=(i, item['id'], 'DescontoPct', f"dc_{item['id']}"))
            
            ec3.number_input("Rebate (R$)", value=float(item['Bonus']), step=0.01, key=f"bn_{item['id']}", 
                             on_change=update_item, args=(i, item['id'], 'Bonus', f"bn_{item['id']}"))
            
            st.write("")
            
            # 2. DRE VISUAL (HTML Puro para não quebrar layout)
            st.markdown("##### 📄 Extrato Financeiro")
            
            dre_html = f"""
            <div style="background-color: #FAFAFA; padding: 15px; border-radius: 12px;">
                <div class="wallet-row"><span>(+) Preço Tabela</span> <span>R$ {preco_base_calc:.2f}</span></div>
                <div class="wallet-row" style="color: #E02424;"><span>(-) Desconto ({desc_calc}%)</span> <span>- R$ {preco_base_calc - preco_final_calc:.2f}</span></div>
                <div class="wallet-row" style="font-weight: 700; color: #000;"><span>(=) RECEITA BRUTA</span> <span>R$ {preco_final_calc:.2f}</span></div>
                <div style="margin: 10px 0; border-bottom: 1px solid #eee;"></div>
                <div class="wallet-row"><span>(-) Impostos ({imposto_padrao}%)</span> <span>- R$ {imposto_val:.2f}</span></div>
                <div class="wallet-row"><span>(-) Comissão ML ({item['TaxaML']}%)</span> <span>- R$ {comissao_val:.2f}</span></div>
                <div class="wallet-row"><span>(-) Frete ({nome_frete_real})</span> <span>- R$ {valor_frete_real:.2f}</span></div>
                <div class="wallet-row"><span>(-) Custo CMV</span> <span>- R$ {item['CMV']:.2f}</span></div>
                <div class="wallet-row" style="color: #108A29;"><span>(+) Rebate/Bônus</span> <span>+ R$ {item['Bonus']:.2f}</span></div>
                
                <div class="wallet-total" style="color: {'#108A29' if lucro_final > 0 else '#E02424'}; border-color: {'#108A29' if lucro_final > 0 else '#E02424'};">
                    <span>LUCRO LÍQUIDO</span>
                    <span>R$ {lucro_final:.2f}</span>
                </div>
            </div>
            """
            st.markdown(dre_html, unsafe_allow_html=True)
            
            # Botão Excluir (Discreto)
            st.write("")
            def deletar(idx=i): del st.session_state.lista_produtos[idx]
            st.button("🗑️ Remover este item", key=f"btn_del_{item['id']}", on_click=deletar, help="Apagar da lista")

        # Espaçador
        st.write("") 

    # --- FOOTER ---
    st.divider()
    col_d, col_c = st.columns(2)
    
    # Exportação
    dados_csv = []
    for it in st.session_state.lista_produtos:
        # Recalcula para CSV
        pf = it['PrecoBase'] * (1 - it['DescontoPct']/100)
        _, fr = identificar_faixa_frete(pf)
        if _ == "manual": fr = it['FreteManual']
        luc = pf - (it['CMV'] + it['Extra'] + fr + (pf*(imposto_padrao+it['TaxaML'])/100)) + it['Bonus']
        dados_csv.append({"MLB": it['MLB'], "Produto": it['Produto'], "Preco Final": pf, "Lucro": luc})
        
    df_final = pd.DataFrame(dados_csv)
    csv = df_final.to_csv(index=False).encode('utf-8')
    
    col_d.download_button("📥 Baixar Excel", csv, "precificacao_2026.csv", "text/csv", use_container_width=True)
    
    def limpar_tudo(): st.session_state.lista_produtos = []
    col_c.button("Limpar Tudo", on_click=limpar_tudo, use_container_width=True)

else:
    # Estado Vazio (Zero State) Bonito
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px; color: #8E8E8E;">
        <div style="font-size: 40px; margin-bottom: 10px;">✨</div>
        <h3 style="color: #262626;">Tudo pronto!</h3>
        <p>Adicione seu primeiro produto acima para começar a precificar.</p>
    </div>
    """, unsafe_allow_html=True)
