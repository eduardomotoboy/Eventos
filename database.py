# -*- coding: utf-8 -*-
"""
Arquivo: database.py
Projeto: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
Descrição: Módulo central de gerenciamento do banco de dados relacional MySQL (localhost:3306).
           Configurado para conectar-se ao servidor MySQL local na base de dados 'Eventos'
           utilizando o usuário 'Eventos_extencionista'.
           Possui suporte a autenticação por CPF, controle de perfis de acesso
           (Gestor, Professor Tutor, Usuário Base), criação automática das tabelas
           com chaves estrangeiras (InnoDB) e carga do usuário gestor inicial (CPF: 29156413823).
Regra de conformidade: Todo o código possui comentários explicativos detalhados.
"""

import os
import hashlib
import pymysql
import pymysql.cursors
from datetime import datetime

# Configurações de conexão com o banco de dados MySQL local
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "Eventos_extencionista")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Eventos_extencionista")
DB_NAME = os.getenv("DB_NAME", "Eventos")


def gerar_hash_senha(senha: str) -> str:
    """
    Gera um hash SHA-256 seguro para armazenamento de senhas de usuários.
    """
    return hashlib.sha256(senha.strip().encode("utf-8")).hexdigest()


def get_db_connection():
    """
    Cria e retorna uma conexão ativa com o servidor MySQL local.
    Utiliza DictCursor para que as colunas possam ser acessadas por nome (linha['nome']).
    """
    conexao = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return conexao


def init_db():
    """
    Inicializa e atualiza a estrutura de tabelas no banco MySQL 'Eventos':
    1. usuarios: Atores do sistema com login por CPF, senha criptografada e perfis de privilégio.
    2. eventos: Catálogo de cursos, eventos e Amostras de Trabalhos.
    3. participantes: Dados cadastrais dos inscritos.
    4. inscricoes: Controle de vagas, QR Code, presenças e notas homologadas.
    5. certificados: Registro de certificados emitidos para validação pública.
    6. tutores: Professores avaliadores designados para bancas da Amostra.
    7. banca_tutores: Vínculo entre tutores e trabalhos da Amostra.
    8. avaliacoes_apresentacao: Notas detalhadas e pareceres técnicos dos tutores.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------
    # 1. TABELA: usuarios (com suporte a login por CPF, senha e perfil)
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        cpf VARCHAR(20) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        telefone VARCHAR(30),
        senha_hash VARCHAR(255) NOT NULL,
        perfil VARCHAR(50) NOT NULL DEFAULT 'Usuário Base', -- 'Gestor', 'Professor Tutor', 'Usuário Base'
        cargo VARCHAR(100) NOT NULL DEFAULT 'Usuário',
        departamento VARCHAR(150),
        ativo INT NOT NULL DEFAULT 1,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # Migrations seguras caso a tabela usuarios já existisse previamente
    novas_colunas_usuarios = [
        ("cpf", "VARCHAR(20)"),
        ("senha_hash", "VARCHAR(255)"),
        ("perfil", "VARCHAR(50) NOT NULL DEFAULT 'Usuário Base'"),
        ("telefone", "VARCHAR(30)"),
        ("ativo", "INT NOT NULL DEFAULT 1")
    ]
    for col, tipagem in novas_colunas_usuarios:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipagem};")
            conn.commit()
        except Exception:
            pass

    # -------------------------------------------------------------
    # 2. TABELA: eventos
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eventos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        titulo VARCHAR(255) NOT NULL,
        descricao TEXT NOT NULL,
        categoria VARCHAR(100) NOT NULL,
        tipo_evento VARCHAR(50) NOT NULL DEFAULT 'Geral',
        permite_apresentacao INT NOT NULL DEFAULT 0,
        qtd_tutores_por_trabalho INT NOT NULL DEFAULT 2,
        status_notas VARCHAR(50) NOT NULL DEFAULT 'Em Avaliação',
        modalidade VARCHAR(50) NOT NULL,
        local_link VARCHAR(255) NOT NULL,
        data_inicio VARCHAR(50) NOT NULL,
        data_fim VARCHAR(50) NOT NULL,
        carga_horaria INT NOT NULL,
        vagas_totais INT NOT NULL,
        palestrante VARCHAR(255) NOT NULL,
        organizador_id INT,
        status VARCHAR(50) NOT NULL DEFAULT 'Inscrições Abertas',
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (organizador_id) REFERENCES usuarios(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # 3. TABELA: participantes
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS participantes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        cpf VARCHAR(20) UNIQUE NOT NULL,
        email VARCHAR(255) NOT NULL,
        telefone VARCHAR(30),
        tipo_participante VARCHAR(100) NOT NULL,
        matricula_curso VARCHAR(150),
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # 4. TABELA: inscricoes
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inscricoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        codigo_inscricao VARCHAR(50) UNIQUE NOT NULL,
        evento_id INT NOT NULL,
        participante_id INT NOT NULL,
        tipo_participacao VARCHAR(50) NOT NULL DEFAULT 'Ouvinte',
        titulo_trabalho VARCHAR(255),
        resumo_trabalho TEXT,
        area_trabalho VARCHAR(100),
        autores VARCHAR(255),
        nota_final DECIMAL(4,2),
        notas_homologadas INT NOT NULL DEFAULT 0,
        data_homologacao DATETIME,
        status VARCHAR(50) NOT NULL DEFAULT 'Confirmada',
        data_inscricao DATETIME DEFAULT CURRENT_TIMESTAMP,
        data_checkin DATETIME,
        observacoes TEXT,
        FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
        FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE,
        UNIQUE KEY uq_evento_participante (evento_id, participante_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # 5. TABELA: certificados
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificados (
        id INT AUTO_INCREMENT PRIMARY KEY,
        codigo_autenticidade VARCHAR(50) UNIQUE NOT NULL,
        inscricao_id INT UNIQUE NOT NULL,
        evento_id INT NOT NULL,
        participante_id INT NOT NULL,
        carga_horaria INT NOT NULL,
        data_emissao DATETIME DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) NOT NULL DEFAULT 'Válido',
        FOREIGN KEY (inscricao_id) REFERENCES inscricoes(id) ON DELETE CASCADE,
        FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
        FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # 6. TABELA: tutores
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tutores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        departamento VARCHAR(150),
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # 7. TABELA: banca_tutores
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS banca_tutores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        evento_id INT NOT NULL,
        inscricao_id INT NOT NULL,
        tutor_id INT NOT NULL,
        status_avaliacao VARCHAR(50) NOT NULL DEFAULT 'Pendente',
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
        FOREIGN KEY (inscricao_id) REFERENCES inscricoes(id) ON DELETE CASCADE,
        FOREIGN KEY (tutor_id) REFERENCES tutores(id) ON DELETE CASCADE,
        UNIQUE KEY uq_banca_inscricao_tutor (inscricao_id, tutor_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # 8. TABELA: avaliacoes_apresentacao
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes_apresentacao (
        id INT AUTO_INCREMENT PRIMARY KEY,
        banca_id INT NOT NULL,
        inscricao_id INT NOT NULL,
        tutor_id INT NOT NULL,
        nota_dominio DECIMAL(4,2) NOT NULL,
        nota_clareza DECIMAL(4,2) NOT NULL,
        nota_relevancia DECIMAL(4,2) NOT NULL,
        nota_media DECIMAL(4,2) NOT NULL,
        comentarios TEXT,
        data_avaliacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (banca_id) REFERENCES banca_tutores(id) ON DELETE CASCADE,
        FOREIGN KEY (inscricao_id) REFERENCES inscricoes(id) ON DELETE CASCADE,
        FOREIGN KEY (tutor_id) REFERENCES tutores(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    conn.commit()
    conn.close()
    print("[database.py] Estrutura de tabelas sincronizada com sucesso no MySQL.")


def seed_database_if_empty():
    """
    Popula o banco de dados MySQL com dados de exemplo iniciais caso esteja vazio,
    assegurando a existência do usuário GESTOR com CPF 29156413823 e privilégio 'Gestor'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------
    # 1. GARANTE O USUÁRIO GESTOR DO SISTEMA (CPF: 29156413823)
    # Senha padrão inicial definida como: 29156413823 (o próprio CPF) ou Eventos@2026
    # -------------------------------------------------------------
    cpf_gestor = "29156413823"
    cursor.execute("SELECT id, perfil FROM usuarios WHERE cpf = %s;", (cpf_gestor,))
    gestor_existente = cursor.fetchone()

    senha_hash_padrao = gerar_hash_senha("29156413823")

    if not gestor_existente:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, email, telefone, senha_hash, perfil, cargo, departamento)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            "Gestor Geral do Sistema",
            cpf_gestor,
            "gestor.eventos@unifaccamp.edu.br",
            "(11) 98765-4321",
            senha_hash_padrao,
            "Gestor",
            "Gestor do Sistema",
            "Pró-Reitoria de Extensão"
        ))
        conn.commit()
        print(f"[database.py] Usuário Gestor cadastrado com sucesso (CPF: {cpf_gestor}, Perfil: Gestor).")
    else:
        # Assegura que o perfil seja 'Gestor'
        cursor.execute("""
            UPDATE usuarios SET perfil = 'Gestor', cargo = 'Gestor do Sistema' WHERE cpf = %s;
        """, (cpf_gestor,))
        conn.commit()

    # -------------------------------------------------------------
    # 2. SEED DE DADOS COMPLEMENTARES CASO A BASE ESTEJA NOVA
    # -------------------------------------------------------------
    cursor.execute("SELECT COUNT(*) AS total FROM eventos;")
    resultado = cursor.fetchone()
    total_eventos = resultado["total"] if resultado else 0

    if total_eventos == 0:
        print("[database.py] Populando banco de dados MySQL com registros iniciais de demonstração...")

        # Inserção de Professores Tutores
        tutores_iniciais = [
            ("Prof. Dr. Ricardo Silva", "ricardo.silva@unifaccamp.edu.br", "Ciência da Computação"),
            ("Profa. Dra. Elaine Cristina", "elaine.cristina@unifaccamp.edu.br", "Sistemas de Informação"),
            ("Prof. Me. Fernando Duarte", "fernando.duarte@unifaccamp.edu.br", "Engenharia de Software")
        ]
        cursor.executemany("INSERT INTO tutores (nome, email, departamento) VALUES (%s, %s, %s);", tutores_iniciais)

        # Inserção de Eventos e Amostra Acadêmica
        eventos_iniciais = [
            (
                "III Mostra de Projetos Extensionistas UNIFACCAMP",
                "Apresentação e avaliação dos trabalhos e projetos extensionistas desenvolvidos pela comunidade acadêmica no semestre 2026.2. Alunos apresentam em banners para bancas de professores tutores.",
                "Mostra Acadêmica",
                "Amostra", 1, 2, "Em Avaliação", "Presencial",
                "Ginásio Poliesportivo do Campus UNIFACCAMP - Campo Limpo Paulista",
                "2026-10-15 08:30", "2026-10-15 18:00", 8, 250,
                "Banca Examinadora de Professores e Convidados", 1, "Inscrições Abertas"
            ),
            (
                "Workshop de Inteligência Artificial e Agentes Autônomos",
                "Oficina prática sobre arquitetura de agentes, modelos generativos e automação inteligente no ecossistema Python.",
                "Workshop", "Geral", 0, 0, "Em Avaliação", "Híbrido",
                "Laboratório de Informática 3 e Transmissão via Google Meet",
                "2026-10-22 19:15", "2026-10-22 22:30", 4, 60,
                "Prof. Dr. Marcos Silveira", 1, "Inscrições Abertas"
            ),
            (
                "Curso de Extensão: Desenvolvimento Web Responsivo e Acessível",
                "Capacitação aberta para estudantes e comunidade externa abordando CSS Grid moderno, acessibilidade digital e boas práticas W3C.",
                "Curso de Extensão", "Geral", 0, 0, "Em Avaliação", "Online",
                "Plataforma EAD UNIFACCAMP",
                "2026-11-05 14:00", "2026-11-26 18:00", 20, 100,
                "Profa. Ma. Juliana Mendes", 1, "Inscrições Abertas"
            )
        ]
        cursor.executemany("""
            INSERT INTO eventos (titulo, descricao, categoria, tipo_evento, permite_apresentacao,
                                qtd_tutores_por_trabalho, status_notas, modalidade, local_link, 
                                data_inicio, data_fim, carga_horaria, vagas_totais, 
                                palestrante, organizador_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, eventos_iniciais)

        # Inserção de Participantes
        participantes_iniciais = [
            ("Eduardo Santos de Oliveira", "123.456.789-00", "eduardo.santos@aluno.unifaccamp.edu.br", "(11) 98765-4321", "Aluno UNIFACCAMP", "ADS - Noturno"),
            ("Mariana Costa Almeida", "234.567.890-11", "mariana.costa@aluno.unifaccamp.edu.br", "(11) 97654-3210", "Aluno UNIFACCAMP", "Engenharia de Software")
        ]
        cursor.executemany("""
            INSERT INTO participantes (nome, cpf, email, telefone, tipo_participante, matricula_curso)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, participantes_iniciais)

        # Inserção de Apresentações
        cursor.execute("""
            INSERT INTO inscricoes (
                codigo_inscricao, evento_id, participante_id, tipo_participacao,
                titulo_trabalho, resumo_trabalho, area_trabalho, autores,
                nota_final, notas_homologadas, data_homologacao, status
            ) VALUES (
                'INS-2026-A101', 1, 1, 'Apresentador',
                'Sistema Web para Gestão de Resíduos Comunitários com Responsive CSS Grid',
                'Protótipo funcional extensionista aplicando CSS Grid e banco de dados relacional MySQL.',
                'Tecnologia e Sustentabilidade', 'Eduardo Santos, Mariana Costa',
                4.80, 1, CURRENT_TIMESTAMP, 'Presente'
            );
        """)

        cursor.execute("""
            INSERT INTO banca_tutores (evento_id, inscricao_id, tutor_id, status_avaliacao)
            VALUES (1, 1, 1, 'Avaliado'), (1, 1, 2, 'Avaliado');
        """)

        cursor.execute("""
            INSERT INTO avaliacoes_apresentacao (
                banca_id, inscricao_id, tutor_id, nota_dominio, nota_clareza, nota_relevancia, nota_media, comentarios
            ) VALUES 
            (1, 1, 1, 5.0, 4.5, 5.0, 4.83, 'Excelente domínio do tema e aplicação prática de grande relevância.'),
            (2, 1, 2, 4.5, 5.0, 4.8, 4.77, 'Apresentação oral muito clara e protótipo responsivo impecável.');
        """)

        cursor.execute("""
            INSERT INTO certificados (codigo_autenticidade, inscricao_id, evento_id, participante_id, carga_horaria, status)
            VALUES ('CERT-2026-8F92A', 1, 1, 1, 8, 'Válido');
        """)

        conn.commit()
        print("[database.py] Carga de dados iniciais no MySQL concluída com sucesso.")

    conn.close()


if __name__ == "__main__":
    init_db()
    seed_database_if_empty()
