import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Precificador ML - V17 Final", layout="wide", page_icon="⚡")

# --- FUNÇÃO DE REINÍCIO ---
def reiniciar_app():
    time.sleep(0.1)
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# --- INICIALIZAÇÃO DE ESTADO ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# Função para inicializar variáveis de input se não existirem
def init_var(key, default_value):
    if key not in st.session_state:
        st.session_state[key] = default_value

# Inicializa as variáveis dos campos (Inputs)
init_var('n_mlb', 'MLB-')
init_var('n_nome', '')
init_var('n_cmv', 32.57)
init_var('n_frete', 18.86)
init_var('n_extra', 0.00)
# Taxas e Metas mantêm o estado (não limpamos a cada produto)
init_var('n_taxa', 16.5)
init_var('n_erp', 85.44)
init_var('n_merp', 20.0)

# --- CSS E ESTILO ---
st.markdown("""
<style>
    div[data-testid="stNumberInput"] label { font-size: 13px; color: #444; }
    .lucro-pos { color: #28a745; font-weight: bold; }
    .lucro-neg { color: #dc3545; font-weight: bold; }
    
    /* Caixa de Sugestão Estilizada */
    .suggestion-container {
        background-color: #f0f7ff;
        border: 1px solid #cce5ff;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .sug-label { font-size: 12px; color: #004085; font-weight: bold; letter-spacing: 1px; }
    .sug-val { font-size: 26px; color: #0056b3; font-weight: 800; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurações")
    with st.expander("📊 Taxas Globais", expanded=True):
        imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5, format="%.2f")
    
    with st.expander("🚚 Tabela Frete ML (<79)", expanded=True):
        taxa_12_29 = st.number_input("R$ 12,50 - 29,00", value=6.25)
        taxa_29_50 = st.number_input("R$ 29,00 - 50,00", value=6.50)
        taxa_50_79 = st.number_input("R$ 50,00 - 79,00", value=6.75)
        taxa_minima = st.number_input("Abaixo de R$ 12,50", value=3.25)

# --- LÓGICA DE NEGÓCIO ---
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

# --- CABEÇALHO ---
st.title("⚡ Precificador ML Pro")

# ==============================================================================
# ÁREA 1: CADASTRO DO PRODUTO
# ==============================================================================
with st.container(border=True):
    st.subheader("1. Dados do Produto")
    
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    # Os inputs estão ligados ao session_state pelas chaves (key)
    codigo_mlb_input = c1.text_input("SKU / MLB", key="n_mlb")
    nome_produto_input = c2.text_input("Nome do Produto", key="n_nome")
    cmv_input = c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
    frete_anuncio_input = c4.number_input("Frete Cheio (>79)", step=0.01, format="%.2f", key="n_frete")

    st.divider() 
    
    c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
    taxa_ml_input = c5.number_input("Comissão ML (%)", step=0.5, format="%.1f", key="n_taxa")
    custo_extra_input = c6.number_input("Extras (R$)", step=0.01, format="%.2f", key="n_extra")
    preco_erp_input = c7.number_input("Preço ERP (R$)", step=0.01, format="%.2f", key="n_erp")
    margem_erp_input = c8.number_input("Margem ERP (%)", step=1.0, format="%.1f", key="n_merp")

# ==============================================================================
# ÁREA 2: SUGESTÃO E ADIÇÃO
# ==============================================================================
# Cálculo da Sugestão
lucro_alvo_input = preco_erp_input * (margem_erp_input / 100)
preco_sug, nome_frete_sug = calcular_preco_sugerido_reverso(
    cmv_input + custo_extra_input, lucro_alvo_input, taxa_ml_input, imposto_padrao, frete_anuncio_input
)

col_painel, col_botao = st.columns([2, 1])

with col_painel:
    # Painel Visual de Sugestão (Nativo + HTML seguro)
    st.markdown(f"""
    <div class="suggestion-container">
        <div style="display: flex; justify-content: space-around; align-items: center;">
            <div>
                <div class="sug-label">META LUCRO (ERP)</div>
                <div class="sug-val">R$ {lucro_alvo_input:.2f}</div>
            </div>
            <div style="font-size: 24px; color: #90caf9;">➜</div>
            <div>
                <div class="sug-label">PREÇO SUGERIDO</div>
                <div class="sug-val">R$ {preco_sug:.2f}</div>
                <div style="font-size: 11px; color: #666;">({nome_frete_sug})</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_botao:
    st.write("") # Espaçamento para alinhar verticalmente
    st.write("") 
    
    # --- LÓGICA DO BOTÃO ADICIONAR (CORRIGIDA) ---
    if st.button("⬇️ ADICIONAR À LISTA", type="primary", use_container_width=True):
        if nome_produto_input:
            # 1. SALVAR O PRODUTO NA LISTA
            novo_id = int(time.time() * 1000)
            novo_item = {
                "id": novo_id,
                "MLB": codigo_mlb_input,
                "Produto": nome_produto_input,
                "CMV": cmv_input,
                "FreteManual": frete_anuncio_input,
                "TaxaML": taxa_ml_input,
                "Extra": custo_extra_input,
                "PrecoERP": preco_erp_input,
                "MargemERP": margem_erp_input,
                "PrecoBase": preco_sug, 
                "DescontoPct": 0.0,
                "Bonus": 0.0,
            }
            st.session_state.lista_produtos.append(novo_item)
            st.success("Adicionado com sucesso!")
            
            # 2. LIMPAR OS CAMPOS PARA O PRÓXIMO (Atualiza o session_state)
            st.session_state.n_mlb = "MLB-"
            st.session_state.n_nome = ""
            st.session_state.n_cmv = 0.00
            st.session_state.n_extra = 0.00
            # Obs: Mantemos n_erp, n_merp, n_taxa pois geralmente repetem
            
            # 3. RECARREGAR A PÁGINA
            reiniciar_app()
        else:
            st.error("Preencha o Nome do Produto.")

# ==============================================================================
# ÁREA 3: LISTA DE GESTÃO
# ==============================================================================
st.markdown("### 📋 Produtos Precificados")

if st.session_state.lista_produtos:
    
    # Cabeçalho da Tabela
    cols = st.columns([1, 3, 2, 1])
    cols[0].caption("CÓDIGO")
    cols[1].caption("PRODUTO")
    cols[2].caption("LUCRO / MARGEM")
    cols[3].caption("AÇÕES")
    
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        with st.container(border=True):
            
            # Recálculos Vivos
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
            
            # Linha Principal
            c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
            c1.write(f"**{item['MLB']}**")
            c2.write(item['Produto'])
            
            cor_txt = ":green" if lucro_final > 0 else ":red"
            c3.markdown(f"{cor_txt}[**R$ {lucro_final:.2f}**] ({margem_final:.1f}%)")
                
            if c4.button("🗑️", key=f"del_{item['id']}"):
                st.session_state.lista_produtos.remove(item)
                reiniciar_app()

            # Detalhes e Edição
            with st.expander(f"✏️ Editar / DRE - {item['Produto']}"):
                
                st.caption("AJUSTES DE VENDA")
                ec1, ec2, ec3 = st.columns(3)
                
                novo_preco = ec1.number_input("Preço Tabela (DE)", value=float(item['PrecoBase']), step=0.5, key=f"pb_{item['id']}")
                novo_desc = ec2.number_input("Desconto (%)", value=float(item['DescontoPct']), step=0.5, key=f"dc_{item['id']}")
                novo_bonus = ec3.number_input("Rebate / Bônus (R$)", value=float(item['Bonus']), step=0.01, key=f"bn_{item['id']}")
                
                if (novo_preco != item['PrecoBase'] or novo_desc != item['DescontoPct'] or novo_bonus != item['Bonus']):
                    item['PrecoBase'] = novo_preco
                    item['DescontoPct'] = novo_desc
                    item['Bonus'] = novo_bonus
                    reiniciar_app()

                st.divider()
                
                # DRE Visual
                st.caption("DEMONSTRATIVO FINANCEIRO")
                d1, d2 = st.columns([3, 1])
                d1.write("(+) Preço Tabela")
                d2.write(f"R$ {preco_base_calc:.2f}")
                
                if desc_calc > 0:
                    d1, d2 = st.columns([3, 1])
                    d1.markdown(f":red[(-) Desconto ({desc_calc}%) ]")
                    d2.markdown(f":red[- R$ {preco_base_calc - preco_final_calc:.2f}]")
                
                st.markdown("---") 
                r1, r2 = st.columns([3, 1])
                r1.markdown("**:blue[(=) PREÇO VENDA (POR)]**")
                r2.markdown(f"**:blue[R$ {preco_final_calc:.2f}]**")
                
                custos = [
                    (f"Impostos ({imposto_padrao}%)", imposto_val),
                    (f"Comissão ({item['TaxaML']}%)", comissao_val),
                    (f"Frete ({nome_frete_real})", valor_frete_real),
                    ("Custo CMV", item['CMV']),
                    ("Extras", item['Extra'])
                ]
                
                for lbl, val in custos:
                    r1, r2 = st.columns([3, 1])
                    r1.caption(f"(-) {lbl}")
                    r2.caption(f"- R$ {val:.2f}")
                
                if item['Bonus'] > 0:
                    r1, r2 = st.columns([3, 1])
                    r1.markdown(":green[(+) Bônus / Rebate]")
                    r2.markdown(f":green[+ R$ {item['Bonus']:.2f}]")
                
                st.divider()
                
                rf1, rf2 = st.columns([3, 1])
                rf1.markdown("#### RESULTADO")
                cor_res = ":green" if lucro_final > 0 else ":red"
                rf2.markdown(f"#### {cor_res}[R$ {lucro_final:.2f}]")

    # Download
    st.markdown("---")
    col_csv, col_clr = st.columns([1, 1])
    
    dados_csv = []
    for it in st.session_state.lista_produtos:
        pf = it['PrecoBase'] * (1 - it['DescontoPct']/100)
        _, fr = identificar_faixa_frete(pf)
        if _ == "manual": fr = it['FreteManual']
        luc = pf - (it['CMV'] + it['Extra'] + fr + (pf*(imposto_padrao+it['TaxaML'])/100)) + it['Bonus']
        dados_csv.append({
            "MLB": it['MLB'], 
            "Produto": it['Produto'], 
            "Preco Final": pf, 
            "Lucro": luc, 
            "Margem %": (luc/pf)*100 if pf else 0
        })
        
    df_final = pd.DataFrame(dados_csv)
    csv = df_final.to_csv(index=False).encode('utf-8')
    
    col_csv.download_button("📥 Baixar Excel Completo", csv, "precificacao_ml.csv", "text/csv")
    if col_clr.button("🗑️ Limpar Lista"):
        st.session_state.lista_produtos = []
        reiniciar_app()

else:
    st.info("Lista vazia. Adicione produtos acima.")
