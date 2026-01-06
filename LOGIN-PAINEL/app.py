import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os

# VERSÃO 0.2 (CORRIGIDA)
# ==============================================================================
# 1. CONFIGURAÇÃO INICIAL E CSS (VISUAL)
# ==============================================================================
st.set_page_config(
    page_title="Painel Comercial | CIG 360º",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed" # Sidebar escondida no login, expandida no painel
)

# CSS para remover espaços em branco e maximizar a área do Power BI
st.markdown("""
    <style>
        /* Remove o padding padrão do topo e laterais do Streamlit */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        /* Esconde o menu 'hambúrguer' padrão do canto superior direito */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Ajuste fino para o iframe não ter bordas indesejadas */
        iframe {
            display: block;
            border: none;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONSTANTES
# ==============================================================================
ARQUIVO_USUARIOS = 'usuarios.xlsx'
ARQUIVO_LOGS = 'logs_acesso.xlsx'

# ==============================================================================
# 3. FUNÇÕES DE BACKEND (LÓGICA E DADOS)
# ==============================================================================

def carregar_usuarios():
    """Carrega usuários do Excel, tratando erros de formatação (espaços, maiúsculas)."""
    try:
        # dtype=str previne erros se a senha for puramente numérica
        df = pd.read_excel(ARQUIVO_USUARIOS, dtype=str)
        
        # Limpeza: converte colunas para minúsculo e remove espaços
        df.columns = df.columns.str.strip().str.lower()
        
        # Dicionário de sinônimos para garantir que o código encontre as colunas
        correcoes = {
            'e-mail': 'email', 'login': 'email', 'usuário': 'email', 'usuario': 'email',
            'pass': 'senha', 'password': 'senha', 'key': 'senha',
            'url': 'link', 'dashboard': 'link'
        }
        df.rename(columns=correcoes, inplace=True)
        return df
    except Exception as e:
        st.error(f"Erro crítico ao ler '{ARQUIVO_USUARIOS}': {e}")
        return pd.DataFrame()

def registrar_entrada(usuario, email):
    """Grava o log de entrada no arquivo Excel."""
    try:
        if os.path.exists(ARQUIVO_LOGS):
            df_logs = pd.read_excel(ARQUIVO_LOGS)
        else:
            df_logs = pd.DataFrame(columns=['data_login', 'hora_login', 'usuario', 'email', 'data_logout', 'hora_logout', 'tempo_sessao'])
        
        agora = datetime.now()
        novo_log = {
            'data_login': agora.strftime('%Y-%m-%d'),
            'hora_login': agora.strftime('%H:%M:%S'),
            'usuario': usuario,
            'email': email,
            'data_logout': '',
            'hora_logout': '',
            'tempo_sessao': ''
        }
        
        df_logs = pd.concat([df_logs, pd.DataFrame([novo_log])], ignore_index=True)
        df_logs.to_excel(ARQUIVO_LOGS, index=False)
        return len(df_logs) - 1, agora # Retorna índice e hora para usar no logout
    except Exception as e:
        st.error(f"Falha ao registrar log: {e}")
        return None, None

def registrar_saida(index_log, tempo_inicio):
    """Atualiza o log com o horário de saída e duração."""
    try:
        if index_log is None: return
        df_logs = pd.read_excel(ARQUIVO_LOGS)
        agora = datetime.now()
        duracao = str(agora - tempo_inicio).split('.')[0] # Remove milissegundos
        
        df_logs.at[index_log, 'data_logout'] = agora.strftime('%Y-%m-%d')
        df_logs.at[index_log, 'hora_logout'] = agora.strftime('%H:%M:%S')
        df_logs.at[index_log, 'tempo_sessao'] = duracao
        
        df_logs.to_excel(ARQUIVO_LOGS, index=False)
    except Exception:
        pass # Falha silenciosa no logout para não travar o usuário

def autenticar_usuario(email, senha):
    """Valida as credenciais comparando com a base carregada."""
    df = carregar_usuarios()
    if df.empty or 'email' not in df.columns or 'senha' not in df.columns:
        st.error("Base de dados incompleta. Verifique as colunas do Excel.")
        return None

    email = str(email).strip()
    senha = str(senha).strip()
    
    # Filtro seguro convertendo tudo para string
    usuario = df[
        (df['email'].astype(str).str.strip() == email) & 
        (df['senha'].astype(str).str.strip() == senha)
    ]
    
    return usuario.iloc[0] if not usuario.empty else None

# ==============================================================================
# 4. GERENCIAMENTO DE ESTADO (SESSION STATE)
# ==============================================================================
if 'logado' not in st.session_state:
    st.session_state.update({
        'logado': False,
        'user_data': None,
        'log_index': None,
        'login_time': None
    })

# ==============================================================================
# 5. FRONTEND - ROTEAMENTO DE TELAS
# ==============================================================================

if not st.session_state['logado']:
    # --- TELA 1: LOGIN ---

    # 1. LOGO NO CANTO SUPERIOR DIREITO
    col_vazia, col_logo = st.columns([8, 2])
    
    with col_logo:
        # Verifica se a imagem existe (Case Sensitive no Linux do servidor!)
        if os.path.exists("logo.png"):
            st.image("logo.png", width=150) 
        elif os.path.exists("Logo.png"): # Tenta com maiúscula por garantia
            st.image("Logo.png", width=150)
        else:
            st.write("📍 Logo aqui") 

    # Espaçamento vertical
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. FORMULÁRIO CENTRALIZADO
    col_esq, col_centro, col_dir = st.columns([1, 3, 1])
    
    with col_centro:
        # TÍTULO FORÇADO EM UMA LINHA
        st.markdown("""
            <h1 style='text-align: center; white-space: nowrap; font-size: 2.5rem;'>
                📊 PAINEL COMERCIAL | CIG 360°
            </h1>
        """, unsafe_allow_html=True)
        
        st.info("Insira suas credenciais corporativas.")
        
        with st.form(key='form_login'):
            email_input = st.text_input("E-mail")
            senha_input = st.text_input("Senha", type="password")
            
            btn_entrar = st.form_submit_button("Acessar Painel", use_container_width=True)
            
            if btn_entrar:
                user = autenticar_usuario(email_input, senha_input)
                if user is not None:
                    # Sucesso
                    st.session_state['logado'] = True
                    st.session_state['user_data'] = user
                    
                    # Registrar log
                    idx, t_inicio = registrar_entrada(user.get('nome', 'Desconhecido'), user['email'])
                    st.session_state['log_index'] = idx
                    st.session_state['login_time'] = t_inicio
                    
                    st.success("Autenticado! Redirecionando...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Acesso negado. Verifique usuário e senha.")
else:
    # --- TELA 2: DASHBOARD (LOGADO) ---
    
    dados_usuario = st.session_state['user_data']
    link_bi = dados_usuario.get('link', '')

    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.header("Menu")
        st.markdown(f"👤 **Usuário:** {dados_usuario.get('nome', 'Visitante')}")
        st.markdown(f"📧 **Email:** {dados_usuario.get('email', '')}")
        st.divider()
        
        if st.button("Sair / Logout 🚪", use_container_width=True):
            registrar_saida(st.session_state['log_index'], st.session_state['login_time'])
            # Limpa sessão
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

    # --- ÁREA PRINCIPAL (POWER BI) ---
    if pd.isna(link_bi) or str(link_bi).strip() == "":
        st.warning("⚠️ Nenhum painel vinculado a este usuário.")
    else:
        # Renderização do Power BI ocupando toda a altura disponível (95vh)
        # CORREÇÃO AQUI: Mudado de 605vh para 95vh
        html_powerbi = f"""
            <iframe 
                title="Dashboard Corporativo" 
                width="100%" 
                height="605vh" 
                src="{link_bi}" 
                frameborder="0" 
                allowFullScreen="true"
                style="border: none; overflow: hidden;">
            </iframe>
        """
        st.markdown(html_powerbi, unsafe_allow_html=True)