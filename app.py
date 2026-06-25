import streamlit as st
import pandas as pd
import os
from src.data_processor import processar_planilhas
from src.chart_maker import gerar_grafico_frequencia
from src.pdf_generator import gerar_pdf
import src.supabase_client as db

st.set_page_config(page_title="ALLNET - Boletins Escolares", page_icon="📊", layout="wide")

# Cria pastas necessárias se não existirem
if not os.path.exists("assets"):
    os.makedirs("assets")

# CSS Customizado
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    h1, h2, h3 { color: #0f172a; font-family: 'Inter', sans-serif; font-weight: 700; }
    .stFileUploader {
        border: 2px dashed #3b82f6; border-radius: 12px; padding: 20px;
        background-color: #eff6ff; transition: all 0.3s ease;
    }
    .stFileUploader:hover { border-color: #2563eb; background-color: #dbeafe; }
    .stButton>button {
        background-color: #2563eb; color: white; border: none; border-radius: 8px;
        padding: 10px 24px; font-weight: 600; transition: all 0.2s ease;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    .stButton>button:hover { background-color: #1d4ed8; transform: translateY(-1px); }
    div[data-testid="metric-container"] {
        background-color: white; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 20px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Título principal
col_logo, col_title = st.columns([1, 4])
logo_path = os.path.join("assets", "logo_allnet.png")
with col_logo:
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.markdown("<h2 style='color: #ff4500;'>all <span style='color: #0055ff;'>net</span></h2>", unsafe_allow_html=True)

with col_title:
    st.title("Sistema de Consolidação e Boletins")
    st.markdown("Gerencie dados e emita boletins de forma centralizada (Supabase).")

# Estrutura em Abas
tab_upload, tab_admin, tab_boletins = st.tabs(["📤 Upload de Dados", "⚙️ Painel Admin", "📄 Boletins"])

# ================================
# ABA: PAINEL ADMIN
# ================================
with tab_admin:
    st.header("Gerenciamento do Sistema")
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("👨‍🏫 Cadastrar Professor"):
            with st.form("form_prof"):
                nome_prof = st.text_input("Nome")
                if st.form_submit_button("Salvar") and nome_prof:
                    db.insert_professor(nome_prof)
                    st.success("Professor salvo!")
                    
        with st.expander("📚 Cadastrar Curso"):
            cursos_atuais = db.get_cursos()
            if cursos_atuais:
                st.markdown("**Cursos já cadastrados:**")
                nomes_cursos = [c['nome'] for c in cursos_atuais]
                st.write(", ".join(nomes_cursos))
            else:
                st.info("Nenhum curso cadastrado ainda.")
                
            with st.form("form_curso"):
                nome_curso = st.text_input("Nome do Curso")
                if st.form_submit_button("Salvar") and nome_curso:
                    nomes_existentes = [c['nome'].strip().lower() for c in (cursos_atuais or [])]
                    if nome_curso.strip().lower() in nomes_existentes:
                        st.warning(f"O curso '{nome_curso}' já está cadastrado!")
                    else:
                        db.insert_curso(nome_curso)
                        st.success("Curso salvo!")
                        st.rerun()
                    
        with st.expander("📖 Cadastrar Matéria"):
            cursos_mat = db.get_cursos()
            if cursos_mat:
                with st.form("form_materia"):
                    nome_materia = st.text_input("Nome da Matéria (Ex: Windows, Excel)")
                    curso_dict_mat = {c['id']: c['nome'] for c in cursos_mat}
                    sel_curso_mat = st.selectbox("Curso a qual pertence", list(curso_dict_mat.keys()), format_func=lambda x: curso_dict_mat[x])
                    ordem_materia = st.number_input("Ordem de exibição (Ex: 1, 2, 3...)", min_value=0, value=0, step=1)
                    if st.form_submit_button("Salvar") and nome_materia:
                        db.insert_materia(nome_materia, sel_curso_mat, int(ordem_materia))
                        st.success("Matéria salva!")
                        st.rerun()
            else:
                st.info("Cadastre ao menos um Curso primeiro.")
                    
    with col2:
        with st.expander("👥 Cadastrar Turma", expanded=True):
            professores = db.get_professores()
            cursos = db.get_cursos()
            
            if professores and cursos:
                with st.form("form_turma"):
                    nome_turma = st.text_input("Nome da Turma (Ex: INF 5.0)")
                    prof_dict = {p['id']: p['nome'] for p in professores}
                    curso_dict = {c['id']: c['nome'] for c in cursos}
                    
                    sel_prof = st.selectbox("Professor Responsável", list(prof_dict.keys()), format_func=lambda x: prof_dict[x])
                    sel_curso = st.selectbox("Curso", list(curso_dict.keys()), format_func=lambda x: curso_dict[x])
                    
                    if st.form_submit_button("Criar Turma") and nome_turma:
                        db.insert_turma(nome_turma, sel_curso, sel_prof)
                        st.success("Turma criada com sucesso!")
                        st.rerun()
            else:
                st.info("Cadastre ao menos um Professor e um Curso primeiro.")
                
    st.divider()
    with st.expander("🗑️ Excluir Registros Permanentes"):
        st.warning("Atenção: A exclusão é permanente.")
        tab_del_prof, tab_del_curso, tab_del_mat, tab_del_turma = st.tabs(["Professores", "Cursos", "Matérias", "Turmas"])
        
        with tab_del_prof:
            profs = db.get_professores()
            if profs:
                prof_dict_del = {p['id']: p['nome'] for p in profs}
                with st.form("form_del_prof"):
                    sel_prof_del = st.selectbox("Selecione o Professor", list(prof_dict_del.keys()), format_func=lambda x: prof_dict_del[x])
                    if st.form_submit_button("Excluir Professor"):
                        db.delete_professor(sel_prof_del)
                        st.success("Professor excluído!")
                        st.rerun()
                        
        with tab_del_curso:
            cursos_cad = db.get_cursos()
            if cursos_cad:
                curso_dict_del = {c['id']: c['nome'] for c in cursos_cad}
                with st.form("form_del_curso"):
                    sel_curso_del = st.selectbox("Selecione o Curso", list(curso_dict_del.keys()), format_func=lambda x: curso_dict_del[x])
                    if st.form_submit_button("Excluir Curso"):
                        db.delete_curso(sel_curso_del)
                        st.success("Curso excluído!")
                        st.rerun()
                        
        with tab_del_mat:
            mats = db.get_materias()
            if mats:
                mat_dict_del = {m['id']: f"{m['nome']} ({m['cursos']['nome']})" for m in mats if m.get('cursos')}
                if mat_dict_del:
                    with st.form("form_del_mat"):
                        sel_mat_del = st.selectbox("Selecione a Matéria", list(mat_dict_del.keys()), format_func=lambda x: mat_dict_del[x])
                        if st.form_submit_button("Excluir Matéria"):
                            db.delete_materia(sel_mat_del)
                            st.success("Matéria excluída!")
                            st.rerun()
                        
        with tab_del_turma:
            turmas_cadastradas = db.get_turmas()
            if turmas_cadastradas:
                turma_dict_del = {t['id']: f"{t['nome']} ({t['cursos']['nome']})" for t in turmas_cadastradas if t.get('cursos')}
                if turma_dict_del:
                    with st.form("form_del_turma"):
                        sel_turma_del = st.selectbox("Selecione a Turma", list(turma_dict_del.keys()), format_func=lambda x: turma_dict_del[x])
                        if st.form_submit_button("Excluir Turma"):
                            db.delete_turma(sel_turma_del)
                            st.success("Turma excluída!")
                            st.rerun()

    with st.expander("💥 Redefinir / Limpar Todo o Banco de Dados"):
        st.error("PERIGO: Esta ação é irreversível e excluirá todos os professores, cursos, matérias, turmas, alunos e notas do banco de dados!")
        confirmar_reset = st.checkbox("Eu tenho certeza de que desejo apagar TODOS os dados do sistema e começar do zero.", key="cb_reset_db")
        if st.button("Executar Limpeza Total", type="primary", disabled=not confirmar_reset, key="btn_reset_db"):
            with st.spinner("Excluindo dados..."):
                try:
                    db.clear_all_data()
                    st.success("O banco de dados foi completamente redefinido!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao limpar banco de dados: {e}")

# ================================
# ABA: UPLOAD DE DADOS
# ================================
with tab_upload:
    st.header("1. Upload de Diários (Planilhas)")
    
    turmas = db.get_turmas()
    
    if not turmas:
        st.warning("Cadastre Turmas no Painel Admin antes de fazer upload.")
    else:
        turma_dict = {t['id']: f"{t['nome']} ({t['cursos']['nome']})" for t in turmas}
        
        sel_turma_upload = st.selectbox("Selecione a Turma da qual esses diários pertencem:", list(turma_dict.keys()), format_func=lambda x: turma_dict[x])
        
        turma_selecionada = next(t for t in turmas if t['id'] == sel_turma_upload)
        materias_do_curso = db.get_materias_por_curso(turma_selecionada['curso_id'])
        
        if not materias_do_curso:
            st.warning("Cadastre Matérias para este curso no Painel Admin antes de fazer upload.")
        else:
            materia_dict = {m['id']: m['nome'] for m in materias_do_curso}
            
            arquivos = st.file_uploader("Selecione os arquivos Excel/CSV", accept_multiple_files=True, type=['xlsx', 'csv'], key=f"uploader_{sel_turma_upload}")
            
            arquivos_com_materias = []
            if arquivos:
                st.subheader("2. Vincular Matérias")
                for arquivo in arquivos:
                    materia_id = st.selectbox(f"Matéria para o arquivo '{arquivo.name}':", list(materia_dict.keys()), format_func=lambda x: materia_dict[x], key=f"mat_{arquivo.name}")
                    if materia_id:
                        arquivos_com_materias.append({'file': arquivo, 'materia': materia_dict[materia_id], 'materia_id': materia_id})
                        
                st.divider()
                if st.button("Processar e Salvar no Supabase", type="primary"):
                    with st.spinner("Processando planilhas e enviando para nuvem..."):
                        try:
                            for item in arquivos_com_materias:
                                df_individual = processar_planilhas([{'file': item['file'], 'materia': item['materia']}])
                                if not df_individual.empty:
                                    sucessos = db.salvar_dados_upload(df_individual, sel_turma_upload, item['materia_id'])
                            st.success("Dados lidos das planilhas e salvos no Supabase com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao processar: {e}")

# ================================
# ABA: BOLETINS
# ================================
with tab_boletins:
    st.header("Gerar Boletins Escolares")
    turmas = db.get_turmas()
    
    if turmas:
        turma_dict_bol = {t['id']: f"{t['nome']} - {t['cursos']['nome']} (Prof. {t['professores']['nome']})" for t in turmas if t.get('cursos') and t.get('professores')}
        if not turma_dict_bol:
            st.info("Nenhuma turma completa encontrada. Cadastre uma turma com curso e professor.")
        else:
            turma_sel_bol = st.selectbox("Escolha a Turma", list(turma_dict_bol.keys()), format_func=lambda x: turma_dict_bol[x])
            
            if turma_sel_bol:
                alunos = db.get_alunos_por_turma(turma_sel_bol)
                if alunos:
                    aluno_dict = {a['matricula']: a['nome'] for a in alunos}
                    aluno_sel = st.selectbox("Selecione o Aluno", list(aluno_dict.keys()), format_func=lambda x: f"{x} - {aluno_dict[x]}")
                    
                    if aluno_sel:
                        notas_aluno = db.get_notas_aluno(aluno_sel)
                        if notas_aluno:
                            df_aluno = pd.DataFrame(notas_aluno)
                            df_aluno['Matéria'] = df_aluno['materias'].apply(lambda m: m['nome'])
                            df_aluno['Ordem'] = df_aluno['materias'].apply(lambda m: m.get('ordem', 0))
                            df_aluno = df_aluno.sort_values(by='Ordem')
                            df_aluno['Nota'] = df_aluno['nota']
                            
                            df_aluno['Presenças'] = df_aluno['presencas']
                            df_aluno['Faltas'] = df_aluno['faltas']
                            df_aluno['Frequência (%)'] = df_aluno.apply(lambda r: (r['Presenças']/(r['Presenças']+r['Faltas'])*100) if (r['Presenças']+r['Faltas'])>0 else 0, axis=1)
                            df_aluno['Detalhes_JSON'] = df_aluno['detalhes_json']
                            
                            st.subheader(f"Desempenho: {aluno_dict[aluno_sel]}")
                            
                            total_p = int(df_aluno['Presenças'].sum())
                            total_f = int(df_aluno['Faltas'].sum())
                            freq_global = (total_p / (total_p + total_f) * 100) if (total_p + total_f) > 0 else 0
                            
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Matérias Cursadas", len(df_aluno))
                            m2.metric("Total Presenças", total_p)
                            m3.metric("Total Faltas", total_f)
                            m4.metric("Frequência Global", f"{freq_global:.1f}%")
                            
                            colunas_mostrar = ['Matéria', 'Nota', 'Presenças', 'Faltas', 'Frequência (%)']
                            st.dataframe(df_aluno[colunas_mostrar], use_container_width=True, hide_index=True)
                            
                            st.divider()
                            st.subheader("Gerar Boletim PDF")
                            with st.form("form_pdf"):
                                nome_responsavel = st.text_input("Nome do Responsável")
                                feedback = st.text_area("Feedback / Observações (opcional)")
                                submitted = st.form_submit_button("Preparar Documento PDF")
                                
                            if submitted:
                                with st.spinner("Gerando documento..."):
                                    chart_buffer = gerar_grafico_frequencia(total_p, total_f)
                                    dados_aluno = {
                                        'nome': aluno_dict[aluno_sel],
                                        'matricula': aluno_sel,
                                        'materias': df_aluno
                                    }
                                    
                                    turma_info = next((t for t in turmas if t['id'] == turma_sel_bol), None)
                                    caminho_pdf = gerar_pdf(
                                        dados_aluno=dados_aluno,
                                        total_presencas=total_p,
                                        total_faltas=total_f,
                                        freq_global=freq_global,
                                        responsavel=nome_responsavel,
                                        feedback=feedback,
                                        chart_buffer=chart_buffer,
                                        professor=turma_info['professores']['nome'],
                                        curso=turma_info['cursos']['nome'],
                                        turma=turma_info['nome'],
                                        logo_path=logo_path if os.path.exists(logo_path) else None
                                    )
                                    st.session_state[f'pdf_{aluno_sel}'] = caminho_pdf
                                    st.success("Boletim preparado!")
                                    
                            if f'pdf_{aluno_sel}' in st.session_state and os.path.exists(st.session_state[f'pdf_{aluno_sel}']):
                                caminho_pdf = st.session_state[f'pdf_{aluno_sel}']
                                with open(caminho_pdf, "rb") as f:
                                    st.download_button("📥 Baixar Boletim PDF", data=f, file_name=os.path.basename(caminho_pdf), mime="application/pdf")
                        else:
                            st.info("Nenhuma nota lançada para este aluno ainda.")
                else:
                    st.info("Nenhum aluno vinculado a esta turma.")
    else:
        st.warning("Cadastre Turmas no Painel Admin.")
