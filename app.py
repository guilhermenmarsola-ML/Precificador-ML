import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Precificador ML - V20 Final", layout="wide", page_icon="⚡")

# --- GERENCIAMENTO DE ESTADO ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# Inicializa variáveis
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

init_state('n_mlb', 'MLB-')
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
# Persistentes
init_state('n_frete', 18.86)
init_state('n_taxa', 16.5)
init_state('n_erp', 85.44)
init_state('n_merp', 20.0)

# --- CSS PROFISSIONAL ---
st.markdown("""
<style>
    div[data-testid="stNumberInput"] label { font-size: 13px; color: #555; }
    
    .suggestion-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #90caf9;
        color: #0d47a1;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .sug-title { font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; color: #1565c0; margin-bottom: 5px; }
    .sug-value { font-size: 28px; font-weight: 800; color: #0d47a1; line-height: 1.2; }
    .sug-sub { font-size: 12px; color: #1e88e5; margin-top: 5px; }
    .seta-div { font-size: 30px; color: #90caf9; margin-top: 15px; }
    
    .text-success { color: #28a745 !important; font-weight: bold; }
    .text-danger { color: #dc3545 !important; font-weight: bold; }
    
    div.stButton > button[kind="primary"] {
        background-color: #2962ff !important;
        color: white !important;
        border: none;
        height: 50px;
        font-size: 16px;
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #0d47a1 !important;
        box-shadow: 0 4px 8px rgba(41, 98, 255, 0.3);
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
    
    for taxa, nome, p_min, p_max in [
        (taxa_50_79, "Tab. 50-79", 50, 79),
        (taxa_29_50, "Tab. 29-50", 29, 50),
        (taxa_12_29, "Tab. 12-29", 12.5, 29)
    ]:
        custos = custo_base + taxa
        preco = (custos + lucro_alvo_reais) / divisor
        if p_min <= preco < p_max: return preco, nome
        
    return preco_est_1, "Frete Manual"

# --- FUNÇÃO CALLBACK (O SEGREDINHO QUE RESOLVE TUDO) ---
def adicionar_produto_action():
    # 1. Validar Nome
    if not st.session_state.n_nome:
        st.error("Digite o nome do produto!")
        return

    # 2. Recalcular Sugestão (Para garantir consistência)
    lucro_alvo = st.session_state.n_erp * (st.session_state.n_merp / 100)
    preco_sug, _ = calcular_preco_sugerido_reverso(
        st.session_state.n_cmv + st.session_state.n_extra,
        lucro_alvo,
        st.session_state.n_taxa,
        imposto_padrao,
        st.session_state.n_frete
    )

    # 3. Criar e Salvar Item
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
    st.toast("Produto salvo!", icon="✅")

    # 4. Limpar Campos (Apenas os variáveis)
    st.session_state.n_mlb = "MLB-"
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00
    st.session_state.n_extra = 0.00
    # Taxas mantêm o estado

# --- CABEÇALHO ---
st.title("⚡ Precificador ML Pro")

# ==============================================================================
# ÁREA 1: FORMULÁRIO
# ==============================================================================
with st.container(border=True):
    st.subheader("1. Dados do Produto")
    
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    st.text_input("SKU / MLB", key="n_mlb")
    st.text_input("Nome do Produto", key="n_nome")
    st.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
    st.number_input("Frete Cheio (>79)", step=0.01, format="%.2f", key="n_frete")

    st.divider() 
    
    c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
    st.number_input("Comissão ML (%)", step=0.5, format="%.1f", key="n_taxa")
    st.number_input("Extras (R$)", step=0.01, format="%.2f", key="n_extra")
    st.number_input("Preço ERP (R$)", step=0.01, format="%.2f", key="n_erp")
    st.number_input("Margem ERP (%)", step=1.0, format="%.1f", key="n_merp")

# ==============================================================================
# ÁREA 2: SUGESTÃO
# ==============================================================================
# Cálculo apenas para visualização prévia
lucro_alvo_view = st.session_state.n_erp * (st.session_state.n_merp / 100)
preco_sug_view, nome_frete_view = calcular_preco_sugerido_reverso(
    st.session_state.n_cmv + st.session_state.n_extra, 
    lucro_alvo_view, 
    st.session_state.n_taxa, 
    imposto_padrao, 
    st.session_state.n_frete
)

st.markdown(f"""
<div class="suggestion-box">
    <div style="display: flex; justify-content: space-around; align-items: flex-start;">
        <div style="flex: 1;">
            <div class="sug-title">META DE LUCRO (ERP)</div>
            <div class="sug-value">R$ {lucro_alvo_view:.2f}</div>
            <div class="sug-sub">{st.session_state.n_merp}% sobre R$ {st.session_state.n_erp}</div>
        </div>
        <div class="seta-div">➜</div>
        <div style="flex: 1;">
            <div class="sug-title">PREÇO SUGERIDO ML</div>
            <div class="sug-value">R$ {preco_sug_view:.2f}</div>
            <div class="sug-sub">Considerando {nome_frete_view}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# BOTÃO ADICIONAR
# A mágica acontece no on_click
st.button("⬇️ ADICIONAR PRODUTO À LISTA", type="primary", use_container_width=True, on_click=adicionar_produto_action)

# ==============================================================================
# ÁREA 3: LISTA DE GESTÃO
# ==============================================================================
if st.session_state.lista_produtos:
    st.markdown("### 📋 Produtos Precificados")
    
    cols = st.columns([1, 3, 2, 1])
    cols[0].caption("CÓDIGO")
    cols[1].caption("PRODUTO")
    cols[2].caption("LUCRO / MARGEM")
    cols[3].caption("AÇÕES")
    
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
            
            # --- LINHA ---
            c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
            c1.write(f"**{item['MLB']}**")
            c2.write(item['Produto'])
            
            cor_css = "text-success" if lucro_final > 0 else "text-danger"
            c3.markdown(f"<span class='{cor_css}'>R$ {lucro_final:.2f}</span> ({margem_final:.1f}%)", unsafe_allow_html=True)
                
            if c4.button("🗑️", key=f"del_{item['id']}"):
                st.session_state.lista_produtos.remove(item)
                try: st.rerun() 
                except: st.experimental_rerun()

            # --- EXPANDER ---
            with st.expander(f"✏️ Editar / DRE - {item['Produto']}"):
                
                ec1, ec2, ec3 = st.columns(3)
                novo_preco = ec1.number_input("Preço Tabela (DE)", value=float(item['PrecoBase']), step=0.5, key=f"pb_{item['id']}")
                novo_desc = ec2.number_input("Desconto (%)", value=float(item['DescontoPct']), step=0.5, key=f"dc_{item['id']}")
                novo_bonus = ec3.number_input("Bônus ML (R$)", value=float(item['Bonus']), step=0.01, key=f"bn_{item['id']}")
                
                if (novo_preco != item['PrecoBase'] or novo_desc != item['DescontoPct'] or novo_bonus != item['Bonus']):
                    item['PrecoBase'] = novo_preco
                    item['DescontoPct'] = novo_desc
                    item['Bonus'] = novo_bonus
                    try: st.rerun() 
                    except: st.experimental_rerun()

                st.divider()
                
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
        try: st.rerun() 
        except: st.experimental_rerun()

else:
    st.info("Lista vazia. Adicione produtos acima.")
