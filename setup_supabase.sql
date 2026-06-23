-- Script para criar o esquema do banco de dados no Supabase (Rodar no SQL Editor)

-- 1. Tabela de Cursos
CREATE TABLE cursos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Tabela de Professores
CREATE TABLE professores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Tabela de Turmas
-- Uma turma pertence a um Curso e pode ter um Professor principal associado
CREATE TABLE turmas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    curso_id UUID REFERENCES cursos(id) ON DELETE CASCADE,
    professor_id UUID REFERENCES professores(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Tabela de Matérias
-- Matérias que pertencem a um curso específico (Módulos do curso)
CREATE TABLE materias (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    curso_id UUID REFERENCES cursos(id) ON DELETE CASCADE,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Tabela de Alunos
-- Usamos a Matrícula como Chave Primária (PK)
CREATE TABLE alunos (
    matricula TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    turma_id UUID REFERENCES turmas(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. Tabela de Notas e Frequência
-- Guarda as notas e presenças de cada aluno por matéria
CREATE TABLE notas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    aluno_matricula TEXT REFERENCES alunos(matricula) ON DELETE CASCADE,
    materia_id UUID REFERENCES materias(id) ON DELETE CASCADE,
    nota NUMERIC(5,2) DEFAULT 0.0,
    presencas INTEGER DEFAULT 0,
    faltas INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    -- Garante que um aluno não tenha duas notas para a mesma matéria na mesma vez
    UNIQUE (aluno_matricula, materia_id)
);
