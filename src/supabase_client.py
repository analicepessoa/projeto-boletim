import math
import os

import streamlit as st
from supabase import Client, create_client


def _config_value(name: str) -> str:
    """Lê configuração local, do Streamlit Cloud ou de variável de ambiente."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""

# O st.cache_resource garante que o cliente Supabase seja inicializado apenas uma vez
@st.cache_resource
def get_supabase_client() -> Client:
    url = _config_value("SUPABASE_URL")
    key = _config_value("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase não configurado. Informe SUPABASE_URL e SUPABASE_KEY "
            "nas configurações do aplicativo."
        )
    return create_client(url, key)


def testar_conexao() -> tuple[bool, str]:
    """Confirma configuração, acesso ao banco e existência do esquema básico."""
    try:
        get_supabase_client().table("cursos").select("id").limit(1).execute()
        return True, ""
    except Exception as exc:
        return False, str(exc)

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

def _tem_historico_de_turmas(supabase) -> bool:
    """Detecta se a migração aluno_turmas/notas.turma_id já foi aplicada."""
    try:
        supabase.table("aluno_turmas").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _matricula_exibicao(matricula_interna: str) -> str:
    """Remove o prefixo interno usado por bancos antigos para separar turmas."""
    return str(matricula_interna).rsplit("::", 1)[-1]


def _chave_aluno_banco_antigo(supabase, matricula: str, turma_id: str) -> str:
    """Mantém históricos separados mesmo antes da migração estrutural do banco."""
    chave_por_turma = f"{turma_id}::{matricula}"
    por_turma = (
        supabase.table("alunos")
        .select("matricula")
        .eq("matricula", chave_por_turma)
        .limit(1)
        .execute()
        .data
    ) or []
    if por_turma:
        return chave_por_turma

    cadastro_original = (
        supabase.table("alunos")
        .select("matricula,turma_id")
        .eq("matricula", matricula)
        .limit(1)
        .execute()
        .data
    ) or []
    if not cadastro_original or cadastro_original[0].get("turma_id") == turma_id:
        return matricula
    return chave_por_turma

def salvar_dados_upload(df_consolidado, turma_id: str, materia_id: str):
    """
    Recebe o DataFrame gerado pelo processador e salva Alunos e Notas no Supabase.
    """
    supabase = get_supabase_client()
    banco_com_historico = _tem_historico_de_turmas(supabase)
    
    # Prepara lista de alunos únicos e notas
    sucesso_notas = 0
    
    for index, row in df_consolidado.iterrows():
        matricula = str(row['Matrícula']).strip()
        nome = str(row['Nome']).strip()
        
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
            
        frequencia_lista = row.get('Frequencia_Detalhada', [])
        notas_extras = row.get('Notas_Detalhadas', {})
        
        detalhes = {
            "frequencia": frequencia_lista,
            "notas": notas_extras
        }
        
        chave_aluno = matricula if banco_com_historico else _chave_aluno_banco_antigo(
            supabase, matricula, turma_id
        )

        # 1. Tenta inserir ou garantir que o aluno existe (Upsert)
        aluno_data = {
            "matricula": chave_aluno,
            "nome": nome,
            "turma_id": turma_id
        }
        supabase.table("alunos").upsert(aluno_data, on_conflict="matricula").execute()

        if banco_com_historico:
            # Mantém o histórico de todas as turmas cursadas pelo aluno.
            supabase.table("aluno_turmas").upsert(
                {
                    "aluno_matricula": chave_aluno,
                    "turma_id": turma_id,
                },
                on_conflict="aluno_matricula,turma_id",
            ).execute()
        
        # 2. Inserir ou atualizar a nota para esta matéria específica
        nota_data = {
            "aluno_matricula": chave_aluno,
            "materia_id": materia_id,
            "nota": nota,
            "presencas": presencas,
            "faltas": faltas,
            "detalhes_json": detalhes
        }
        if banco_com_historico:
            nota_data["turma_id"] = turma_id
        
        try:
            # Atualiza ou cria em uma única operação, sem apagar a nota anterior primeiro.
            conflito = (
                "aluno_matricula,turma_id,materia_id"
                if banco_com_historico
                else "aluno_matricula,materia_id"
            )
            supabase.table("notas").upsert(nota_data, on_conflict=conflito).execute()
            sucesso_notas += 1
        except Exception as e:
            st.warning(f"Erro ao salvar nota do aluno {nome}: {str(e)}")
            
    return sucesso_notas

# ==========================================
# FUNÇÕES PARA BOLETINS
# ==========================================

def get_alunos_por_turma(turma_id: str):
    supabase = get_supabase_client()
    if _tem_historico_de_turmas(supabase):
        vinculos = (
            supabase.table("aluno_turmas")
            .select("aluno_matricula")
            .eq("turma_id", turma_id)
            .execute()
            .data
        ) or []
        matriculas = [v["aluno_matricula"] for v in vinculos]
        if not matriculas:
            return []
        alunos = (
            supabase.table("alunos")
            .select("matricula,nome")
            .in_("matricula", matriculas)
            .execute()
            .data
        ) or []
    else:
        alunos = (
            supabase.table("alunos")
            .select("matricula,nome")
            .eq("turma_id", turma_id)
            .execute()
            .data
        ) or []

    for aluno in alunos:
        aluno["matricula_exibicao"] = _matricula_exibicao(aluno["matricula"])
    return sorted(alunos, key=lambda aluno: aluno.get("nome", ""))

def get_notas_aluno(matricula: str, turma_id: str):
    supabase = get_supabase_client()
    # Puxa as notas juntamente com o nome e a ordem da matéria usando Foreign Key
    consulta = (
        supabase.table("notas")
        .select("*, materias(nome, ordem)")
        .eq("aluno_matricula", matricula)
    )
    if _tem_historico_de_turmas(supabase):
        consulta = consulta.eq("turma_id", turma_id)
    response = consulta.execute()
    return response.data

def clear_all_data():
    supabase = get_supabase_client()
    # Delete in order of dependency to respect foreign key constraints
    # 1. Notas
    supabase.table("notas").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    # 2. Vínculos entre alunos e turmas (quando a migração já existe)
    if _tem_historico_de_turmas(supabase):
        supabase.table("aluno_turmas").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    # 3. Alunos
    supabase.table("alunos").delete().neq("matricula", "").execute()
    # 4. Turmas
    supabase.table("turmas").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    # 5. Materias
    supabase.table("materias").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    # 6. Cursos
    supabase.table("cursos").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    # 7. Professores
    supabase.table("professores").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

# Force reload for streamlit
