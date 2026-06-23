import os
from supabase import create_client, Client
import streamlit as st

# Usando as credenciais informadas pelo usuário
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zfevvffmayedloyhzhlt.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_-UWnsy5OXQLwnoaIoJiavg_33ASJBxW")

# O st.cache_resource garante que o cliente Supabase seja inicializado apenas uma vez
@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# FUNÇÕES DE CRUD - PAINEL ADMIN
# ==========================================

def get_professores():
    supabase = get_supabase_client()
    response = supabase.table("professores").select("*").execute()
    return response.data

def insert_professor(nome: str):
    supabase = get_supabase_client()
    response = supabase.table("professores").insert({"nome": nome}).execute()
    return response.data

def delete_professor(prof_id: str):
    supabase = get_supabase_client()
    response = supabase.table("professores").delete().eq("id", prof_id).execute()
    return response.data

def get_cursos():
    supabase = get_supabase_client()
    response = supabase.table("cursos").select("*").execute()
    return response.data

def insert_curso(nome: str):
    supabase = get_supabase_client()
    response = supabase.table("cursos").insert({"nome": nome}).execute()
    return response.data

def delete_curso(curso_id: str):
    supabase = get_supabase_client()
    response = supabase.table("cursos").delete().eq("id", curso_id).execute()
    return response.data

def get_materias():
    supabase = get_supabase_client()
    response = supabase.table("materias").select("*, cursos(nome)").order("ordem").execute()
    return response.data

def get_materias_por_curso(curso_id: str):
    supabase = get_supabase_client()
    response = supabase.table("materias").select("*").eq("curso_id", curso_id).order("ordem").execute()
    return response.data

def insert_materia(nome: str, curso_id: str, ordem: int = 0):
    supabase = get_supabase_client()
    response = supabase.table("materias").insert({"nome": nome, "curso_id": curso_id, "ordem": ordem}).execute()
    return response.data

def delete_materia(materia_id: str):
    supabase = get_supabase_client()
    response = supabase.table("materias").delete().eq("id", materia_id).execute()
    return response.data

def get_turmas():
    supabase = get_supabase_client()
    response = supabase.table("turmas").select("*, cursos(nome), professores(nome)").execute()
    return response.data

def insert_turma(nome: str, curso_id: str, professor_id: str):
    supabase = get_supabase_client()
    response = supabase.table("turmas").insert({
        "nome": nome,
        "curso_id": curso_id,
        "professor_id": professor_id
    }).execute()
    return response.data

def delete_turma(turma_id: str):
    supabase = get_supabase_client()
    response = supabase.table("turmas").delete().eq("id", turma_id).execute()
    return response.data

# ==========================================
# FUNÇÕES DE UPLOAD E NOTAS
# ==========================================

import math

def salvar_dados_upload(df_consolidado, turma_id: str, materia_id: str):
    """
    Recebe o DataFrame gerado pelo processador e salva Alunos e Notas no Supabase.
    """
    supabase = get_supabase_client()
    
    # Prepara lista de alunos únicos e notas
    sucesso_notas = 0
    
    for index, row in df_consolidado.iterrows():
        matricula = str(row['Matrícula'])
        nome = str(row['Nome'])
        
        # Lida com NaN de forma segura
        try:
            nota = float(row.get('Nota', 0.0))
            if math.isnan(nota):
                nota = 0.0
        except (ValueError, TypeError):
            nota = 0.0
            
        try:
            presencas = int(row.get('Presenças', 0))
        except (ValueError, TypeError):
            presencas = 0
            
        try:
            faltas = int(row.get('Faltas', 0))
        except (ValueError, TypeError):
            faltas = 0
        
        # 1. Tenta inserir ou garantir que o aluno existe (Upsert)
        # Como o upsert nativo baseia-se na PK (matrícula), usamos upsert
        aluno_data = {
            "matricula": matricula,
            "nome": nome,
            "turma_id": turma_id
        }
        supabase.table("alunos").upsert(aluno_data).execute()
        
        # 2. Inserir ou atualizar a nota para esta matéria específica
        # Usamos on_conflict para lidar com a UNIQUE constraint se ela for criada depois
        nota_data = {
            "aluno_matricula": matricula,
            "materia_id": materia_id,
            "nota": nota,
            "presencas": presencas,
            "faltas": faltas
        }
        
        # Como é uma relação única entre aluno e materia, caso já exista, precisa atualizar.
        # Mas para simplificar, vamos tentar deletar a nota antiga se houver, e inserir a nova, 
        # ou apenas inserir e tratar erro
        try:
            # Apaga registro anterior se existir para evitar erro de duplicidade
            supabase.table("notas").delete().eq("aluno_matricula", matricula).eq("materia_id", materia_id).execute()
            
            # Insere a nova
            supabase.table("notas").insert(nota_data).execute()
            sucesso_notas += 1
        except Exception as e:
            st.warning(f"Erro ao salvar nota do aluno {nome}: {str(e)}")
            
    return sucesso_notas

# ==========================================
# FUNÇÕES PARA BOLETINS
# ==========================================

def get_alunos_por_turma(turma_id: str):
    supabase = get_supabase_client()
    response = supabase.table("alunos").select("*").eq("turma_id", turma_id).execute()
    return response.data

def get_notas_aluno(matricula: str):
    supabase = get_supabase_client()
    # Puxa as notas juntamente com o nome da matéria usando Foreign Key
    response = supabase.table("notas").select("*, materias(nome)").eq("aluno_matricula", matricula).execute()
    return response.data

# Force reload for streamlit
