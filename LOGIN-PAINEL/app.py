import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os

# VERSÃO 0.3 (SEGURANÇA IMPLEMENTADA + LOGOUT VISÍVEL)

#============================================
# COMANDO DE DEPLOY
#============================================
# git add .
# git commit -m "Pequenos ajustes e correcoes"
# git push

# ==============================================================================
# 1. CONFIGURAÇÃO INICIAL E CSS
# ==============================================================================
st.set_page_config(
    page_title="Painel Comercial | CIG 360º",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Ajustado
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important; /* Um pouco de espaço para o botão Sair */
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        iframe {
            display: block;
            border: none;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CONSTANTES DE CAMINHOS
# ==============================================================================
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
# O arquivo de usuarios.xlsx NÃO É MAIS USADO para leitura de senhas
ARQUIVO_LOGS = os.path.join(PASTA_ATUAL, 'logs_acesso.xlsx')
CAMINHO_LOGO = os.path.join(PASTA_ATUAL, 'logo.png')

# ==============================================================================
# 3. FUNÇÕES DE BACKEND
# ==============================================================================

def carregar_usuarios_seguros():
    """
    Carrega usuários diretamente do Streamlit Secrets (Cofre na Nuvem).
    Substitui o arquivo Excel inseguro.
    """
    try:
        # Verifica se existem segredos configurados
        if 'usuarios' in st.secrets:
            # Transforma a lista do TOML em DataFrame do Pandas
            df = pd.DataFrame(st.secrets['usuarios'])
            
            # Garante que colunas de texto sejam strings
            df['email'] = df['email'].astype(str).str.strip().str.lower()
            df['senha'] = df['senha'].astype(str).str.strip()
            return df
        else:
            st.error("ERRO DE CONFIGURAÇÃO: 'Secrets' não encontrados no Streamlit Cloud.")
            return pd.DataFrame()
            
    except Exception as e:
        # Fallback para teste local (opcional) se não tiver secrets configurado no PC
        st.warning(f"Usando modo local ou erro nos secrets: {e}")
        return pd.DataFrame()

def registrar_entrada(usuario, email):
    try:
        # Cria o arquivo de logs se não existir
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
        return len(df_logs) - 1, agora
    except Exception as e:
        st.error(f"Falha ao registrar log: {e}")
        return None, None

def registrar_saida(index_log, tempo_inicio):
    try:
        if index_log is None: return
        df_logs = pd.read_excel(ARQUIVO_LOGS)
        agora = datetime.now()
        
        # Calcula tempo
        duracao = str(agora - tempo_inicio).split('.')[0]
        
        df_logs.at[index_log, 'data_logout'] = agora.strftime('%Y-%m-%d')
        df_logs.at[index_log, 'hora_logout'] = agora.strftime('%H:%M:%S')
        df_logs.at[index_log, 'tempo_sessao'] = duracao
        
        df_logs.to_excel(ARQUIVO_LOGS, index=False)
    except Exception:
        pass

def autenticar_usuario(email, senha):
    # AGORA USA A FUNÇÃO SEGURA
    df = carregar_usuarios_seguros()
    
    if df.empty:
        return None

    email = str(email).strip().lower()
    senha = str(senha).strip()
    
    usuario = df[
        (df['email'] == email) & 
        (df['senha'] == senha)
    ]
    
    return usuario.iloc[0] if not usuario.empty else None

# ==============================================================================
# 4. GERENCIAMENTO DE ESTADO
# ==============================================================================
if 'logado' not in st.session_state:
    st.session_state.update({
        'logado': False, 'user_data': None, 'log_index': None, 'login_time': None
    })

# ==============================================================================
# 5. FRONTEND
# ==============================================================================

if not st.session_state['logado']:
    # --- TELA DE LOGIN ---
    col_vazia, col_logo = st.columns([8, 2])
    with col_logo:
        if os.path.exists(CAMINHO_LOGO):
            st.image(CAMINHO_LOGO, width=150)
        else:
            st.write("")

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_esq, col_centro, col_dir = st.columns([1, 3, 1])
    with col_centro:
        st.markdown("<h1 style='text-align: center; white-space: nowrap; font-size: 2.5rem;'>📊 PAINEL COMERCIAL | CIG 360°</h1>", unsafe_allow_html=True)
        st.info("Insira suas credenciais corporativas.")
        
        with st.form(key='form_login'):
            email_input = st.text_input("E-mail")
            senha_input = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Acessar Painel", use_container_width=True)
            
            if btn_entrar:
                user = autenticar_usuario(email_input, senha_input)
                if user is not None:
                    st.session_state['logado'] = True
                    st.session_state['user_data'] = user
                    idx, t_inicio = registrar_entrada(user.get('nome', 'Visitante'), user['email'])
                    st.session_state['log_index'] = idx
                    st.session_state['login_time'] = t_inicio
                    st.success("Autenticado! Carregando...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Acesso negado. Verifique suas credenciais.")

else:
    # --- TELA DO POWER BI (LOGADO) ---
    
    dados = st.session_state['user_data']
    link_bi = dados.get('link', '')

    # BARRA SUPERIOR COM BOTÃO SAIR
    # Divide em: Saudação (Esquerda) e Botão Sair (Direita)
    col_info, col_logout = st.columns([9, 1])
    
    with col_info:
        st.markdown(f"👤 **{dados.get('nome', 'Usuário')}** | {dados.get('email', '')}")
    
    with col_logout:
        # BOTÃO SAIR AGORA NA TELA PRINCIPAL
        if st.button("Sair 🚪", key='btn_sair_topo', use_container_width=True):
            registrar_saida(st.session_state['log_index'], st.session_state['login_time'])
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
            
    st.divider()

    # POWER BI
    if pd.isna(link_bi) or str(link_bi).strip() == "":
        st.warning("⚠️ Nenhum painel vinculado.")
    else:
        html_powerbi = f"""
            <iframe 
                title="Dashboard" 
                width="100%" 
                height="605vh" 
                src="{link_bi}" 
                frameborder="0" 
                allowFullScreen="true"
                style="border: none; overflow: hidden;">
            </iframe>
        """
        st.markdown(html_powerbi, unsafe_allow_html=True)