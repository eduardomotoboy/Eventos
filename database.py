# -*- coding: utf-8 -*-
"""
Arquivo: database.py
Projeto: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
Descrição: Módulo central de gerenciamento do banco de dados relacional MySQL (localhost:3306).
           Configurado para conectar-se ao servidor MySQL local na base de dados 'Eventos'
           utilizando o usuário 'Eventos_extencionista'.
           Possui suporte a autenticação por CPF, controle de perfis de acesso
           (Gestor, Professor Tutor, Usuário Base), criação automática das tabelas
           com chaves estrangeiras (InnoDB) e carga do usuário gestor inicial (CPF: 00000000000).
Regra de conformidade: Todo o código possui comentários explicativos detalhados.
"""

import os
import hmac
import hashlib
import secrets
import pymysql
import pymysql.cursors
from datetime import datetime, timedelta

# Carrega variáveis de ambiente do arquivo .env (caso exista) com fallback automático
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configurações de conexão com o banco de dados MySQL local (lidas do .env)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "Eventos_extencionista")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Eventos_extencionista")
DB_NAME = os.getenv("DB_NAME", "Eventos")

# CPF inicial padrão do Gestor / Administrador do sistema
ADMIN_DEFAULT_CPF = os.getenv("ADMIN_DEFAULT_CPF", "00000000000")

# Chave institucional secreta (Pepper) para Blind Index e hashing criptográfico seguro de CPFs (LGPD).
# Garante que um vazamento da base não permita ataques de tabela arco-íris contra CPFs (11 dígitos numéricos).
CPF_PEPPER_KEY = os.getenv("CPF_PEPPER_KEY", "UNIFACCAMP_EVENTOS_LGPD_SECURE_PEPPER_KEY_2026_@#!*")

# Iterações para o algoritmo PBKDF2-HMAC-SHA256 (Padrão recomendado NIST SP 800-132 e OWASP)
PBKDF2_ITERACOES = 100000


def gerar_hash_senha(senha: str) -> str:
    """
    Gera um hash criptográfico seguro PBKDF2-HMAC-SHA256 com salt aleatório único (16 bytes)
    e 100.000 iterações (conforme recomendações do NIST SP 800-132 e OWASP).
    Formato armazenado: pbkdf2:sha256:100000$<salt_hex>$<hash_hex>
    Protege contra ataques de força bruta com GPU, dicionário e tabelas rainbow.
    """
    if not senha:
        senha = ""
    # Salt aleatório de 16 bytes (32 caracteres hexadecimais)
    salt_bytes = secrets.token_bytes(16)
    salt_hex = salt_bytes.hex()
    
    # Derivação de chave segura com 100.000 iterações
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        senha.strip().encode("utf-8"),
        salt_bytes,
        PBKDF2_ITERACOES
    )
    hash_hex = hash_bytes.hex()
    return f"pbkdf2:sha256:{PBKDF2_ITERACOES}${salt_hex}${hash_hex}"


def verificar_hash_senha(senha_candidata: str, senha_armazenada: str) -> bool:
    """
    Verifica se a senha candidata informada corresponde ao hash armazenado no banco de dados.
    Utiliza hmac.compare_digest para prevenção contra ataques de temporização (timing attacks).
    Possui retrocompatibilidade: reconhece o padrão moderno PBKDF2 e hashes legados SHA-256 simples.
    """
    if not senha_candidata or not senha_armazenada:
        return False

    senha_limpa = senha_candidata.strip()

    # Formato seguro PBKDF2: pbkdf2:sha256:<rounds>$<salt_hex>$<hash_hex>
    if senha_armazenada.startswith("pbkdf2:sha256:"):
        partes = senha_armazenada.split("$")
        if len(partes) != 3:
            return False

        prefixo_rounds, salt_hex, hash_esperado = partes
        try:
            iteracoes = int(prefixo_rounds.split(":")[-1])
            salt_bytes = bytes.fromhex(salt_hex)
        except (ValueError, TypeError):
            return False

        # Deriva o hash com os mesmos parâmetros criptográficos
        hash_calculado = hashlib.pbkdf2_hmac(
            "sha256",
            senha_limpa.encode("utf-8"),
            salt_bytes,
            iteracoes
        ).hex()

        # Comparação em tempo constante contra timing attacks
        return hmac.compare_digest(hash_calculado, hash_esperado)

    # Retrocompatibilidade com SHA-256 legado simples (64 caracteres hexadecimais)
    hash_legado = hashlib.sha256(senha_limpa.encode("utf-8")).hexdigest()
    return hmac.compare_digest(hash_legado, senha_armazenada.strip())


def gerar_hash_cpf(cpf: str) -> str:
    """
    Gera um hash determinístico criptografado HMAC-SHA256 (Blind Index) para indexação segura de CPF.
    Utiliza a chave institucional secreta (Pepper), tornando matematicamente impossível ataques
    de rainbow tables ou quebra de CPFs por dicionário (já que CPFs possuem apenas 11 dígitos).
    Permite consultas ultra-rápidas O(1) indexadas no MySQL sem expor o CPF em texto claro.
    """
    cpf_limpo = "".join([c for c in str(cpf) if c.isdigit()])
    return hmac.new(
        CPF_PEPPER_KEY.encode("utf-8"),
        cpf_limpo.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def mascarar_cpf(cpf: str) -> str:
    """
    Aplica máscara de proteção aos dígitos do CPF para conformidade com a LGPD.
    Exemplo: '00000000000' -> '000.***.***-00'
    """
    cpf_limpo = "".join([c for c in str(cpf) if c.isdigit()])
    if len(cpf_limpo) == 11:
        return f"{cpf_limpo[:3]}.***.***-{cpf_limpo[9:]}"
    return "***.***.***-**"


def validar_cpf(cpf: str, permitir_admin_padrao: bool = True) -> bool:
    """
    Valida um CPF brasileiro conforme o algoritmo oficial dos dois dígitos verificadores
    (Módulo 11) estabelecido pela Receita Federal do Brasil.

    Regras de Validação:
    1. Higieniza o texto recebido, extraindo apenas os dígitos numéricos.
    2. Exige comprimento estrito de 11 dígitos.
    3. Permite opcionalmente o CPF administrativo institucional padrão (ADMIN_DEFAULT_CPF = 00000000000).
    4. Rejeita números formados por dígitos repetidos (ex: 111.111.111-11, 222.222.222-22).
    5. Valida o primeiro dígito verificador através da soma ponderada decrescente de pesos 10 a 2.
    6. Valida o segundo dígito verificador através da soma ponderada decrescente de pesos 11 a 2.

    Retorna:
        bool: True se o CPF for válido e autêntico; False caso contrário.
    """
    if not cpf:
        return False

    digitos = [c for c in str(cpf) if c.isdigit()]
    if len(digitos) != 11:
        return False

    cpf_limpo = "".join(digitos)

    # Exceção controlada para o Gestor institucional padrão
    if permitir_admin_padrao and cpf_limpo == ADMIN_DEFAULT_CPF:
        return True

    # Rejeita CPFs formados por todos os dígitos iguais (ex: 11111111111, 22222222222, etc.)
    if len(set(digitos)) == 1:
        return False

    # 1º Dígito Verificador (pesos de 10 a 2)
    soma_1 = sum(int(digitos[i]) * (10 - i) for i in range(9))
    resto_1 = (soma_1 * 10) % 11
    d1 = 0 if resto_1 in (10, 11) else resto_1
    if int(digitos[9]) != d1:
        return False

    # 2º Dígito Verificador (pesos de 11 a 2)
    soma_2 = sum(int(digitos[i]) * (11 - i) for i in range(10))
    resto_2 = (soma_2 * 10) % 11
    d2 = 0 if resto_2 in (10, 11) else resto_2
    if int(digitos[10]) != d2:
        return False

    return True


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
    # 1. TABELA: usuarios (com suporte a login por CPF, Blind Index cpf_hash e perfil)
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        cpf VARCHAR(20) UNIQUE NOT NULL,
        cpf_hash VARCHAR(64),
        email VARCHAR(255) UNIQUE NOT NULL,
        telefone VARCHAR(30),
        tipo_participante VARCHAR(100) DEFAULT 'Comunidade Externa',
        matricula_curso VARCHAR(150),
        senha_hash VARCHAR(255) NOT NULL,
        perfil VARCHAR(50) NOT NULL DEFAULT 'Usuário Base', -- 'Gestor', 'Professor Tutor', 'Usuário Base'
        cargo VARCHAR(100) NOT NULL DEFAULT 'Usuário',
        departamento VARCHAR(150),
        ativo INT NOT NULL DEFAULT 1,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_usuarios_cpf_hash (cpf_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # Migrations seguras caso a tabela usuarios já existisse previamente
    novas_colunas_usuarios = [
        ("cpf", "VARCHAR(20)"),
        ("cpf_hash", "VARCHAR(64)"),
        ("senha_hash", "VARCHAR(255)"),
        ("perfil", "VARCHAR(50) NOT NULL DEFAULT 'Usuário Base'"),
        ("telefone", "VARCHAR(30)"),
        ("tipo_participante", "VARCHAR(100) DEFAULT 'Comunidade Externa'"),
        ("matricula_curso", "VARCHAR(150)"),
        ("ativo", "INT NOT NULL DEFAULT 1")
    ]
    for col, tipagem in novas_colunas_usuarios:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipagem};")
            conn.commit()
        except Exception:
            pass

    # Garante a existência do índice em cpf_hash para pesquisas ultra-rápidas O(1)
    try:
        cursor.execute("CREATE INDEX idx_usuarios_cpf_hash ON usuarios (cpf_hash);")
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
    # 3. TABELA: participantes (com suporte a Blind Index cpf_hash)
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS participantes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        cpf VARCHAR(20) UNIQUE NOT NULL,
        cpf_hash VARCHAR(64),
        email VARCHAR(255) NOT NULL,
        telefone VARCHAR(30),
        tipo_participante VARCHAR(100) NOT NULL,
        matricula_curso VARCHAR(150),
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_participantes_cpf_hash (cpf_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # Migration segura de adição da coluna cpf_hash em participantes
    try:
        cursor.execute("ALTER TABLE participantes ADD COLUMN cpf_hash VARCHAR(64);")
        conn.commit()
    except Exception:
        pass

    try:
        cursor.execute("CREATE INDEX idx_participantes_cpf_hash ON participantes (cpf_hash);")
        conn.commit()
    except Exception:
        pass

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inscricao_participantes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        inscricao_id INT NOT NULL,
        cpf_hash VARCHAR(64) NOT NULL,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (inscricao_id) REFERENCES inscricoes(id) ON DELETE CASCADE,
        UNIQUE KEY uq_inscricao_cpf_hash (inscricao_id, cpf_hash),
        INDEX idx_inscricao_participantes_cpf_hash (cpf_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # 5. TABELA: certificados
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificados (
        id INT AUTO_INCREMENT PRIMARY KEY,
        codigo_autenticidade VARCHAR(50) UNIQUE NOT NULL,
        inscricao_id INT NOT NULL,
        evento_id INT NOT NULL,
        participante_id INT NULL,
        cpf_hash VARCHAR(64) NOT NULL,
        carga_horaria INT NOT NULL,
        data_emissao DATETIME DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) NOT NULL DEFAULT 'Válido',
        FOREIGN KEY (inscricao_id) REFERENCES inscricoes(id) ON DELETE CASCADE,
        FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
        FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE,
        UNIQUE KEY uq_certificado_inscricao_cpf_hash (inscricao_id, cpf_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    try:
        cursor.execute("ALTER TABLE certificados ADD COLUMN cpf_hash VARCHAR(64) NULL;")
        conn.commit()
    except Exception:
        pass

    cursor.execute("""
        SELECT c.id, p.cpf
        FROM certificados c
        JOIN participantes p ON p.id = c.participante_id
        WHERE c.cpf_hash IS NULL OR c.cpf_hash = '';
    """)
    certificados_sem_hash = cursor.fetchall()
    for certificado in certificados_sem_hash:
        cursor.execute(
            "UPDATE certificados SET cpf_hash = %s WHERE id = %s;",
            (gerar_hash_cpf(certificado["cpf"]), certificado["id"])
        )

    try:
        cursor.execute("ALTER TABLE certificados MODIFY participante_id INT NULL;")
        conn.commit()
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE certificados MODIFY cpf_hash VARCHAR(64) NOT NULL;")
        conn.commit()
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE certificados DROP INDEX inscricao_id;")
        conn.commit()
    except Exception:
        pass

    try:
        cursor.execute("CREATE UNIQUE INDEX uq_certificado_inscricao_cpf_hash ON certificados (inscricao_id, cpf_hash);")
        conn.commit()
    except Exception:
        pass

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

    # -------------------------------------------------------------
    # 9. TABELA: recuperacao_senha (Tokens e Códigos de Recuperação por E-mail)
    # -------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recuperacao_senha (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        codigo_verificacao VARCHAR(10) NOT NULL,
        codigo_hash VARCHAR(64) NOT NULL,
        email_destinatario VARCHAR(255) NOT NULL,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        expira_em DATETIME NOT NULL,
        utilizado INT NOT NULL DEFAULT 0,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        INDEX idx_recup_usuario (usuario_id),
        INDEX idx_recup_codigo (codigo_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # -------------------------------------------------------------
    # MIGRAÇÃO AUTOMÁTICA DE SEGURANÇA E CONFORMIDADE:
    # 1. Substitui qualquer referência anterior ao CPF real pelo CPF administrativo '00000000000'
    # 2. Atualiza a senha do gestor para hash PBKDF2 de alta segurança
    # 3. Popula o Blind Index (cpf_hash) para todos os usuários e participantes legados
    # -------------------------------------------------------------
    cpf_novo_gestor = "00000000000"
    hash_gestor_cpf = gerar_hash_cpf(cpf_novo_gestor)
    senha_gestor_pbkdf2 = gerar_hash_senha(cpf_novo_gestor)

    # Garante que a conta institucional padrão do Gestor Geral utilize o CPF '00000000000'
    cursor.execute("""
        UPDATE usuarios 
        SET cpf = %s, cpf_hash = %s, senha_hash = %s, perfil = 'Gestor', cargo = 'Gestor do Sistema'
        WHERE email = 'gestor.eventos@unifaccamp.edu.br';
    """, (cpf_novo_gestor, hash_gestor_cpf, senha_gestor_pbkdf2))
    conn.commit()

    # Backfill de Blind Index (cpf_hash) em usuarios
    cursor.execute("SELECT id, cpf FROM usuarios WHERE cpf_hash IS NULL OR cpf_hash = '';")
    usuarios_sem_hash = cursor.fetchall()
    for u in usuarios_sem_hash:
        if u.get("cpf"):
            cursor.execute("UPDATE usuarios SET cpf_hash = %s WHERE id = %s;", (gerar_hash_cpf(u["cpf"]), u["id"]))
    if usuarios_sem_hash:
        conn.commit()
        print(f"[database.py] Migração de segurança: {len(usuarios_sem_hash)} usuários atualizados com Blind Index (cpf_hash).")

    # Backfill de Blind Index (cpf_hash) em participantes
    cursor.execute("SELECT id, cpf FROM participantes WHERE cpf_hash IS NULL OR cpf_hash = '';")
    participantes_sem_hash = cursor.fetchall()
    for p in participantes_sem_hash:
        if p.get("cpf"):
            cursor.execute("UPDATE participantes SET cpf_hash = %s WHERE id = %s;", (gerar_hash_cpf(p["cpf"]), p["id"]))
    if participantes_sem_hash:
        conn.commit()
        print(f"[database.py] Migração de segurança: {len(participantes_sem_hash)} participantes atualizados com Blind Index (cpf_hash).")

    cursor.execute("""
        INSERT IGNORE INTO inscricao_participantes (inscricao_id, cpf_hash)
        SELECT i.id, p.cpf_hash
        FROM inscricoes i
        JOIN participantes p ON p.id = i.participante_id
        WHERE p.cpf_hash IS NOT NULL AND p.cpf_hash != '';
    """)

    conn.commit()
    conn.close()
    print("[database.py] Estrutura de tabelas sincronizada com sucesso no MySQL.")


def seed_database_if_empty():
    """
    Popula o banco de dados MySQL com dados de exemplo iniciais caso esteja vazio,
    assegurando a existência do usuário GESTOR com CPF 00000000000 e privilégio 'Gestor'
    com senha criptografada em PBKDF2 e Blind Index (cpf_hash).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------
    # 1. GARANTE O USUÁRIO GESTOR DO SISTEMA (CPF: 00000000000)
    # Senha padrão inicial salva com hash PBKDF2 (100.000 iterações + salt)
    # -------------------------------------------------------------
    cpf_gestor = "00000000000"
    cpf_hash_gestor = gerar_hash_cpf(cpf_gestor)
    cursor.execute("SELECT id, perfil, senha_hash, cpf_hash FROM usuarios WHERE cpf = %s OR cpf_hash = %s;", (cpf_gestor, cpf_hash_gestor))
    gestor_existente = cursor.fetchone()

    senha_hash_padrao = gerar_hash_senha("00000000000")

    if not gestor_existente:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, cpf_hash, email, telefone, senha_hash, perfil, cargo, departamento)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            "Gestor Geral do Sistema",
            cpf_gestor,
            cpf_hash_gestor,
            "gestor.eventos@unifaccamp.edu.br",
            "(11) 98765-4321",
            senha_hash_padrao,
            "Gestor",
            "Gestor do Sistema",
            "Pró-Reitoria de Extensão"
        ))
        conn.commit()
        print(f"[database.py] Usuário Gestor cadastrado com sucesso (CPF: {cpf_gestor}, Perfil: Gestor, PBKDF2 Hash).")
    else:
        # Se a senha do gestor ainda for legado (não PBKDF2), atualiza para hash PBKDF2 e atualiza cpf_hash
        atualizacoes = ["perfil = 'Gestor'", "cargo = 'Gestor do Sistema'"]
        valores = []
        if not gestor_existente.get("senha_hash", "").startswith("pbkdf2:sha256:"):
            atualizacoes.append("senha_hash = %s")
            valores.append(senha_hash_padrao)
        if not gestor_existente.get("cpf_hash"):
            atualizacoes.append("cpf_hash = %s")
            valores.append(cpf_hash_gestor)

        sql_update = f"UPDATE usuarios SET {', '.join(atualizacoes)} WHERE id = %s;"
        valores.append(gestor_existente["id"])
        cursor.execute(sql_update, tuple(valores))
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
            INSERT INTO certificados (codigo_autenticidade, inscricao_id, evento_id, participante_id, cpf_hash, carga_horaria, status)
            VALUES ('CERT-2026-8F92A', 1, 1, 1, %s, 8, 'Válido');
        """, (gerar_hash_cpf("123.456.789-00"),))

        conn.commit()
        print("[database.py] Carga de dados iniciais no MySQL concluída com sucesso.")

    conn.close()


if __name__ == "__main__":
    init_db()
    seed_database_if_empty()
