import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Precificador ML - V15 Gold", layout="wide", page_icon="⚡")

# Função Universal de Reinício
def reiniciar_app():
    time.sleep(0.1)
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- CSS ---
st.markdown("""
<style>
    /* Ajuste para inputs ficarem compactos na lista */
    div[data-testid="stNumberInput"] label { font-size: 13px; }
    
    /* Cores de Lucro */
    .lucro-pos { color: #28a745; font-weight: bold; }
    .lucro-neg { color: #dc3545; font-weight: bold; }
    
    /* Estilo do Card */
    .st-emotion-cache-1r6slb0 {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        background-color: white;
    }
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

# --- LÓGICA DE FRETE ---
def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", taxa_50_79
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", taxa_29_50
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", taxa_12_29
    else: return "Tab. Mínima", taxa_minima

# --- LÓGICA DE SUGESTÃO ---
def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_ml_pct, imposto_pct, frete_manual):
    custos_fixos_1 = custo_base + frete_manual
    divisor = 1 - ((taxa_ml_pct + imposto_pct) / 100)
    if divisor <= 0: return 0.0, "Erro Taxas > 100%"
    
    preco_est_1 = (custos_fixos_1 + lucro_alvo_reais) / divisor
    if preco_est_1 >= 79.00: return preco_est_1, "Frete Manual (>79)"
    
    for taxa, nome, p_min, p_max in [
        (taxa_50_79, "Tab. 50-79", 50, 79),
        (taxa_29_50, "Tab. 29-50", 29, 50),
        (taxa_12_29, "Tab. 12-29", 12.5, 29)
    ]:
        custos = custo_base + taxa
        preco = (custos + lucro_alvo_reais) / divisor
        if p_min <= preco < p_max: return preco, nome
        
    return preco_est_1, "Frete Manual (Fallback)"

# --- CABEÇALHO ---
st.title("⚡ Precificador ML Pro")

# ==============================================================================
# ÁREA 1: CARD DE CADASTRO (COM KEYS PARA LIMPEZA)
# ==============================================================================
with st.container(border=True):
    st.subheader("1. Novo Produto")
    
    # Definindo valores iniciais caso não existam no estado
    if 'n_mlb' not in st.session_state: st.session_state.n_mlb = "MLB-"
    if 'n_nome' not in st.session_state: st.session_state.n_nome = ""
    if 'n_cmv' not in st.session_state: st.session_state.n_cmv = 32.57
    if 'n_frete' not in st.session_state: st.session_state.n_frete = 18.86
    if 'n_taxa' not in st.session_state: st.session_state.n_taxa = 16.5
    if 'n_extra' not in st.session_state: st.session_state.n_extra = 0.0
    if 'n_erp' not in st.session_state: st.session_state.n_erp = 85.44
    if 'n_merp' not in st.session_state: st.session_state.n_merp = 20.0

    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    # Usando key= para vincular ao session_state
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
with st.container(border=True):
    col_sug, col_add = st.columns([3, 1])
    
    with col_sug:
        lucro_alvo_input = preco_erp_input * (margem_erp_input / 100)
        preco_sug, nome_frete_sug = calcular_preco_sugerido_reverso(
            cmv_input + custo_extra_input, lucro_alvo_input, taxa_ml_input, imposto_padrao, frete_anuncio_input
        )
        st.info(f"🎯 Meta: Lucrar **R$ {lucro_alvo_input:.2f}**. Sugestão de Venda: **R$ {preco_sug:.2f}** ({nome_frete_sug})")

    with col_add:
        st.write("") 
        if st.button("⬇️ ADICIONAR À LISTA", type="primary", use_container_width=True):
            if nome_produto_input:
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
                st.success("Adicionado!")
                
                # --- LIMPEZA DOS CAMPOS ---
                st.session_state.n_mlb = "MLB-"
                st.session_state.n_nome = ""
                # Mantivemos as taxas padrão, mas zeramos os valores específicos
                # Se quiser zerar o CMV também, mude para 0.0
                st.session_state.n_cmv = 32.57 
                st.session_state.n_erp = 85.44
                #st.session_state.n_extra = 0.0 (Já está no padrão)
                
                reiniciar_app()
            else:
                st.error("Nome obrigatório")

# ==============================================================================
# ÁREA 3: LISTA DE GESTÃO
# ==============================================================================
st.markdown("### 📋 Gerenciamento de Preços")

if st.session_state.lista_produtos:
    
    cols = st.columns([1, 3, 2, 1])
    cols[0].caption("CÓDIGO")
    cols[1].caption("PRODUTO")
    cols[2].caption("LUCRO / MARGEM")
    cols[3].caption("AÇÕES")
    
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        with st.container(border=True):
            
            # --- CÁLCULOS VIVOS ---
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
            
            # --- LINHA PRINCIPAL ---
            c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
            c1.write(f"**{item['MLB']}**")
            c2.write(item['Produto'])
            
            cor_txt = ":green" if lucro_final > 0 else ":red"
            c3.markdown(f"{cor_txt}[**R$ {lucro_final:.2f}**] ({margem_final:.1f}%)")
                
            if c4.button("🗑️", key=f"del_{item['id']}"):
                st.session_state.lista_produtos.remove(item)
                reiniciar_app()

            # --- EXPANDER ---
            with st.expander(f"✏️ Editar Precificação - {item['Produto']}"):
                
                st.markdown("##### 1. Ajuste de Preço e Promoção")
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
                
                st.markdown("##### 2. Demonstrativo Financeiro (DRE)")
                d1, d2 = st.columns([3, 1])
                d1.write("(+) Preço Tabela")
                d2.write(f"R$ {preco_base_calc:.2f}")
                
                if desc_calc > 0:
                    d1, d2 = st.columns([3, 1])
                    d1.markdown(f":red[(-) Desconto ({desc_calc}%) ]")
                    d2.markdown(f":red[- R$ {preco_base_calc - preco_final_calc:.2f}]")
                
                st.markdown("---") 
                
                d1, d2 = st.columns([3, 1])
                d1.markdown("**:blue[(=) PREÇO VENDA (POR)]**")
                d2.markdown(f"**:blue[R$ {preco_final_calc:.2f}]**")
                
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
                    d1.markdown(":green[(+) Bônus / Rebate]")
                    d2.markdown(f":green[+ R$ {item['Bonus']:.2f}]")
                
                st.divider()
                
                rf1, rf2 = st.columns([3, 1])
                rf1.markdown("#### RESULTADO")
                cor_res = ":green" if lucro_final > 0 else ":red"
                rf2.markdown(f"#### {cor_res}[R$ {lucro_final:.2f}]")
                rf2.caption(f"Margem Líquida: {margem_final:.1f}%")

    # Footer
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
