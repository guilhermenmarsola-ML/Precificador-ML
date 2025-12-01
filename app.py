import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Precificador ML - V12 (Live Editor)", layout="wide", page_icon="⚡")

# Função Universal de Reinício
def reiniciar_app():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- CSS PROFISSIONAL ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    
    /* Card do Produto na Lista */
    .product-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px 15px;
        border-left: 5px solid #ccc;
        margin-bottom: 10px;
    }
    .status-ok { border-left-color: #28a745 !important; }
    .status-bad { border-left-color: #dc3545 !important; }
    
    /* DRE Box */
    .dre-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        font-family: monospace;
        font-size: 14px;
        margin-top: 10px;
    }
    
    /* Inputs Compactos na Lista */
    div[data-testid="stNumberInput"] label {
        font-size: 12px;
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

# --- LÓGICA DE SUGESTÃO (REVERSA) ---
def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_ml_pct, imposto_pct, frete_manual):
    custos_fixos_1 = custo_base + frete_manual
    divisor = 1 - ((taxa_ml_pct + imposto_pct) / 100)
    if divisor <= 0: return 0.0, "Erro"
    
    preco_est_1 = (custos_fixos_1 + lucro_alvo_reais) / divisor
    if preco_est_1 >= 79.00: return preco_est_1, "Frete Manual (>79)"
    
    # Tentativas nas faixas
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
st.title("⚡ Precificador ML Pro (Edição em Linha)")
st.markdown("---")

# ==============================================================================
# ÁREA 1: CADASTRO DE NOVO ITEM
# ==============================================================================
with st.expander("📝 Cadastrar Novo Produto", expanded=True):
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    codigo_mlb_input = c1.text_input("SKU / MLB", "MLB-")
    nome_produto_input = c2.text_input("Nome do Produto", "")
    cmv_input = c3.number_input("Custo (CMV)", value=32.57, step=0.01, format="%.2f")
    frete_anuncio_input = c4.number_input("Frete Cheio (>79)", value=18.86, step=0.01, format="%.2f")

    c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
    taxa_ml_input = c5.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
    custo_extra_input = c6.number_input("Extras (R$)", value=0.00, step=0.01, format="%.2f")
    preco_erp_input = c7.number_input("Preço ERP (R$)", value=85.44, step=0.01, format="%.2f")
    margem_erp_input = c8.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f")

    # Botão de Cálculo Prévio
    lucro_alvo_input = preco_erp_input * (margem_erp_input / 100)
    preco_sug, nome_frete_sug = calcular_preco_sugerido_reverso(
        cmv_input + custo_extra_input, lucro_alvo_input, taxa_ml_input, imposto_padrao, frete_anuncio_input
    )
    
    st.info(f"💡 Sugestão para Meta: **R$ {preco_sug:.2f}** ({nome_frete_sug})")
    
    if st.button("⬇️ ADICIONAR À LISTA", type="primary"):
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
                
                # Valores Iniciais de Venda
                "PrecoBase": preco_sug, # Começa com o sugerido
                "DescontoPct": 0.0,
                "Bonus": 0.0,
            }
            st.session_state.lista_produtos.append(novo_item)
            st.success("Adicionado! Edite os detalhes abaixo.")
            time.sleep(0.5)
            reiniciar_app()
        else:
            st.error("Nome obrigatório")

# ==============================================================================
# ÁREA 2: LISTA DE PRODUTOS (COM EDIÇÃO VIVA)
# ==============================================================================
st.markdown("---")
st.subheader(f"📋 Gerenciamento ({len(st.session_state.lista_produtos)} itens)")

if st.session_state.lista_produtos:
    
    # Cabeçalho da Lista
    h1, h2, h3, h4 = st.columns([1, 3, 2, 1])
    h1.caption("CÓDIGO")
    h2.caption("PRODUTO (Clique na seta p/ Editar)")
    h3.caption("RESULTADO FINAL")
    h4.caption("AÇÃO")
    st.divider()

    # Loop pelos itens
    # Precisamos usar enumerate para gerar keys únicas para os inputs
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        # --- CÁLCULO EM TEMPO REAL (LIVE) ---
        # 1. Recupera valores (Podem ter sido editados no input abaixo)
        preco_base_calc = item['PrecoBase']
        desc_calc = item['DescontoPct']
        preco_final_calc = preco_base_calc * (1 - (desc_calc / 100))
        
        # 2. Identifica Frete
        nome_frete_real, valor_frete_real = identificar_faixa_frete(preco_final_calc)
        if nome_frete_real == "manual": valor_frete_real = item['FreteManual']
        
        # 3. DRE
        imposto_val = preco_final_calc * (imposto_padrao / 100)
        comissao_val = preco_final_calc * (item['TaxaML'] / 100)
        custos_totais = item['CMV'] + item['Extra'] + valor_frete_real + imposto_val + comissao_val
        lucro_final = preco_final_calc - custos_totais + item['Bonus']
        margem_final = (lucro_final / preco_final_calc * 100) if preco_final_calc > 0 else 0
        
        # Define cor da borda
        css_class = "status-ok" if lucro_final > 0 else "status-bad"
        
        # --- RENDERIZAÇÃO DA LINHA ---
        col_resumo = st.container()
        
        # Linha Resumo (Visível Sempre)
        c1, c2, c3, c4 = col_resumo.columns([1, 3, 2, 1])
        c1.write(f"**{item['MLB']}**")
        c2.write(item['Produto'])
        
        cor_txt = ":green" if lucro_final > 0 else ":red"
        c3.markdown(f"Venda: **R$ {preco_final_calc:.2f}** | Lucro: {cor_txt}[**R$ {lucro_final:.2f}**]")
        
        if c4.button("🗑️", key=f"del_{item['id']}"):
            st.session_state.lista_produtos.remove(item)
            reiniciar_app()

        # --- ÁREA DE EDIÇÃO E DETALHES (EXPANDER) ---
        with st.expander(f"✏️ Editar / Ver Detalhes - {item['Produto']}"):
            
            st.markdown("#### 🛠️ Editar Valores")
            
            # Inputs de Edição (Atualizam direto o dicionário na sessão)
            ec1, ec2, ec3, ec4 = st.columns(4)
            
            # Aqui está a mágica: Os inputs atualizam o `item` direto
            novo_preco_base = ec1.number_input("Preço Tabela (R$)", value=float(item['PrecoBase']), step=0.5, key=f"pbase_{item['id']}")
            novo_desc = ec2.number_input("Desconto (%)", value=float(item['DescontoPct']), step=0.5, key=f"desc_{item['id']}")
            novo_bonus = ec3.number_input("Rebate / Bônus (R$)", value=float(item['Bonus']), step=0.01, key=f"bonus_{item['id']}")
            novo_cmv = ec4.number_input("CMV (Custo)", value=float(item['CMV']), step=0.5, key=f"cmv_{item['id']}")
            
            # Atualiza o estado se houver mudança
            if (novo_preco_base != item['PrecoBase'] or 
                novo_desc != item['DescontoPct'] or 
                novo_bonus != item['Bonus'] or 
                novo_cmv != item['CMV']):
                
                item['PrecoBase'] = novo_preco_base
                item['DescontoPct'] = novo_desc
                item['Bonus'] = novo_bonus
                item['CMV'] = novo_cmv
                st.rerun() # Recarrega para atualizar os cálculos acima

            st.divider()
            
            # --- DRE VISUAL (NATIVA) ---
            st.markdown("#### 📄 DRE (Resultado Financeiro)")
            
            # Receita
            d1, d2 = st.columns([3, 1])
            d1.write(f"(+) Preço Tabela")
            d2.write(f"R$ {preco_base_calc:.2f}")
            
            if desc_calc > 0:
                d1, d2 = st.columns([3, 1])
                d1.markdown(f":red[(-) Desconto ({desc_calc}%) ]")
                d2.markdown(f":red[- R$ {preco_base_calc - preco_final_calc:.2f}]")
            
            st.markdown("---") # Linha fina
            
            # Custos
            custos_list = [
                (f"Impostos ({imposto_padrao}%)", imposto_val),
                (f"Comissão ML ({item['TaxaML']}%)", comissao_val),
                (f"Frete ({nome_frete_real})", valor_frete_real),
                ("Custo (CMV)", item['CMV']),
                ("Extras", item['Extra'])
            ]
            
            for nome, valor in custos_list:
                d1, d2 = st.columns([3, 1])
                d1.write(f"(-) {nome}")
                d2.markdown(f":red[- R$ {valor:.2f}]")

            if item['Bonus'] > 0:
                d1, d2 = st.columns([3, 1])
                d1.markdown(f":blue[(+) Bônus / Rebate]")
                d2.markdown(f":blue[+ R$ {item['Bonus']:.2f}]")

            st.divider() # Linha grossa
            
            # Resultado Final do Item
            rf1, rf2 = st.columns([3, 1])
            rf1.markdown("### LUCRO LÍQUIDO")
            cor_final = ":green" if lucro_final > 0 else ":red"
            rf2.markdown(f"### {cor_final}[R$ {lucro_final:.2f}]")
            rf2.caption(f"Margem: {margem_final:.1f}%")

        st.divider()

    # Botões Finais
    col_dl, col_cl = st.columns([1, 1])
    
    # Gera DataFrame atualizado para Excel
    # Precisamos recalcular o DF final baseado nos dados vivos
    dados_export = []
    for item in st.session_state.lista_produtos:
        # Recalcula para garantir que o CSV saia com os dados editados
        pb = item['PrecoBase']
        pf = pb * (1 - item['DescontoPct']/100)
        _, fr = identificar_faixa_frete(pf)
        if _ == "manual": fr = item['FreteManual']
        luc = pf - (item['CMV'] + item['Extra'] + fr + (pf*(imposto_padrao+item['TaxaML'])/100)) + item['Bonus']
        
        dados_export.append({
            "MLB": item['MLB'],
            "Produto": item['Produto'],
            "Preco Final": pf,
            "Lucro": luc,
            "Margem": (luc/pf) if pf>0 else 0
        })
        
    df_exp = pd.DataFrame(dados_export)
    csv = df_exp.to_csv(index=False).encode('utf-8')
    
    col_dl.download_button("📥 Baixar Planilha Atualizada", csv, "precificacao_v12.csv", "text/csv")
    
    if col_cl.button("🗑️ Limpar Lista Completa"):
        st.session_state.lista_produtos = []
        reiniciar_app()

else:
    st.info("Lista vazia. Cadastre o primeiro produto acima.")
