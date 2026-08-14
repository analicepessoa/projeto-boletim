-- Script para criar o esquema do banco de dados no Supabase (Rodar no SQL Editor)

-- 1. Tabela de Cursos
CREATE TABLE IF NOT EXISTS cursos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Tabela de Professores
CREATE TABLE IF NOT EXISTS professores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Tabela de Turmas
-- Uma turma pertence a um Curso e pode ter um Professor principal associado
CREATE TABLE IF NOT EXISTS turmas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    curso_id UUID REFERENCES cursos(id) ON DELETE CASCADE,
    professor_id UUID REFERENCES professores(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Tabela de Matérias
-- Matérias que pertencem a um curso específico (Módulos do curso)
CREATE TABLE IF NOT EXISTS materias (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    curso_id UUID REFERENCES cursos(id) ON DELETE CASCADE,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Tabela de Alunos
-- Usamos a Matrícula como Chave Primária (PK)
CREATE TABLE IF NOT EXISTS alunos (
    matricula TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    turma_id UUID REFERENCES turmas(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. Histórico de turmas cursadas por cada aluno
CREATE TABLE IF NOT EXISTS aluno_turmas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    aluno_matricula TEXT NOT NULL REFERENCES alunos(matricula) ON DELETE CASCADE,
    turma_id UUID NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE (aluno_matricula, turma_id)
);

-- 7. Tabela de Notas e Frequência
-- Guarda as notas e presenças de cada aluno por matéria
CREATE TABLE IF NOT EXISTS notas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    aluno_matricula TEXT REFERENCES alunos(matricula) ON DELETE CASCADE,
    turma_id UUID NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
    materia_id UUID REFERENCES materias(id) ON DELETE CASCADE,
    nota NUMERIC(5,2) DEFAULT 0.0,
    presencas INTEGER DEFAULT 0,
    faltas INTEGER DEFAULT 0,
    detalhes_json JSONB DEFAULT '{"frequencia": [], "notas": {}}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    -- O mesmo aluno pode cursar a mesma matéria em turmas diferentes.
    UNIQUE (aluno_matricula, turma_id, materia_id)
);

-- Migração segura para bancos criados com a versão anterior.
ALTER TABLE notas
ADD COLUMN IF NOT EXISTS detalhes_json JSONB
DEFAULT '{"frequencia": [], "notas": {}}'::jsonb;

ALTER TABLE notas
ADD COLUMN IF NOT EXISTS turma_id UUID REFERENCES turmas(id) ON DELETE CASCADE;

-- O campo turma_id de alunos passa a indicar apenas a turma mais recente.
ALTER TABLE alunos DROP CONSTRAINT IF EXISTS alunos_turma_id_fkey;
ALTER TABLE alunos
ADD CONSTRAINT alunos_turma_id_fkey
FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE SET NULL;

-- Conserva todos os vínculos existentes antes de ativar o novo modelo.
INSERT INTO aluno_turmas (aluno_matricula, turma_id)
SELECT matricula, turma_id
FROM alunos
WHERE turma_id IS NOT NULL
ON CONFLICT (aluno_matricula, turma_id) DO NOTHING;

UPDATE notas AS n
SET turma_id = a.turma_id
FROM alunos AS a
WHERE n.aluno_matricula = a.matricula
  AND n.turma_id IS NULL;

ALTER TABLE notas
DROP CONSTRAINT IF EXISTS notas_aluno_matricula_materia_id_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'notas_aluno_turma_materia_key'
    ) THEN
        ALTER TABLE notas
        ADD CONSTRAINT notas_aluno_turma_materia_key
        UNIQUE (aluno_matricula, turma_id, materia_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM notas WHERE turma_id IS NULL) THEN
        ALTER TABLE notas ALTER COLUMN turma_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_aluno_turmas_turma
ON aluno_turmas (turma_id);

CREATE INDEX IF NOT EXISTS idx_notas_aluno_turma
ON notas (aluno_matricula, turma_id);
