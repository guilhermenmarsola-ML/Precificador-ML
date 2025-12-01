import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gerenciador ML - V11 (Gestão Total)", layout="wide", page_icon="⚡")

# Função de Reinício Universal
def reiniciar_app():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# Inicialização de Estado (Memória)
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- FUNÇÃO PARA CARREGAR DADOS NO FORMULÁRIO (EDITAR) ---
def carregar_para_edicao(item):
    # Joga os valores do item para as chaves dos widgets
    st.session_state['w_mlb'] = item['MLB']
    st.session_state['w_nome'] = item['Produto']
    st.session_state['w_cmv'] = item['CMV']
    st.session_state['w_frete_anuncio'] = 18.86 # Valor padrão ou recuperar se tivesse salvo o manual específico
    st.session_state['w_taxa_ml'] = item['ComissaoPct']
    st.session_state['w_extra'] = item['Extra']
    st.session_state['w_preco_base'] = item['PrecoBase']
    st.session_state['w_desc'] = item['DescontoPct']
    st.session_state['w_bonus'] = item['Bonus']
    
    # Remove o item antigo da lista para não duplicar
    st.session_state.lista_produtos.remove(item)
    st.toast(f"Editando: {item['Produto']}. Dados carregados no topo!", icon="✏️")

# --- FUNÇÃO PARA REMOVER ---
def remover_item(item):
    st.session_state.lista_produtos.remove(item)
    st.toast("Item removido com sucesso!", icon="🗑️")

# --- CSS PROFISSIONAL ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; color: #2c3e50; }
    
    .custom-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        margin-bottom: 20px;
    }
    
    /* Botão Principal */
    div.stButton > button:first-child {
        font-weight: bold;
        border-radius: 8px;
    }
    
    /* Estilo específico para botões de ação na lista (pequenos) */
    div[data-testid="column"] button {
        padding: 0px 10px;
        font-size: 12px;
        min-height: 35px;
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

# --- FUNÇÕES LÓGICAS ---
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
    if preco_est_1 >= 79.00: return preco_est_1, "Frete Manual (>79)"
    
    custos_fixos_2 = custo_base + taxa_50_79
    preco_est_2 = (custos_fixos_2 + lucro_alvo_reais) / divisor
    if 50.00 <= preco_est_2 < 79.00: return preco_est_2, "Tab. 50-79"
        
    custos_fixos_3 = custo_base + taxa_29_50
    preco_est_3 = (custos_fixos_3 + lucro_alvo_reais) / divisor
    if 29.00 <= preco_est_3 < 50.00: return preco_est_3, "Tab. 29-50"
        
    custos_fixos_4 = custo_base + taxa_12_29
    preco_est_4 = (custos_fixos_4 + lucro_alvo_reais) / divisor
    if 12.50 <= preco_est_4 < 29.00: return preco_est_4, "Tab. 12-29"
        
    return preco_est_1, "Frete Manual (Fallback)"

st.title("⚡ Precificador Mercado Livre Pro")
st.markdown("---")

# --- BLOCO 1: DADOS E CUSTOS ---
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.subheader("1. Dados do Produto e Custos")
c1, c2, c3, c4 = st.columns([1, 2, 1, 1])

# USANDO KEYS PARA PERMITIR A EDICAO
with c1: codigo_mlb = st.text_input("SKU / MLB", key="w_mlb")
with c2: nome_produto = st.text_input("Nome do Produto", key="w_nome")
with c3: cmv = st.number_input("Custo (CMV)", step=0.01, format="%.2f", key="w_cmv")
with c4: frete_anuncio = st.number_input("Frete Cheio (>79)", value=18.86, step=0.01, format="%.2f", key="w_frete_anuncio")

c_taxa, c_extra = st.columns(2)
with c_taxa: taxa_ml = st.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f", key="w_taxa_ml")
with c_extra: custo_extra = st.number_input("Embalagem / Extra (R$)", step=0.01, format="%.2f", key="w_extra")
st.markdown('</div>', unsafe_allow_html=True)

# --- BLOCO 2: ESTRATÉGIA ---
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.subheader("2. Definição de Meta (ERP)")
col_meta, col_sugestao = st.columns([1, 1])

with col_meta:
    mc1, mc2 = st.columns(2)
    preco_erp = mc1.number_input("Preço ERP (R$)", value=85.44, step=0.01, format="%.2f", key="w_preco_erp")
    margem_erp = mc2.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f", key="w_margem_erp")
    lucro_alvo = preco_erp * (margem_erp / 100)
    st.markdown(f"🎯 Meta de Lucro: :green[**R$ {lucro_alvo:.2f}**]")

with col_sugestao:
    preco_ideal, nome_frete_ideal = calcular_preco_sugerido_reverso(
        custo_base=(cmv + custo_extra),
        lucro_alvo_reais=lucro_alvo,
        taxa_ml_pct=taxa_ml,
        imposto_pct=imposto_padrao,
        frete_manual=frete_anuncio
    )
    st.info(f"💡 **Preço Sugerido:**\n# **R$ {preco_ideal:.2f}**\n*({nome_frete_ideal})*")
st.markdown('</div>', unsafe_allow_html=True)

# --- BLOCO 3: AJUSTE FINO ---
st.markdown('<div class="custom-card" style="background-color: #f0f8ff; border: 1px solid #b3d7ff;">', unsafe_allow_html=True)
st.subheader("3. Decisão Final e Promoções")
col_decisao, col_promo = st.columns([1, 1.5])

with col_decisao:
    # Se não tiver valor na sessão (primeira vez), usa o ideal
    if 'w_preco_base' not in st.session_state:
        st.session_state['w_preco_base'] = float(round(preco_ideal, 2))
        
    preco_base_decisao = st.number_input("Preço de Tabela (DE:)", step=0.01, format="%.2f", key="w_preco_base")

with col_promo:
    pc1, pc2 = st.columns(2)
    desconto_pct = pc1.number_input("Desconto (%)", step=0.5, format="%.1f", key="w_desc")
    bonus_ml = pc2.number_input("Rebate / Bônus (R$)", step=0.01, format="%.2f", key="w_bonus")
    
    preco_final = preco_base_decisao * (1 - (desconto_pct / 100))
    st.markdown(f"🛒 Preço Final de Venda (POR): **R$ {preco_final:.2f}**")
st.markdown('</div>', unsafe_allow_html=True)

# --- CÁLCULO FINAL ---
nome_frete_real, valor_frete_real = identificar_faixa_frete(preco_final)
if nome_frete_real == "manual": valor_frete_real = frete_anuncio

imposto_val = preco_final * (imposto_padrao / 100)
comissao_val = preco_final * (taxa_ml / 100)
custos_totais = cmv + custo_extra + valor_frete_real + imposto_val + comissao_val
lucro_final = preco_final - custos_totais + bonus_ml
margem_final = (lucro_final / preco_final * 100) if preco_final > 0 else 0

st.subheader("📊 Resultado da Simulação")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Frete Aplicado", f"R$ {valor_frete_real:.2f}", nome_frete_real)
k2.metric("Comissão + Imposto", f"R$ {(comissao_val + imposto_val):.2f}")
k3.metric("Bônus", f"R$ {bonus_ml:.2f}")
k4.metric("Lucro Líquido", f"R$ {lucro_final:.2f}", f"Dif Meta: R$ {lucro_final - lucro_alvo:.2f}")

# --- BOTÃO ADICIONAR ---
st.markdown("---")
col_add, _ = st.columns([1, 2])
if col_add.button("➕ ADICIONAR / ATUALIZAR LISTA"):
    if nome_produto:
        novo_id = int(time.time() * 1000)
        novo_item = {
            "id": novo_id,
            "MLB": codigo_mlb,
            "Produto": nome_produto,
            "PrecoBase": preco_base_decisao,
            "DescontoPct": desconto_pct,
            "PrecoFinal": preco_final,
            "ImpostoVal": imposto_val,
            "ImpostoPct": imposto_padrao,
            "ComissaoVal": comissao_val,
            "ComissaoPct": taxa_ml,
            "FreteVal": valor_frete_real,
            "FreteNome": nome_frete_real,
            "CMV": cmv,
            "Extra": custo_extra,
            "Bonus": bonus_ml,
            "Lucro": lucro_final,
            "Margem": margem_final
        }
        st.session_state.lista_produtos.append(novo_item)
        st.success("Salvo com sucesso!")
        time.sleep(0.5)
        reiniciar_app() # Recarrega para limpar o form ou mostrar na lista
    else:
        st.error("Nome do produto é obrigatório.")

# --- LISTA DE PRODUTOS ---
if st.session_state.lista_produtos:
    st.markdown("### 📋 Produtos Salvos")
    
    # Cabeçalho Fixo
    with st.container():
        h1, h2, h3, h4, h5 = st.columns([1, 3, 2, 2, 1.5])
        h1.caption("CÓDIGO")
        h2.caption("PRODUTO")
        h3.caption("PREÇO FINAL")
        h4.caption("LUCRO")
        h5.caption("AÇÕES")
        st.divider()

    # Iterar sobre a lista (Cópia invertida para mostrar recentes primeiro)
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 1.5])
        
        c1.write(f"**{item['MLB']}**")
        c2.write(item['Produto'])
        c3.write(f"R$ {item['PrecoFinal']:.2f}")
        
        if item['Lucro'] > 0:
            c4.markdown(f":green[**R$ {item['Lucro']:.2f}**] ({item['Margem']:.1f}%)")
        else:
            c4.markdown(f":red[**R$ {item['Lucro']:.2f}**] ({item['Margem']:.1f}%)")

        # --- BOTÕES DE AÇÃO ---
        btn_col1, btn_col2 = c5.columns(2)
        
        # Botão EDITAR
        if btn_col1.button("✏️", key=f"edit_{item['id']}", help="Editar este item"):
            carregar_para_edicao(item)
            reiniciar_app()
            
        # Botão EXCLUIR
        if btn_col2.button("🗑️", key=f"del_{item['id']}", help="Excluir este item"):
            remover_item(item)
            reiniciar_app()

        # DRE Expansível
        with st.expander("📄 DRE Detalhada"):
            d1, d2 = st.columns([3, 1])
            d1.markdown("Preço Tabela")
            d2.markdown(f"R$ {item['PrecoBase']:.2f}")
            
            if item['DescontoPct'] > 0:
                d1, d2 = st.columns([3, 1])
                d1.markdown(f":red[(-) Desconto ({item['DescontoPct']}%) ]")
                d2.markdown(f":red[- R$ {item['PrecoBase'] - item['PrecoFinal']:.2f}]")
            
            st.markdown("---")
            d1, d2 = st.columns([3, 1])
            d1.markdown("**(=) RECEITA BRUTA**")
            d2.markdown(f"**R$ {item['PrecoFinal']:.2f}**")
            st.markdown("---")
            
            custos_list = [
                (f"Impostos ({item['ImpostoPct']}%)", item['ImpostoVal']),
                (f"Comissão ML ({item['ComissaoPct']}%)", item['ComissaoVal']),
                (f"Frete ({item['FreteNome']})", item['FreteVal']),
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

            st.divider()
            d1, d2 = st.columns([3, 1])
            d1.markdown("#### RESULTADO FINAL")
            cor_final = ":green" if item['Lucro'] > 0 else ":red"
            d2.markdown(f"#### {cor_final}[R$ {item['Lucro']:.2f}]")
            
        st.divider()

    # Exportação
    col_dw, col_clr = st.columns([1, 1])
    df_exp = pd.DataFrame(st.session_state.lista_produtos)
    csv = df_exp.to_csv(index=False).encode('utf-8')
    col_dw.download_button("📥 Baixar Planilha Excel", csv, "precificacao.csv", "text/csv")
    
    if col_clr.button("🗑️ Limpar Tudo"):
        st.session_state.lista_produtos = []
        reiniciar_app()

else:
    st.info("Lista vazia.")
