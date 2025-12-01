import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Precificador ML - V16 Stable", layout="wide", page_icon="⚡")

# --- GERENCIAMENTO DE ESTADO ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# Inicializa as chaves dos inputs se não existirem
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

init_state('n_mlb', 'MLB-')
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
# Mantemos taxas e ERP persistentes para agilizar digitação em lote

# --- FUNÇÃO DE LIMPEZA (CALLBACK) ---
# Esta função roda APENAS quando clica no botão adicionar
def limpar_campos_produto():
    st.session_state.n_mlb = "MLB-"
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00 # Zera o custo para o próximo
    st.session_state.n_extra = 0.00
    # Nota: Não zeramos taxas/margens pois geralmente são repetitivas

# --- CSS PROFISSIONAL ---
st.markdown("""
<style>
    /* Ajuste de Inputs */
    div[data-testid="stNumberInput"] label { font-size: 13px; color: #555; }
    
    /* Painel de Sugestão (Caixa Azul) */
    .suggestion-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #90caf9;
        color: #0d47a1;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .sug-title { font-size: 14px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; color: #1565c0; }
    .sug-value { font-size: 28px; font-weight: 800; color: #0d47a1; margin: 5px 0; }
    .sug-sub { font-size: 13px; color: #1e88e5; }
    
    /* Cores de Resultado */
    .text-success { color: #28a745 !important; font-weight: bold; }
    .text-danger { color: #dc3545 !important; font-weight: bold; }
    
    /* Botões */
    div.stButton > button[kind="primary"] {
        background-color: #2962ff;
        border: none;
        height: 50px;
        font-size: 16px;
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
    
    # Loop de verificação de faixas
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
# ÁREA 1: FORMULÁRIO DE CADASTRO
# ==============================================================================
with st.container(border=True):
    st.subheader("1. Dados do Produto")
    
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    codigo_mlb_input = c1.text_input("SKU / MLB", key="n_mlb")
    nome_produto_input = c2.text_input("Nome do Produto", key="n_nome")
    cmv_input = c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
    frete_anuncio_input = c4.number_input("Frete Cheio (>79)", value=18.86, step=0.01, format="%.2f", key="n_frete")

    st.divider() 
    
    c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
    taxa_ml_input = c5.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f", key="n_taxa")
    custo_extra_input = c6.number_input("Extras (R$)", step=0.01, format="%.2f", key="n_extra")
    preco_erp_input = c7.number_input("Preço ERP (R$)", value=85.44, step=0.01, format="%.2f", key="n_erp")
    margem_erp_input = c8.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f", key="n_merp")

# ==============================================================================
# ÁREA 2: SUGESTÃO INTELIGENTE (CAIXA AZUL NOVA)
# ==============================================================================
lucro_alvo_input = preco_erp_input * (margem_erp_input / 100)
preco_sug, nome_frete_sug = calcular_preco_sugerido_reverso(
    cmv_input + custo_extra_input, lucro_alvo_input, taxa_ml_input, imposto_padrao, frete_anuncio_input
)

# HTML Personalizado para a Caixa Azul (Visual Limpo)
st.markdown(f"""
<div class="suggestion-box">
    <div style="display: flex; justify-content: space-around; align-items: center;">
        <div>
            <div class="sug-title">META DE LUCRO (ERP)</div>
            <div class="sug-value">R$ {lucro_alvo_input:.2f}</div>
            <div class="sug-sub">{margem_erp_input}% sobre R$ {preco_erp_input}</div>
        </div>
        <div style="font-size: 30px; color: #90caf9;">➔</div>
        <div>
            <div class="sug-title">PREÇO SUGERIDO ML</div>
            <div class="sug-value">R$ {preco_sug:.2f}</div>
            <div class="sug-sub">Considerando {nome_frete_sug}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# BOTÃO ADICIONAR (COM CALLBACK DE LIMPEZA)
# O argumento 'on_click' chama a função de limpeza antes de recarregar
if st.button("⬇️ ADICIONAR PRODUTO À LISTA", type="primary", use_container_width=True, on_click=limpar_campos_produto):
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
        st.toast(f"Produto {nome_produto_input} salvo!", icon="✅")
    else:
        st.error("Por favor, digite o Nome do Produto.")

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
    
    # Loop reverso
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        with st.container(border=True):
            
            # --- CÁLCULOS ---
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
            
            # --- DISPLAY LINHA ---
            c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
            c1.write(f"**{item['MLB']}**")
            c2.write(item['Produto'])
            
            cor_css = "text-success" if lucro_final > 0 else "text-danger"
            c3.markdown(f"<span class='{cor_css}'>R$ {lucro_final:.2f}</span> ({margem_final:.1f}%)", unsafe_allow_html=True)
                
            if c4.button("🗑️", key=f"del_{item['id']}"):
                st.session_state.lista_produtos.remove(item)
                st.rerun()

            # --- EXPANDER ---
            with st.expander(f"✏️ Detalhes e Ajustes - {item['Produto']}"):
                
                ec1, ec2, ec3 = st.columns(3)
                
                # Campos de Edição com Auto-Save
                novo_preco = ec1.number_input("Preço Tabela (DE)", value=float(item['PrecoBase']), step=0.5, key=f"pb_{item['id']}")
                novo_desc = ec2.number_input("Desconto (%)", value=float(item['DescontoPct']), step=0.5, key=f"dc_{item['id']}")
                novo_bonus = ec3.number_input("Bônus ML (R$)", value=float(item['Bonus']), step=0.01, key=f"bn_{item['id']}")
                
                # Lógica de Atualização
                if (novo_preco != item['PrecoBase'] or novo_desc != item['DescontoPct'] or novo_bonus != item['Bonus']):
                    item['PrecoBase'] = novo_preco
                    item['DescontoPct'] = novo_desc
                    item['Bonus'] = novo_bonus
                    st.rerun()

                st.divider()
                
                # --- DRE NATIVA ---
                st.caption("DEMONSTRATIVO FINANCEIRO")
                
                r1, r2 = st.columns([3, 1])
                r1.write("(+) Preço Tabela")
                r2.write(f"R$ {preco_base_calc:.2f}")
                
                if desc_calc > 0:
                    r1, r2 = st.columns([3, 1])
                    r1.markdown(f":red[(-) Desconto ({desc_calc}%) ]")
                    r2.markdown(f":red[- R$ {preco_base_calc - preco_final_calc:.2f}]")
                
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

    # Footer Download
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
        st.rerun()

else:
    st.info("Lista vazia. Adicione produtos acima.")
