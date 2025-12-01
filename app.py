import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Precificador ML - Premium", layout="wide", page_icon="💎")

# --- GERENCIAMENTO DE ESTADO ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

# Variáveis do Formulário
init_state('n_mlb', 'MLB-')
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
# Variáveis Persistentes
init_state('n_frete', 18.86)
init_state('n_taxa', 16.5)
init_state('n_erp', 85.44)
init_state('n_merp', 20.0)

# --- CSS PREMIUM (DESIGN SYSTEM) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f4f6f9; /* Fundo Cinza Gelo */
    }

    /* Títulos */
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    /* Cards Brancos (Container Principal) */
    .premium-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03); /* Sombra Suave */
        border: 1px solid #f1f5f9;
        margin-bottom: 24px;
    }

    /* Painel de Sugestão (Hero Gradient) */
    .hero-box {
        background: linear-gradient(120deg, #6366f1 0%, #3b82f6 100%); /* Roxo para Azul */
        padding: 25px;
        border-radius: 16px;
        color: white;
        box-shadow: 0 10px 25px rgba(59, 130, 246, 0.25);
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .hero-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        opacity: 0.9;
        margin-bottom: 5px;
    }
    .hero-value {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -1px;
    }
    .hero-sub {
        font-size: 0.9rem;
        opacity: 0.8;
        background: rgba(255,255,255,0.15);
        padding: 4px 10px;
        border-radius: 20px;
        display: inline-block;
        margin-top: 5px;
    }
    .hero-arrow {
        font-size: 2rem;
        color: rgba(255,255,255,0.6);
        padding: 0 20px;
    }

    /* Botão Principal */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%); /* Verde Esmeralda */
        color: white;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
        transition: all 0.3s ease;
        width: 100%;
        height: 55px;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(16, 185, 129, 0.3);
        background: linear-gradient(90deg, #059669 0%, #047857 100%);
    }

    /* Lista de Produtos (Cards Individuais) */
    .product-item-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px 20px;
        border-left: 6px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 12px;
        transition: transform 0.2s;
    }
    .product-item-card:hover {
        transform: translateX(5px);
    }
    
    /* Indicadores de Status */
    .status-green { border-left-color: #10b981 !important; }
    .status-red { border-left-color: #ef4444 !important; }
    
    .price-tag {
        font-family: 'Inter', monospace;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .text-green { color: #059669; }
    .text-red { color: #dc2626; }

    /* Ajustes finos do Streamlit */
    div[data-testid="stExpander"] {
        border: none;
        box-shadow: none;
        background-color: #f8fafc;
        border-radius: 8px;
    }
    hr { margin: 1.5rem 0; border-color: #e2e8f0; }
    
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (Dark Mode Style) ---
with st.sidebar:
    st.markdown("### ⚙️ Painel de Controle")
    st.markdown("---")
    
    with st.expander("📊 Taxas Globais", expanded=True):
        imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5, format="%.2f")
    
    with st.expander("🚚 Tabela Frete ML (<79)", expanded=True):
        taxa_12_29 = st.number_input("R$ 12,50 - 29,00", value=6.25)
        taxa_29_50 = st.number_input("R$ 29,00 - 50,00", value=6.50)
        taxa_50_79 = st.number_input("R$ 50,00 - 79,00", value=6.75)
        taxa_minima = st.number_input("Abaixo de R$ 12,50", value=3.25)
    
    st.markdown("---")
    st.caption("v22.0 - Premium Edition")

# --- LÓGICA DE NEGÓCIO (Mantida Intacta) ---
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

# --- CALLBACKS ---
def adicionar_produto_action():
    if not st.session_state.n_nome:
        st.error("⚠️ Digite o nome do produto!")
        return

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
    st.toast("Produto adicionado com sucesso!", icon="✨")

    # Limpeza
    st.session_state.n_mlb = "MLB-"
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00
    st.session_state.n_extra = 0.00

# ==============================================================================
# 🚀 APLICAÇÃO VISUAL
# ==============================================================================

st.markdown("## 💎 Precificação Estratégica")
st.markdown("Defina seus custos, estabeleça sua meta e deixe o sistema calcular.")

# 1. BLOCO BRANCO (CARD) DE INPUTS
st.markdown('<div class="premium-card">', unsafe_allow_html=True)
st.markdown("#### 1. Cadastro & Custos")
c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
c1.text_input("SKU / MLB", key="n_mlb")
c2.text_input("Nome do Produto", key="n_nome", placeholder="Ex: Lona 4x4 Reforçada")
c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
c4.number_input("Frete (>79)", step=0.01, format="%.2f", key="n_frete")

st.markdown("---")

c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
c5.number_input("Comissão ML (%)", step=0.5, format="%.1f", key="n_taxa")
c6.number_input("Extras (R$)", step=0.01, format="%.2f", key="n_extra")
c7.number_input("Preço ERP (R$)", step=0.01, format="%.2f", key="n_erp")
c8.number_input("Margem ERP (%)", step=1.0, format="%.1f", key="n_merp")
st.markdown('</div>', unsafe_allow_html=True)

# 2. BLOCO HERO (GRADIENTE) DE SUGESTÃO
lucro_alvo_view = st.session_state.n_erp * (st.session_state.n_merp / 100)
preco_sug_view, nome_frete_view = calcular_preco_sugerido_reverso(
    st.session_state.n_cmv + st.session_state.n_extra, 
    lucro_alvo_view, 
    st.session_state.n_taxa, 
    imposto_padrao, 
    st.session_state.n_frete
)

col_hero, col_btn = st.columns([2.5, 1])

with col_hero:
    st.markdown(f"""
    <div class="hero-box">
        <div>
            <div class="hero-label">Meta de Lucro</div>
            <div class="hero-value">R$ {lucro_alvo_view:.2f}</div>
            <div class="hero-sub">{st.session_state.n_merp}% sobre R$ {st.session_state.n_erp}</div>
        </div>
        <div class="hero-arrow">➔</div>
        <div style="text-align: right;">
            <div class="hero-label">Preço Sugerido</div>
            <div class="hero-value">R$ {preco_sug_view:.2f}</div>
            <div class="hero-sub">{nome_frete_view}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.write("") # Espaçamento para alinhar
    st.write("")
    st.button("ADICIONAR À LISTA ✚", type="primary", on_click=adicionar_produto_action, use_container_width=True)

# 3. LISTA DE PRODUTOS
if st.session_state.lista_produtos:
    st.markdown("### 📋 Seus Produtos")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Cabeçalho Discreto
    h_col = st.columns([1, 3, 2, 1])
    h_col[0].caption("CÓDIGO")
    h_col[1].caption("PRODUTO / DETALHES")
    h_col[2].caption("PERFORMANCE")
    h_col[3].caption("AÇÕES")
    
    # Loop de Produtos
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        # Recálculo "Vivo"
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
        
        # Cor da borda baseada no lucro
        status_class = "status-green" if lucro_final > 0 else "status-red"
        
        # Container do Produto (Sem st.container(border=True) padrão, usando CSS)
        st.markdown(f'<div class="product-item-card {status_class}">', unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
        
        with c1:
            st.markdown(f"**{item['MLB']}**")
            
        with c2:
            st.markdown(f"**{item['Produto']}**")
            st.caption(f"Tabela: R$ {item['PrecoBase']:.2f} | Frete: {nome_frete_real}")
            
        with c3:
            css_cor = "text-green" if lucro_final > 0 else "text-red"
            st.markdown(f"""
                <div class="price-tag">
                    Venda: R$ {preco_final_calc:.2f}<br>
                    <span class="{css_cor}">Lucro: R$ {lucro_final:.2f} ({margem_final:.1f}%)</span>
                </div>
            """, unsafe_allow_html=True)
            
        with c4:
            def deletar_item(idx=i): del st.session_state.lista_produtos[idx]
            st.button("🗑️", key=f"del_{item['id']}", on_click=deletar_item)
            
        st.markdown('</div>', unsafe_allow_html=True) # Fecha Card

        # Área de Edição (Expander Nativo, mas limpo)
        with st.expander(f"✏️ Editar / DRE Completa"):
            
            # Edição
            st.caption("AJUSTES RÁPIDOS")
            ec1, ec2, ec3, ec4 = st.columns(4)
            
            def update_field(key_id, field):
                st.session_state.lista_produtos[i][field] = st.session_state[key_id]

            ec1.number_input("Preço Tabela", value=float(item['PrecoBase']), step=0.5, key=f"pb_{item['id']}", on_change=update_field, args=(f"pb_{item['id']}", 'PrecoBase'))
            ec2.number_input("Desconto %", value=float(item['DescontoPct']), step=0.5, key=f"dc_{item['id']}", on_change=update_field, args=(f"dc_{item['id']}", 'DescontoPct'))
            ec3.number_input("Bônus R$", value=float(item['Bonus']), step=0.01, key=f"bn_{item['id']}", on_change=update_field, args=(f"bn_{item['id']}", 'Bonus'))
            ec4.number_input("CMV", value=float(item['CMV']), step=0.01, key=f"cmv_{item['id']}", on_change=update_field, args=(f"cmv_{item['id']}", 'CMV'))

            st.markdown("---")
            
            # DRE
            d1, d2 = st.columns([3, 1])
            d1.markdown("**(+) Preço Tabela**")
            d2.markdown(f"R$ {preco_base_calc:.2f}")
            
            if desc_calc > 0:
                d1, d2 = st.columns([3, 1])
                d1.markdown(f":red[**(-) Desconto ({desc_calc}%)**]")
                d2.markdown(f":red[- R$ {preco_base_calc - preco_final_calc:.2f}]")
            
            st.markdown("---")
            
            custos = [
                (f"Impostos ({imposto_padrao}%)", imposto_val),
                (f"Comissão ({item['TaxaML']}%)", comissao_val),
                (f"Frete ({nome_frete_real})", valor_frete_real),
                ("Custo CMV", item['CMV']),
                ("Extras", item['Extra'])
            ]
            
            for lbl, val in custos:
                d1, d2 = st.columns([3, 1])
                d1.caption(f"(-) {lbl}")
                d2.caption(f"- R$ {val:.2f}")
            
            if item['Bonus'] > 0:
                d1, d2 = st.columns([3, 1])
                d1.markdown(":green[**(+) Bônus / Rebate**]")
                d2.markdown(f":green[+ R$ {item['Bonus']:.2f}]")
            
            st.divider()
            r1, r2 = st.columns([3, 1])
            r1.markdown("#### RESULTADO LÍQUIDO")
            cor_res = ":green" if lucro_final > 0 else ":red"
            r2.markdown(f"#### {cor_res}[R$ {lucro_final:.2f}]")

    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2 = st.columns([1, 1])
    
    # Gerar CSV
    dados_csv = []
    for it in st.session_state.lista_produtos:
        pf = it['PrecoBase'] * (1 - it['DescontoPct']/100)
        _, fr = identificar_faixa_frete(pf)
        if _ == "manual": fr = it['FreteManual']
        luc = pf - (it['CMV'] + it['Extra'] + fr + (pf*(imposto_padrao+it['TaxaML'])/100)) + it['Bonus']
        dados_csv.append({"MLB": it['MLB'], "Produto": it['Produto'], "Preco Final": pf, "Lucro": luc, "Margem %": (luc/pf)*100 if pf else 0})
    
    df_final = pd.DataFrame(dados_csv)
    csv = df_final.to_csv(index=False).encode('utf-8')
    f1.download_button("📥 BAIXAR RELATÓRIO EXCEL", csv, "precificacao_ml_premium.csv", "text/csv", use_container_width=True)
    
    def limpar_tudo(): st.session_state.lista_produtos = []
    f2.button("🗑️ LIMPAR TUDO", on_click=limpar_tudo, use_container_width=True)

else:
    st.info("👋 Bem-vindo! Adicione seu primeiro produto acima para começar.")
