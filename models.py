# -*- coding: utf-8 -*-
"""
Arquivo: models.py
Projeto: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
Descrição: Camada de acesso a dados (DAO / Services) e lógica de negócio com suporte total ao MySQL.
           Utiliza parametrização segura padrão MySQL (%s) para proteção contra SQL Injection
           e DictCursor para acesso direto por chaves de dicionário.
           Funcionalidades completas:
           - Geração de QR Code Base64 para credenciamento instantâneo.
           - Gestão de Eventos do tipo 'Amostra' (Mostra de Trabalhos Acadêmicos).
           - Designação de Professores Tutores e quantidades configuradas pelo criador.
           - Lançamento de notas pelos tutores via webapp (critérios e feedback).
           - Validação e Homologação final das notas pelo criador do evento antes
             da disponibilização online para os alunos.
           - Scanner de QR Code para busca de projetos e registro de presença (Check-in).
           - Emissão e validação pública de certificados digitais.
Regra de conformidade: Todo o código possui comentários explicativos detalhados.
"""

import os
import uuid
import hashlib
import secrets
import io
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import qrcode
from database import (
    get_db_connection,
    gerar_hash_senha,
    verificar_hash_senha,
    gerar_hash_cpf,
    mascarar_cpf,
    validar_cpf
)


class QRCodeHelper:
    """
    Classe utilitária para geração de QR Codes alfanuméricos em formato Base64.
    Permite embutir a imagem diretamente nos templates HTML sem gerar arquivos temporários.
    """

    @staticmethod
    def gerar_qr_base64(conteudo: str) -> str:
        """
        Gera uma imagem de QR Code a partir de uma string (código de inscrição)
        e a converte em uma string Base64 utilizável na tag <img src="data:image/png;base64,...">.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(conteudo)
        qr.make(fit=True)

        imagem = qr.make_image(fill_color="#0f3460", back_color="#ffffff")
        buffer = io.BytesIO()
        imagem.save(buffer, format="PNG")
        imagem_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{imagem_b64}"


class EventoService:
    """
    Serviço responsável pelas operações de negócio relacionadas a Eventos e Cursos de Extensão no MySQL.
    """

    @staticmethod
    def listar_todos(filtro_categoria=None, filtro_status=None, termo_busca=None):
        """
        Retorna a lista de eventos cadastrados com suporte a filtros e busca por texto no MySQL.
        Calcula dinamicamente a quantidade de vagas ocupadas e disponíveis para cada evento.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                e.id, e.titulo, e.descricao, e.categoria, e.tipo_evento, e.permite_apresentacao,
                e.qtd_tutores_por_trabalho, e.status_notas, e.modalidade, e.local_link,
                e.data_inicio, e.data_fim, e.carga_horaria, e.vagas_totais, e.palestrante,
                e.status, e.criado_em,
                u.nome AS organizador_nome,
                COUNT(CASE WHEN i.status != 'Cancelada' THEN i.id END) AS vagas_ocupadas
            FROM eventos e
            LEFT JOIN usuarios u ON e.organizador_id = u.id
            LEFT JOIN inscricoes i ON e.id = i.evento_id
            WHERE 1=1
        """
        parametros = []

        if filtro_categoria:
            sql += " AND e.categoria = %s"
            parametros.append(filtro_categoria)

        if filtro_status:
            sql += " AND e.status = %s"
            parametros.append(filtro_status)

        if termo_busca:
            sql += " AND (e.titulo LIKE %s OR e.descricao LIKE %s OR e.palestrante LIKE %s)"
            termo = f"%{termo_busca}%"
            parametros.extend([termo, termo, termo])

        sql += " GROUP BY e.id ORDER BY e.data_inicio ASC;"

        cursor.execute(sql, tuple(parametros))
        eventos = cursor.fetchall()
        conn.close()
        return eventos

    @staticmethod
    def buscar_por_id(evento_id: int):
        """
        Localiza um evento pelo seu identificador primário único no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                e.id, e.titulo, e.descricao, e.categoria, e.tipo_evento, e.permite_apresentacao,
                e.qtd_tutores_por_trabalho, e.status_notas, e.modalidade, e.local_link,
                e.data_inicio, e.data_fim, e.carga_horaria, e.vagas_totais, e.palestrante,
                e.status, e.organizador_id, e.criado_em,
                u.nome AS organizador_nome,
                COUNT(CASE WHEN i.status != 'Cancelada' THEN i.id END) AS vagas_ocupadas
            FROM eventos e
            LEFT JOIN usuarios u ON e.organizador_id = u.id
            LEFT JOIN inscricoes i ON e.id = i.evento_id
            WHERE e.id = %s
            GROUP BY e.id;
        """
        cursor.execute(sql, (evento_id,))
        evento = cursor.fetchone()
        conn.close()
        return evento

    @staticmethod
    def criar_evento(dados: dict):
        """
        Cadastra um novo evento ou curso de extensão no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        tipo_evento = "Amostra" if dados.get("permite_apresentacao") in [1, "1", True, "true"] else "Geral"
        permite_apresentacao = 1 if tipo_evento == "Amostra" else 0
        qtd_tutores = int(dados.get("qtd_tutores_por_trabalho", 2))

        sql = """
            INSERT INTO eventos (
                titulo, descricao, categoria, tipo_evento, permite_apresentacao,
                qtd_tutores_por_trabalho, status_notas, modalidade, local_link,
                data_inicio, data_fim, carga_horaria, vagas_totais,
                palestrante, organizador_id, status
            ) VALUES (%s, %s, %s, %s, %s, %s, 'Em Avaliação', %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(sql, (
            dados['titulo'],
            dados['descricao'],
            dados['categoria'],
            tipo_evento,
            permite_apresentacao,
            qtd_tutores,
            dados['modalidade'],
            dados['local_link'],
            dados['data_inicio'],
            dados['data_fim'],
            int(dados['carga_horaria']),
            int(dados['vagas_totais']),
            dados['palestrante'],
            dados.get('organizador_id', 1),
            dados.get('status', 'Inscrições Abertas')
        ))
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return novo_id

    @staticmethod
    def atualizar_evento(evento_id: int, dados: dict):
        """
        Atualiza as informações de um evento existente no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        tipo_evento = "Amostra" if dados.get("permite_apresentacao") in [1, "1", True, "true"] else "Geral"
        permite_apresentacao = 1 if tipo_evento == "Amostra" else 0
        qtd_tutores = int(dados.get("qtd_tutores_por_trabalho", 2))

        sql = """
            UPDATE eventos SET
                titulo = %s, descricao = %s, categoria = %s, tipo_evento = %s, permite_apresentacao = %s,
                qtd_tutores_por_trabalho = %s, modalidade = %s, local_link = %s,
                data_inicio = %s, data_fim = %s, carga_horaria = %s, vagas_totais = %s,
                palestrante = %s, status = %s
            WHERE id = %s;
        """
        cursor.execute(sql, (
            dados['titulo'],
            dados['descricao'],
            dados['categoria'],
            tipo_evento,
            permite_apresentacao,
            qtd_tutores,
            dados['modalidade'],
            dados['local_link'],
            dados['data_inicio'],
            dados['data_fim'],
            int(dados['carga_horaria']),
            int(dados['vagas_totais']),
            dados['palestrante'],
            dados['status'],
            evento_id
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def excluir_evento(evento_id: int):
        """
        Remove um evento do sistema (as inscrições são removidas em cascata pela FK).
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM eventos WHERE id = %s;", (evento_id,))
        conn.commit()
        conn.close()


class InscricaoService:
    """
    Serviço responsável pelas operações de inscrição de participantes no MySQL,
    submissão de trabalhos para eventos de Amostra, credenciamento (check-in)
    e consulta com suporte a QR Code.
    """

    @staticmethod
    def realizar_inscricao(evento_id: int, dados_participante: dict):
        """
        Fluxo de inscrição no MySQL com validações de vagas e duplicidade.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. Validação do evento e vagas
            cursor.execute("""
                SELECT e.vagas_totais, e.status, e.tipo_evento, e.permite_apresentacao,
                       COUNT(CASE WHEN i.status != 'Cancelada' THEN i.id END) AS vagas_ocupadas
                FROM eventos e
                LEFT JOIN inscricoes i ON e.id = i.evento_id
                WHERE e.id = %s
                GROUP BY e.id;
            """, (evento_id,))
            evento = cursor.fetchone()

            if not evento:
                raise ValueError("Evento não encontrado.")

            if evento['status'] != 'Inscrições Abertas':
                raise ValueError(f"As inscrições para este evento estão com status: {evento['status']}.")

            if evento['vagas_ocupadas'] >= evento['vagas_totais']:
                raise ValueError("Desculpe, todas as vagas para este evento já foram preenchidas.")

            # 2. Localizar ou cadastrar o participante (busca por CPF e Blind Index cpf_hash)
            cpf_bruto = dados_participante['cpf'].strip()
            cpf_digitos = "".join([c for c in cpf_bruto if c.isdigit()])
            cpf_hash = gerar_hash_cpf(cpf_digitos) if cpf_digitos else ""

            cursor.execute("""
                SELECT id FROM participantes 
                WHERE (cpf_hash = %s AND %s != '') 
                   OR cpf = %s 
                   OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = %s;
            """, (cpf_hash, cpf_hash, cpf_bruto, cpf_digitos))
            participante = cursor.fetchone()

            if participante:
                participante_id = participante['id']
                cursor.execute("""
                    UPDATE participantes SET
                        nome = %s, email = %s, telefone = %s, tipo_participante = %s, matricula_curso = %s, cpf_hash = %s
                    WHERE id = %s;
                """, (
                    dados_participante['nome'].strip(),
                    dados_participante['email'].strip(),
                    dados_participante.get('telefone', '').strip(),
                    dados_participante['tipo_participante'],
                    dados_participante.get('matricula_curso', '').strip(),
                    cpf_hash,
                    participante_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO participantes (nome, cpf, cpf_hash, email, telefone, tipo_participante, matricula_curso)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (
                    dados_participante['nome'].strip(),
                    cpf_bruto,
                    cpf_hash,
                    dados_participante['email'].strip(),
                    dados_participante.get('telefone', '').strip(),
                    dados_participante['tipo_participante'],
                    dados_participante.get('matricula_curso', '').strip()
                ))
                participante_id = cursor.lastrowid

            # 3. Verifica duplicidade de inscrição
            cursor.execute("""
                SELECT id, codigo_inscricao, status 
                FROM inscricoes 
                WHERE evento_id = %s AND participante_id = %s;
            """, (evento_id, participante_id))
            inscricao_existente = cursor.fetchone()

            tipo_participacao = dados_participante.get("tipo_participacao", "Ouvinte")
            titulo_trabalho = dados_participante.get("titulo_trabalho")
            resumo_trabalho = dados_participante.get("resumo_trabalho")
            area_trabalho = dados_participante.get("area_trabalho")
            autores = dados_participante.get("autores")

            if inscricao_existente:
                if inscricao_existente['status'] == 'Cancelada':
                    codigo = inscricao_existente['codigo_inscricao']
                    cursor.execute("""
                        UPDATE inscricoes SET 
                            status = 'Confirmada',
                            tipo_participacao = %s,
                            titulo_trabalho = %s,
                            resumo_trabalho = %s,
                            area_trabalho = %s,
                            autores = %s,
                            data_inscricao = CURRENT_TIMESTAMP
                        WHERE id = %s;
                    """, (tipo_participacao, titulo_trabalho, resumo_trabalho, area_trabalho, autores, inscricao_existente['id']))
                    conn.commit()
                    return codigo
                else:
                    raise ValueError(f"Este participante já está inscrito neste evento (Código: {inscricao_existente['codigo_inscricao']}).")

            # 4. Código de inscrição único
            sufixo = uuid.uuid4().hex[:6].upper()
            codigo_inscricao = f"INS-2026-{sufixo}"

            # 5. Salva no MySQL
            cursor.execute("""
                INSERT INTO inscricoes (
                    codigo_inscricao, evento_id, participante_id, tipo_participacao,
                    titulo_trabalho, resumo_trabalho, area_trabalho, autores, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Confirmada');
            """, (codigo_inscricao, evento_id, participante_id, tipo_participacao, titulo_trabalho, resumo_trabalho, area_trabalho, autores))

            conn.commit()
            return codigo_inscricao

        finally:
            conn.close()

    @staticmethod
    def buscar_por_codigo(codigo_inscricao: str):
        """
        Retorna os detalhes completos de uma inscrição no MySQL a partir de seu código único.
        Gera o QR Code em Base64.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                i.id AS inscricao_id, i.codigo_inscricao, i.status AS status_inscricao,
                i.tipo_participacao, i.titulo_trabalho, i.resumo_trabalho, i.area_trabalho,
                i.autores, i.nota_final, i.notas_homologadas, i.data_homologacao,
                i.data_inscricao, i.data_checkin,
                e.id AS evento_id, e.titulo AS evento_titulo, e.categoria, e.tipo_evento,
                e.permite_apresentacao, e.modalidade, e.local_link, e.data_inicio, e.data_fim,
                e.carga_horaria, e.palestrante,
                p.id AS participante_id, p.nome AS participante_nome, p.cpf, p.email,
                p.tipo_participante, p.matricula_curso,
                c.codigo_autenticidade AS certificado_codigo
            FROM inscricoes i
            JOIN eventos e ON i.evento_id = e.id
            JOIN participantes p ON i.participante_id = p.id
            LEFT JOIN certificados c ON i.id = c.inscricao_id
            WHERE i.codigo_inscricao = %s;
        """
        cursor.execute(sql, (codigo_inscricao.strip().upper(),))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            dados = dict(resultado)
            dados["qr_code_b64"] = QRCodeHelper.gerar_qr_base64(dados["codigo_inscricao"])
            return dados
        return None

    @staticmethod
    def listar_por_evento(evento_id: int):
        """
        Lista todos os participantes inscritos em um determinado evento no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                i.id AS inscricao_id, i.codigo_inscricao, i.status AS status_inscricao,
                i.tipo_participacao, i.titulo_trabalho, i.resumo_trabalho, i.area_trabalho,
                i.autores, i.nota_final, i.notas_homologadas,
                i.data_inscricao, i.data_checkin,
                p.id AS participante_id, p.nome, p.cpf, p.email, p.telefone,
                p.tipo_participante, p.matricula_curso,
                c.codigo_autenticidade AS certificado_codigo
            FROM inscricoes i
            JOIN participantes p ON i.participante_id = p.id
            LEFT JOIN certificados c ON i.id = c.inscricao_id
            WHERE i.evento_id = %s
            ORDER BY p.nome ASC;
        """
        cursor.execute(sql, (evento_id,))
        inscritos = cursor.fetchall()
        conn.close()
        return inscritos

    @staticmethod
    def listar_por_cpf(cpf: str):
        """
        Consulta todas as inscrições associadas a um CPF fornecido (área Minhas Inscrições) no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                i.id AS inscricao_id, i.codigo_inscricao, i.status AS status_inscricao,
                i.tipo_participacao, i.titulo_trabalho, i.resumo_trabalho, i.area_trabalho,
                i.nota_final, i.notas_homologadas,
                i.data_inscricao, i.data_checkin,
                e.id AS evento_id, e.titulo, e.categoria, e.tipo_evento, e.permite_apresentacao,
                e.modalidade, e.data_inicio, e.carga_horaria,
                p.nome AS participante_nome, p.cpf, p.cpf_hash,
                c.codigo_autenticidade AS certificado_codigo
            FROM inscricoes i
            JOIN eventos e ON i.evento_id = e.id
            JOIN participantes p ON i.participante_id = p.id
            LEFT JOIN certificados c ON i.id = c.inscricao_id
            WHERE ((p.cpf_hash = %s AND %s != '') OR p.cpf = %s OR p.cpf = %s OR REPLACE(REPLACE(REPLACE(p.cpf, '.', ''), '-', ''), ' ', '') = %s OR p.email = %s)
            ORDER BY e.data_inicio DESC;
        """
        # Sanitização e parametrização segura para busca por Blind Index e prevenção de SQL Injection
        cpf_limpo = "".join([c for c in cpf if c.isdigit()])
        cpf_hash = gerar_hash_cpf(cpf_limpo) if cpf_limpo else ""
        cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf.strip()
        cursor.execute(sql, (cpf_hash, cpf_hash, cpf.strip(), cpf_formatado, cpf_limpo, cpf.strip()))
        linhas = cursor.fetchall()
        conn.close()

        inscricoes = []
        for l in linhas:
            d = dict(l)
            d["qr_code_b64"] = QRCodeHelper.gerar_qr_base64(d["codigo_inscricao"])
            inscricoes.append(d)
        return inscricoes

    @staticmethod
    def registrar_checkin(inscricao_id: int):
        """
        Registra a presença do participante no evento (Check-in) no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE inscricoes 
            SET status = 'Presente', data_checkin = %s
            WHERE id = %s;
        """, (agora, inscricao_id))

        conn.commit()
        conn.close()

    @staticmethod
    def registrar_checkin_por_codigo(codigo_inscricao: str):
        """
        Realiza o Check-in via código de QR Code lido pelo scanner no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT i.id, i.codigo_inscricao, i.status, i.tipo_participacao, i.titulo_trabalho,
                   p.nome AS participante_nome, p.cpf, e.titulo AS evento_titulo, e.id AS evento_id
            FROM inscricoes i
            JOIN participantes p ON i.participante_id = p.id
            JOIN eventos e ON i.evento_id = e.id
            WHERE i.codigo_inscricao = %s;
        """, (codigo_inscricao.strip().upper(),))
        inscricao = cursor.fetchone()

        if not inscricao:
            conn.close()
            return {"sucesso": False, "mensagem": f"Nenhuma inscrição localizada para o código: {codigo_inscricao}"}

        ja_presente = (inscricao["status"] == "Presente")
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE inscricoes 
            SET status = 'Presente', data_checkin = COALESCE(data_checkin, %s)
            WHERE id = %s;
        """, (agora, inscricao["id"]))

        conn.commit()
        conn.close()

        return {
            "sucesso": True,
            "inscricao_id": inscricao["id"],
            "codigo_inscricao": inscricao["codigo_inscricao"],
            "participante_nome": inscricao["participante_nome"],
            "cpf": inscricao["cpf"],
            "evento_titulo": inscricao["evento_titulo"],
            "evento_id": inscricao["evento_id"],
            "tipo_participacao": inscricao["tipo_participacao"],
            "titulo_trabalho": inscricao["titulo_trabalho"] or "Participação como Ouvinte",
            "ja_presente": ja_presente,
            "data_checkin": agora,
            "mensagem": "Presença confirmada anteriormente!" if ja_presente else "Check-in realizado com sucesso!"
        }

    @staticmethod
    def cancelar_inscricao(inscricao_id: int):
        """
        Altera o status da inscrição para 'Cancelada' no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE inscricoes SET status = 'Cancelada' WHERE id = %s;", (inscricao_id,))
        conn.commit()
        conn.close()


class TutorService:
    """
    Serviço de gestão dos Professores Tutores que compõem as bancas de avaliação no MySQL.
    """

    @staticmethod
    def listar_todos():
        """Retorna todos os professores tutores cadastrados no MySQL."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, email, departamento, criado_em FROM tutores ORDER BY nome ASC;")
        tutores = cursor.fetchall()
        conn.close()
        return tutores

    @staticmethod
    def buscar_por_id(tutor_id: int):
        """Busca um tutor pelo seu ID primário no MySQL."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, email, departamento FROM tutores WHERE id = %s;", (tutor_id,))
        tutor = cursor.fetchone()
        conn.close()
        return tutor

    @staticmethod
    def buscar_por_email(email: str):
        """
        Busca um professor tutor pelo endereço de e-mail institucional no MySQL.
        Permite associar com precisão o usuário logado com seu registro de tutor na banca.
        """
        if not email:
            return None
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, email, departamento FROM tutores WHERE LOWER(email) = LOWER(%s);", (email.strip(),))
        tutor = cursor.fetchone()
        conn.close()
        return tutor

    @staticmethod
    def cadastrar(nome: str, email: str, departamento: str):
        """Cadastra um novo professor tutor no MySQL."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tutores (nome, email, departamento)
            VALUES (%s, %s, %s);
        """, (nome.strip(), email.strip(), departamento.strip()))
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return novo_id


class AmostraService:
    """
    Serviço especializado para gerenciar as apresentações de Amostra Acadêmica no MySQL.
    """

    @staticmethod
    def listar_apresentacoes_evento(evento_id: int):
        """
        Retorna todas as apresentações de Amostra do evento com tutores e notas no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                i.id AS inscricao_id, i.codigo_inscricao, i.status AS status_inscricao,
                i.titulo_trabalho, i.resumo_trabalho, i.area_trabalho, i.autores,
                i.nota_final, i.notas_homologadas, i.data_homologacao,
                p.id AS participante_id, p.nome AS participante_nome, p.cpf, p.email,
                p.matricula_curso,
                COUNT(b.id) AS qtd_tutores_designados,
                COUNT(CASE WHEN b.status_avaliacao = 'Avaliado' THEN 1 END) AS qtd_avaliacoes_feitas,
                AVG(a.nota_media) AS media_preliminar_tutores
            FROM inscricoes i
            JOIN participantes p ON i.participante_id = p.id
            LEFT JOIN banca_tutores b ON i.id = b.inscricao_id
            LEFT JOIN avaliacoes_apresentacao a ON b.id = a.banca_id
            WHERE i.evento_id = %s AND (i.tipo_participacao = 'Apresentador' OR i.titulo_trabalho IS NOT NULL)
            GROUP BY i.id
            ORDER BY i.titulo_trabalho ASC;
        """
        cursor.execute(sql, (evento_id,))
        linhas = cursor.fetchall()

        apresentacoes = []
        for l in linhas:
            item = dict(l)
            cursor.execute("""
                SELECT b.id AS banca_id, b.tutor_id, b.status_avaliacao,
                       t.nome AS tutor_nome, t.departamento,
                       a.nota_media, a.comentarios, a.data_avaliacao
                FROM banca_tutores b
                JOIN tutores t ON b.tutor_id = t.id
                LEFT JOIN avaliacoes_apresentacao a ON b.id = a.banca_id
                WHERE b.inscricao_id = %s
                ORDER BY t.nome ASC;
            """, (item["inscricao_id"],))
            item["tutores_banca"] = cursor.fetchall()
            apresentacoes.append(item)

        conn.close()
        return apresentacoes

    @staticmethod
    def definir_qtd_tutores_evento(evento_id: int, qtd_tutores: int):
        """
        Permite ao criador estipular a quantidade de tutores no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE eventos SET qtd_tutores_por_trabalho = %s WHERE id = %s;", (qtd_tutores, evento_id))
        conn.commit()
        conn.close()

    @staticmethod
    def designar_tutor(evento_id: int, inscricao_id: int, tutor_id: int):
        """
        Designa um professor tutor para avaliar uma apresentação no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO banca_tutores (evento_id, inscricao_id, tutor_id, status_avaliacao)
                VALUES (%s, %s, %s, 'Pendente');
            """, (evento_id, inscricao_id, tutor_id))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def remover_tutor_banca(banca_id: int):
        """
        Remove um tutor da banca no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM banca_tutores WHERE id = %s;", (banca_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def listar_trabalhos_atribuidos_ao_tutor(tutor_id: int):
        """
        Retorna as apresentações atribuídas ao tutor selecionado no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                b.id AS banca_id, b.status_avaliacao,
                i.id AS inscricao_id, i.codigo_inscricao, i.titulo_trabalho, i.resumo_trabalho,
                i.area_trabalho, i.autores, i.status AS status_presenca,
                p.nome AS autor_principal, p.matricula_curso,
                e.id AS evento_id, e.titulo AS evento_titulo, e.data_inicio,
                a.nota_dominio, a.nota_clareza, a.nota_relevancia, a.nota_media, a.comentarios, a.data_avaliacao
            FROM banca_tutores b
            JOIN inscricoes i ON b.inscricao_id = i.id
            JOIN participantes p ON i.participante_id = p.id
            JOIN eventos e ON b.evento_id = e.id
            LEFT JOIN avaliacoes_apresentacao a ON b.id = a.banca_id
            WHERE b.tutor_id = %s
            ORDER BY b.status_avaliacao DESC, i.titulo_trabalho ASC;
        """
        cursor.execute(sql, (tutor_id,))
        trabalhos = cursor.fetchall()
        conn.close()
        return trabalhos

    @staticmethod
    def verificar_tutor_designado(inscricao_id: int, tutor_id: int) -> bool:
        """
        Verifica se o professor tutor está formalmente associado à banca examinadora da apresentação no MySQL.
        Garante a regra estrita de negócio: cada tutor só pode acessar e pontuar seus próprios trabalhos designados.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM banca_tutores WHERE inscricao_id = %s AND tutor_id = %s;", (inscricao_id, tutor_id))
        banca = cursor.fetchone()
        conn.close()
        return banca is not None

    @staticmethod
    def salvar_avaliacao_tutor(inscricao_id: int, tutor_id: int, nota_dominio: float, nota_clareza: float, nota_relevancia: float, comentarios: str):
        """
        Registra as notas dadas pelo tutor no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id FROM banca_tutores WHERE inscricao_id = %s AND tutor_id = %s;
            """, (inscricao_id, tutor_id))
            banca = cursor.fetchone()

            if not banca:
                raise ValueError("Este professor tutor não está designado para esta apresentação.")

            banca_id = banca["id"]
            nota_media = round((nota_dominio + nota_clareza + nota_relevancia) / 3.0, 2)

            cursor.execute("SELECT id FROM avaliacoes_apresentacao WHERE banca_id = %s;", (banca_id,))
            av_existente = cursor.fetchone()

            if av_existente:
                cursor.execute("""
                    UPDATE avaliacoes_apresentacao SET
                        nota_dominio = %s, nota_clareza = %s, nota_relevancia = %s,
                        nota_media = %s, comentarios = %s, data_avaliacao = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (nota_dominio, nota_clareza, nota_relevancia, nota_media, comentarios.strip(), av_existente["id"]))
            else:
                cursor.execute("""
                    INSERT INTO avaliacoes_apresentacao (
                        banca_id, inscricao_id, tutor_id, nota_dominio, nota_clareza, nota_relevancia, nota_media, comentarios
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (banca_id, inscricao_id, tutor_id, nota_dominio, nota_clareza, nota_relevancia, nota_media, comentarios.strip()))

            cursor.execute("UPDATE banca_tutores SET status_avaliacao = 'Avaliado' WHERE id = %s;", (banca_id,))
            conn.commit()
            return nota_media

        finally:
            conn.close()

    @staticmethod
    def homologar_notas_trabalho(inscricao_id: int):
        """
        Validação do criador: oficializa a nota no MySQL e torna visível online para o aluno.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT AVG(nota_media) AS media_final
                FROM avaliacoes_apresentacao
                WHERE inscricao_id = %s;
            """, (inscricao_id,))
            resultado = cursor.fetchone()

            if not resultado or resultado["media_final"] is None:
                raise ValueError("Nenhuma avaliação foi realizada pelos tutores para este trabalho.")

            media_final = round(resultado["media_final"], 2)

            cursor.execute("""
                UPDATE inscricoes SET
                    nota_final = %s,
                    notas_homologadas = 1,
                    data_homologacao = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (media_final, inscricao_id))

            conn.commit()
            return media_final

        finally:
            conn.close()

    @staticmethod
    def homologar_todas_notas_evento(evento_id: int):
        """
        Validação em lote pelo criador no MySQL.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT i.id, AVG(a.nota_media) AS media_calc
            FROM inscricoes i
            JOIN avaliacoes_apresentacao a ON i.id = a.inscricao_id
            WHERE i.evento_id = %s
            GROUP BY i.id;
        """, (evento_id,))
        trabalhos = cursor.fetchall()

        total_homologados = 0
        for t in trabalhos:
            media = round(t["media_calc"], 2)
            cursor.execute("""
                UPDATE inscricoes SET
                    nota_final = %s,
                    notas_homologadas = 1,
                    data_homologacao = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (media, t["id"]))
            total_homologados += 1

        cursor.execute("UPDATE eventos SET status_notas = 'Homologadas' WHERE id = %s;", (evento_id,))
        conn.commit()
        conn.close()
        return total_homologados

    @staticmethod
    def obter_resultado_aluno(inscricao_id: int):
        """
        Recupera as avaliações no MySQL. Se não homologado, bloqueia as notas parciais.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                i.id AS inscricao_id, i.codigo_inscricao, i.titulo_trabalho, i.resumo_trabalho,
                i.area_trabalho, i.autores, i.nota_final, i.notas_homologadas, i.data_homologacao,
                p.nome AS aluno_nome, p.cpf, p.matricula_curso,
                e.id AS evento_id, e.titulo AS evento_titulo, e.data_inicio
            FROM inscricoes i
            JOIN participantes p ON i.participante_id = p.id
            JOIN eventos e ON i.evento_id = e.id
            WHERE i.id = %s;
        """
        cursor.execute(sql, (inscricao_id,))
        trabalho = cursor.fetchone()

        if not trabalho:
            conn.close()
            return None

        resultado = dict(trabalho)

        if resultado["notas_homologadas"] == 1:
            cursor.execute("""
                SELECT 
                    t.nome AS tutor_nome, t.departamento,
                    a.nota_dominio, a.nota_clareza, a.nota_relevancia, a.nota_media,
                    a.comentarios, a.data_avaliacao
                FROM avaliacoes_apresentacao a
                JOIN tutores t ON a.tutor_id = t.id
                WHERE a.inscricao_id = %s
                ORDER BY t.nome ASC;
            """, (inscricao_id,))
            resultado["avaliacoes_tutores"] = cursor.fetchall()
        else:
            resultado["avaliacoes_tutores"] = []

        conn.close()
        return resultado


class CertificadoService:
    """
    Serviço de certificados no MySQL.
    """

    @staticmethod
    def emitir_certificado(inscricao_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT i.id, i.status, i.evento_id, i.participante_id, e.carga_horaria
                FROM inscricoes i
                JOIN eventos e ON i.evento_id = e.id
                WHERE i.id = %s;
            """, (inscricao_id,))
            inscricao = cursor.fetchone()

            if not inscricao:
                raise ValueError("Inscrição não encontrada.")

            if inscricao['status'] != 'Presente':
                raise ValueError("O certificado só pode ser emitido para participantes com presença confirmada (Check-in).")

            cursor.execute("SELECT codigo_autenticidade FROM certificados WHERE inscricao_id = %s;", (inscricao_id,))
            cert_existente = cursor.fetchone()

            if cert_existente:
                return cert_existente['codigo_autenticidade']

            token_base = f"{inscricao_id}-{inscricao['evento_id']}-{inscricao['participante_id']}-{datetime.now().isoformat()}"
            hash_gerado = hashlib.sha256(token_base.encode('utf-8')).hexdigest()[:8].upper()
            codigo_autenticidade = f"CERT-2026-{hash_gerado}"

            cursor.execute("""
                INSERT INTO certificados (codigo_autenticidade, inscricao_id, evento_id, participante_id, carga_horaria)
                VALUES (%s, %s, %s, %s, %s);
            """, (
                codigo_autenticidade,
                inscricao_id,
                inscricao['evento_id'],
                inscricao['participante_id'],
                inscricao['carga_horaria']
            ))

            conn.commit()
            return codigo_autenticidade

        finally:
            conn.close()

    @staticmethod
    def validar_certificado(codigo_autenticidade: str):
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT 
                c.id AS certificado_id, c.codigo_autenticidade, c.data_emissao, c.status AS status_certificado,
                c.carga_horaria,
                e.titulo AS evento_titulo, e.categoria, e.modalidade, e.data_inicio, e.data_fim, e.palestrante,
                p.nome AS participante_nome, p.cpf, p.tipo_participante, p.matricula_curso
            FROM certificados c
            JOIN eventos e ON c.evento_id = e.id
            JOIN participantes p ON c.participante_id = p.id
            WHERE c.codigo_autenticidade = %s;
        """
        cursor.execute(sql, (codigo_autenticidade.strip().upper(),))
        resultado = cursor.fetchone()
        conn.close()
        return resultado


class RelatorioService:
    """
    Serviço analítico no MySQL.
    """

    @staticmethod
    def obter_estatisticas_gerais():
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS total_eventos FROM eventos;")
        total_eventos = cursor.fetchone()['total_eventos']

        cursor.execute("SELECT COUNT(*) AS total_inscricoes FROM inscricoes WHERE status != 'Cancelada';")
        total_inscricoes = cursor.fetchone()['total_inscricoes']

        cursor.execute("SELECT COUNT(*) AS total_presentes FROM inscricoes WHERE status = 'Presente';")
        total_presentes = cursor.fetchone()['total_presentes']

        cursor.execute("SELECT COUNT(*) AS total_certificados FROM certificados WHERE status = 'Válido';")
        total_certificados = cursor.fetchone()['total_certificados']

        cursor.execute("SELECT COUNT(*) AS total_amostras FROM inscricoes WHERE tipo_participacao = 'Apresentador';")
        total_amostras = cursor.fetchone()['total_amostras']

        cursor.execute("SELECT COUNT(*) AS total_avaliacoes FROM avaliacoes_apresentacao;")
        total_avaliacoes = cursor.fetchone()['total_avaliacoes']

        cursor.execute("""
            SELECT e.titulo, COUNT(i.id) AS qtd_inscritos, e.vagas_totais
            FROM eventos e
            LEFT JOIN inscricoes i ON e.id = i.evento_id AND i.status != 'Cancelada'
            GROUP BY e.id
            ORDER BY qtd_inscritos DESC
            LIMIT 5;
        """)
        top_eventos = cursor.fetchall()

        conn.close()

        taxa_presenca = 0
        if total_inscricoes > 0:
            taxa_presenca = round((total_presentes / total_inscricoes) * 100, 1)

        return {
            "total_eventos": total_eventos,
            "total_inscricoes": total_inscricoes,
            "total_presentes": total_presentes,
            "taxa_presenca": taxa_presenca,
            "total_certificados": total_certificados,
            "total_amostras": total_amostras,
            "total_avaliacoes": total_avaliacoes,
            "top_eventos": top_eventos
        }


# # ============================================================================
# SERVIÇO DE DISPARO DE E-MAILS TRANSACIONAIS E NOTIFICAÇÕES (SMTP / DEV)
# ============================================================================
class EmailService:
    """
    Serviço central de envio de e-mails transacionais (como recuperação de senhas).
    Suporta servidores SMTP reais configurados via arquivo .env (Gmail, SendGrid, Amazon SES, Outlook)
    e conta com modo de fallback transparente para simulação em ambiente local/desenvolvimento.
    """

    @staticmethod
    def mascarar_email(email: str) -> str:
        """
        Aplica máscara de proteção ao e-mail para exibição segura ao usuário (LGPD).
        Exemplo: 'gestor.eventos@unifaccamp.edu.br' -> 'g***s@unifaccamp.edu.br'
        """
        if not email or "@" not in email:
            return "***@***"
        usuario, dominio = email.split("@", 1)
        if len(usuario) <= 2:
            usuario_mascarado = usuario[0] + "*"
        else:
            usuario_mascarado = usuario[0] + "*" * (len(usuario) - 2) + usuario[-1]
        return f"{usuario_mascarado}@{dominio}"

    @staticmethod
    def enviar_codigo_recuperacao(destinatario: str, nome_usuario: str, codigo: str) -> bool:
        """
        Envia o e-mail contendo o código numérico de 6 dígitos para redefinição de senha.
        Se os parâmetros SMTP do .env não estiverem configurados, opera no modo de simulação seguro.
        """
        smtp_server = os.getenv("SMTP_SERVER", "").strip()
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
        smtp_from = os.getenv("SMTP_FROM", "UNIFACCAMP Eventos <nao-responda@unifaccamp.edu.br>")
        smtp_tls = os.getenv("SMTP_TLS", "True").lower() in ("true", "1", "yes")

        assunto = "Código de Recuperação de Senha - Portal de Eventos UNIFACCAMP"
        corpo_texto = f"""Olá, {nome_usuario}!

Recebemos uma solicitação para redefinir a senha da sua conta no Portal de Eventos e Extensão UNIFACCAMP.

Seu código de verificação é: {codigo}

Por motivos de segurança, este código expira em 15 minutos.
Se você não solicitou a recuperação de senha, desconsidere esta mensagem.

Atenciosamente,
Pró-Reitoria de Extensão Universitária - UNIFACCAMP
"""

        # Envio real via servidor SMTP configurado no .env
        if smtp_server and smtp_user:
            try:
                # Se for Gmail, o remetente visível deve coincidir com a conta autenticada
                if "gmail.com" in smtp_server.lower():
                    remetente_final = f"UNIFACCAMP Eventos <{smtp_user}>"
                else:
                    remetente_final = smtp_from or smtp_user

                msg = MIMEMultipart()
                msg["From"] = remetente_final
                msg["To"] = destinatario
                msg["Subject"] = assunto
                msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))

                # Suporte a porta 465 (SSL direto) ou 587 (STARTTLS com handshake ehlo)
                if smtp_port == 465:
                    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=12) as servidor:
                        servidor.login(smtp_user, smtp_password)
                        servidor.send_message(msg)
                else:
                    with smtplib.SMTP(smtp_server, smtp_port, timeout=12) as servidor:
                        servidor.ehlo()
                        if smtp_tls:
                            servidor.starttls()
                            servidor.ehlo()
                        servidor.login(smtp_user, smtp_password)
                        servidor.send_message(msg)

                print(f"[EmailService] Código de recuperação enviado via SMTP com sucesso para: {destinatario}")
                return True
            except Exception as erro_smtp:
                print(f"[EmailService - AVISO] Falha no disparo SMTP ({erro_smtp}). Código registrado no log de segurança.")

        # Modo seguro de desenvolvimento / simulação local
        print(f"[EmailService - SIMULAÇÃO] Código de 6 dígitos gerado para {destinatario}: {codigo}")
        return True


# ============================================================================
# SERVIÇO DE USUÁRIOS, AUTENTICAÇÃO POR CPF E CONTROLE DE PERFIS (ACL)
# ============================================================================
class UsuarioService:
    """
    Serviço de gerenciamento de Usuários, Autenticação por CPF e Controle de Perfis (ACL).
    Implementa:
    - Autenticação por CPF (Blind Index HMAC-SHA256) e verificação de senha com PBKDF2.
    - Cadastro inicial automático como 'Usuário Base'.
    - Painel de Gestão de Usuários com busca por CPF.
    - Alteração dinâmica de perfis pelo Gestor a qualquer momento.
    - Recuperação de senha segura com código numérico enviado por e-mail.
    """

    @staticmethod
    def autenticar(cpf: str, senha: str):
        """
        Autentica o usuário pelo CPF utilizando Blind Index HMAC-SHA256 (cpf_hash)
        e validação segura de senha com PBKDF2-HMAC-SHA256 (100.000 iterações + salt aleatório)
        com proteção estrita contra ataques de temporização (timing attacks).
        Atualiza automaticamente senhas legadas para PBKDF2 no primeiro login com sucesso.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cpf_bruto = str(cpf).strip()
        cpf_limpo = "".join([c for c in cpf_bruto if c.isdigit()])
        cpf_hash = gerar_hash_cpf(cpf_limpo) if cpf_limpo else ""
        cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_bruto

        # Busca segura indexada O(1) pelo Blind Index cpf_hash, CPF exato/formatado ou e-mail
        sql = """
            SELECT id, nome, cpf, cpf_hash, email, telefone, senha_hash, perfil, cargo, departamento, ativo
            FROM usuarios
            WHERE (cpf_hash = %s AND %s != '') 
               OR cpf = %s
               OR cpf = %s
               OR REPLACE(REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', ''), '/', '') = %s
               OR LOWER(email) = LOWER(%s);
        """
        cursor.execute(sql, (cpf_hash, cpf_hash, cpf_bruto, cpf_formatado, cpf_limpo, cpf_bruto))
        usuario = cursor.fetchone()

        if not usuario:
            conn.close()
            raise ValueError("Usuário não encontrado com o CPF informado.")

        if usuario.get("ativo", 1) == 0:
            conn.close()
            raise ValueError("Este usuário está inativo no sistema.")

        # Validação estrita da senha com algoritmo criptográfico PBKDF2 / timing attack protection
        senha_armazenada = usuario.get("senha_hash", "")
        senha_valida = verificar_hash_senha(senha, senha_armazenada)

        if not senha_valida:
            conn.close()
            raise ValueError("Senha incorreta. Verifique e tente novamente.")

        # Re-hashing transparente: se a senha não estava em PBKDF2 ou se faltava cpf_hash, salva os novos dados
        precisa_novo_hash = not senha_armazenada.startswith("pbkdf2:sha256:")
        precisa_cpf_hash = not usuario.get("cpf_hash")

        if precisa_novo_hash or precisa_cpf_hash:
            novo_hash_senha = gerar_hash_senha(senha) if precisa_novo_hash else senha_armazenada
            cursor.execute("""
                UPDATE usuarios 
                SET senha_hash = %s, cpf_hash = %s 
                WHERE id = %s;
            """, (novo_hash_senha, cpf_hash, usuario["id"]))
            conn.commit()
            usuario["senha_hash"] = novo_hash_senha
            usuario["cpf_hash"] = cpf_hash

        conn.close()
        return usuario

    @staticmethod
    def cadastrar(nome: str, cpf: str, email: str, telefone: str, senha: str):
        """
        Cadastra um novo usuário no sistema com máxima segurança:
        - Senha protegida com PBKDF2-HMAC-SHA256 (salt de 16 bytes e 100.000 iterações).
        - CPF protegido com Blind Index criptográfico HMAC-SHA256 (cpf_hash).
        - Todo usuário inicia obrigatoriamente com o perfil 'Usuário Base'.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cpf_limpo = "".join([c for c in cpf if c.isdigit()])
        if not validar_cpf(cpf_limpo, permitir_admin_padrao=True):
            conn.close()
            raise ValueError("O CPF informado é inválido. Por favor, forneça um CPF válido com 11 dígitos e dígitos verificadores corretos.")

        # Blind Index HMAC-SHA256 para busca indexada sem vazamento do CPF
        cpf_hash = gerar_hash_cpf(cpf_limpo)

        # Verifica duplicidade utilizando o Blind Index cpf_hash e email
        cursor.execute("""
            SELECT id FROM usuarios 
            WHERE (cpf_hash = %s AND %s != '') 
               OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = %s 
               OR email = %s;
        """, (cpf_hash, cpf_hash, cpf_limpo, email.strip()))
        existente = cursor.fetchone()

        if existente:
            conn.close()
            raise ValueError("Já existe um cadastro com este CPF ou e-mail no sistema.")

        # Geração do hash PBKDF2 seguro
        hash_senha_pbkdf2 = gerar_hash_senha(senha)

        # Formatação do CPF
        cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"

        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, cpf_hash, email, telefone, senha_hash, perfil, cargo, departamento)
            VALUES (%s, %s, %s, %s, %s, %s, 'Usuário Base', 'Usuário Base', 'Comunidade Acadêmica');
        """, (nome.strip(), cpf_formatado, cpf_hash, email.strip(), telefone.strip() if telefone else "", hash_senha_pbkdf2))

        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return novo_id

    @staticmethod
    def listar_todos(busca_cpf_nome: str = None):
        """
        Lista todos os usuários cadastrados com suporte a busca por CPF ou Nome.
        Utiliza o Blind Index (cpf_hash) para busca exata de CPF por índice O(1).
        Exclusivo para uso do Gestor do Sistema.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT id, nome, cpf, cpf_hash, email, telefone, perfil, cargo, departamento, ativo, criado_em
            FROM usuarios
            WHERE 1=1
        """
        params = []
        if busca_cpf_nome:
            busca_limpa = "".join([c for c in busca_cpf_nome if c.isdigit()])
            if busca_limpa:
                if len(busca_limpa) == 11:
                    cpf_hash_busca = gerar_hash_cpf(busca_limpa)
                    sql += " AND (cpf_hash = %s OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') LIKE %s OR nome LIKE %s)"
                    params.extend([cpf_hash_busca, f"%{busca_limpa}%", f"%{busca_cpf_nome}%"])
                else:
                    sql += " AND (REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') LIKE %s OR nome LIKE %s)"
                    params.extend([f"%{busca_limpa}%", f"%{busca_cpf_nome}%"])
            else:
                sql += " AND (nome LIKE %s OR email LIKE %s)"
                params.extend([f"%{busca_cpf_nome}%", f"%{busca_cpf_nome}%"])

        sql += " ORDER BY CASE WHEN perfil = 'Gestor' THEN 1 WHEN perfil = 'Professor Tutor' THEN 2 ELSE 3 END, nome ASC;"
        cursor.execute(sql, tuple(params))
        usuarios = cursor.fetchall()
        conn.close()
        return usuarios

    @staticmethod
    def buscar_por_id(usuario_id: int):
        """Busca os dados de um usuário pelo ID primário."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cpf, cpf_hash, email, telefone, perfil, cargo, departamento, ativo, criado_em FROM usuarios WHERE id = %s;", (usuario_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    @staticmethod
    def buscar_por_cpf(cpf: str):
        """
        Localiza um usuário pelo CPF (via Blind Index ou limpeza de caracteres) ou por e-mail.
        Garante busca tolerante a pontuações, espaços, barras e maiúsculas/minúsculas.
        """
        if not cpf:
            return None
        conn = get_db_connection()
        cursor = conn.cursor()
        cpf_bruto = str(cpf).strip()
        cpf_limpo = "".join([c for c in cpf_bruto if c.isdigit()])
        cpf_hash = gerar_hash_cpf(cpf_limpo) if cpf_limpo else ""
        cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_bruto

        sql = """
            SELECT id, nome, cpf, cpf_hash, email, telefone, perfil, cargo, departamento, ativo, criado_em
            FROM usuarios
            WHERE (cpf_hash = %s AND %s != '') 
               OR cpf = %s
               OR cpf = %s
               OR REPLACE(REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', ''), '/', '') = %s
               OR LOWER(email) = LOWER(%s);
        """
        cursor.execute(sql, (cpf_hash, cpf_hash, cpf_bruto, cpf_formatado, cpf_limpo, cpf_bruto))
        user = cursor.fetchone()
        conn.close()
        return user

    @staticmethod
    def solicitar_recuperacao_senha(cpf: str) -> dict:
        """
        Inicia o fluxo de recuperação de senha por CPF:
        1. Localiza o usuário cadastrado no sistema.
        2. Gera um código numérico aleatório criptograficamente seguro de 6 dígitos.
        3. Grava o código e o hash na tabela 'recuperacao_senha' com validade de 15 minutos.
        4. Dispara o e-mail transacional para o endereço cadastrado.
        """
        usuario = UsuarioService.buscar_por_cpf(cpf)
        if not usuario:
            raise ValueError("Não encontramos nenhum cadastro ativo com o CPF informado. Verifique os dados ou cadastre-se.")

        if usuario.get("ativo", 1) == 0:
            raise ValueError("Esta conta de usuário está desativada no sistema.")

        email_destino = usuario.get("email", "").strip()
        if not email_destino:
            raise ValueError("O usuário não possui um endereço de e-mail válido cadastrado para recuperação.")

        # Gera código numérico seguro de 6 dígitos (ex: 482915)
        codigo_numerico = f"{secrets.randbelow(900000) + 100000}"
        codigo_hash = hashlib.sha256(codigo_numerico.encode("utf-8")).hexdigest()
        expira_em = datetime.now() + timedelta(minutes=15)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Invalida códigos anteriores pendentes para o mesmo usuário
        cursor.execute("UPDATE recuperacao_senha SET utilizado = 1 WHERE usuario_id = %s AND utilizado = 0;", (usuario["id"],))

        # Registra o novo código de recuperação
        cursor.execute("""
            INSERT INTO recuperacao_senha (usuario_id, codigo_verificacao, codigo_hash, email_destinatario, expira_em)
            VALUES (%s, %s, %s, %s, %s);
        """, (usuario["id"], codigo_numerico, codigo_hash, email_destino, expira_em))
        conn.commit()
        conn.close()

        # Dispara o e-mail com o código
        EmailService.enviar_codigo_recuperacao(
            destinatario=email_destino,
            nome_usuario=usuario["nome"],
            codigo=codigo_numerico
        )

        email_mascarado = EmailService.mascarar_email(email_destino)
        return {
            "sucesso": True,
            "usuario_id": usuario["id"],
            "email_mascarado": email_mascarado,
            "codigo_dev": codigo_numerico,
            "cpf_formatado": usuario["cpf"]
        }

    @staticmethod
    def validar_codigo_recuperacao(cpf: str, codigo: str) -> dict:
        """
        Valida o código de verificação recebido pelo usuário.
        Verifica correspondência, prazo de validade (15 minutos) e status de utilização.
        """
        usuario = UsuarioService.buscar_por_cpf(cpf)
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        codigo_limpo = codigo.strip()
        codigo_hash = hashlib.sha256(codigo_limpo.encode("utf-8")).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta código ativo não expirado
        cursor.execute("""
            SELECT id, usuario_id, expira_em 
            FROM recuperacao_senha 
            WHERE usuario_id = %s 
              AND (codigo_hash = %s OR codigo_verificacao = %s)
              AND utilizado = 0 
              AND expira_em >= NOW()
            ORDER BY id DESC LIMIT 1;
        """, (usuario["id"], codigo_hash, codigo_limpo))
        registro = cursor.fetchone()

        if not registro:
            conn.close()
            raise ValueError("Código de verificação incorreto ou expirado. Verifique os 6 dígitos recebidos ou solicite um novo código.")

        # Marca o código como validado / utilizado
        cursor.execute("UPDATE recuperacao_senha SET utilizado = 1 WHERE id = %s;", (registro["id"],))
        conn.commit()
        conn.close()

        return {
            "valido": True,
            "usuario_id": usuario["id"],
            "usuario_nome": usuario["nome"]
        }

    @staticmethod
    def redefinir_senha(usuario_id: int, nova_senha: str) -> bool:
        """
        Grava a nova senha do usuário utilizando o hash criptográfico seguro PBKDF2
        após validação bem-sucedida do código de verificação.
        """
        if not nova_senha or len(nova_senha.strip()) < 6:
            raise ValueError("A nova senha deve possuir no mínimo 6 caracteres.")

        senha_hash_segura = gerar_hash_senha(nova_senha)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s;", (senha_hash_segura, usuario_id))
        # Invalida quaisquer tokens pendentes
        cursor.execute("UPDATE recuperacao_senha SET utilizado = 1 WHERE usuario_id = %s;", (usuario_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def alterar_perfil(usuario_id: int, novo_perfil: str, usuario_logado_perfil: str = "Gestor"):
        """
        Permite ao Gestor ou Professor Tutor alterar o perfil de um usuário:
        - Perfis possíveis: 'Gestor', 'Professor Tutor', 'Usuário Base', 'Coordenador'.
        - Regra de Segurança: Professor Tutor NÃO pode alterar o perfil de Gestores,
          nem pode promover nenhum usuário ao perfil de Gestor.
        - Caso o perfil seja alterado para 'Professor Tutor', garante que o usuário
          também esteja inserido na tabela 'tutores' para figurar nas bancas de Amostras.
        """
        perfis_validos = ["Gestor", "Professor Tutor", "Usuário Base", "Coordenador"]
        if novo_perfil not in perfis_validos:
            raise ValueError(f"Perfil inválido: {novo_perfil}")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, nome, email, departamento, perfil, cpf FROM usuarios WHERE id = %s;", (usuario_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise ValueError("Usuário não encontrado.")

        # Regra de Segurança: Professor Tutor não edita Gestor nem promove para Gestor
        if usuario_logado_perfil == "Professor Tutor":
            if user["perfil"] == "Gestor" or str(user["cpf"]).replace(".", "").replace("-", "").strip() == "00000000000":
                conn.close()
                raise ValueError("Acesso negado: Professores Tutores não têm permissão para alterar o privilégio de Gestores.")
            if novo_perfil == "Gestor":
                conn.close()
                raise ValueError("Acesso negado: Professores Tutores não têm permissão para promover usuários ao perfil de Gestor.")

        cursor.execute("""
            UPDATE usuarios SET perfil = %s, cargo = %s WHERE id = %s;
        """, (novo_perfil, novo_perfil, usuario_id))

        # Se virou Professor Tutor, sincroniza com a tabela 'tutores' para bancas examinadoras
        if novo_perfil == "Professor Tutor":
            cursor.execute("SELECT id FROM tutores WHERE email = %s;", (user["email"],))
            tutor_existente = cursor.fetchone()
            if not tutor_existente:
                dept = user["departamento"] or "Corpo Docente UNIFACCAMP"
                cursor.execute("""
                    INSERT INTO tutores (nome, email, departamento) VALUES (%s, %s, %s);
                """, (user["nome"], user["email"], dept))

        conn.commit()
        conn.close()
        return True

    @staticmethod
    def atualizar_usuario(
        usuario_id: int,
        nome: str,
        cpf: str,
        email: str,
        telefone: str = "",
        perfil: str = "Usuário Base",
        cargo: str = "",
        departamento: str = "",
        ativo: int = 1,
        nova_senha: str = None,
        usuario_logado_perfil: str = "Gestor"
    ) -> bool:
        """
        Atualiza o cadastro completo de um usuário no sistema (Gestor ou Professor Tutor):
        - Gestor tem autonomia total para editar qualquer usuário e qualquer privilégio.
        - Professor Tutor pode editar Usuários Base, Professores Tutores e Coordenadores,
          mas NUNCA pode editar Gestores nem promover nenhum usuário a Gestor.
        - Valida CPF (Módulo 11) e atualiza o Blind Index (cpf_hash).
        - Impede duplicidade de CPF ou e-mail com outros usuários existentes.
        - Se informada 'nova_senha' (mínimo 6 caracteres), gera hash seguro PBKDF2.
        - Se o perfil for 'Professor Tutor', sincroniza automaticamente na tabela de tutores.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, nome, cpf, email, perfil, cargo, departamento, ativo FROM usuarios WHERE id = %s;", (usuario_id,))
        alvo = cursor.fetchone()
        if not alvo:
            conn.close()
            raise ValueError("Usuário não encontrado.")

        # Regra de Segurança Estrita: Professor Tutor não edita Gestor nem promove para Gestor
        if usuario_logado_perfil == "Professor Tutor":
            if alvo["perfil"] == "Gestor" or str(alvo["cpf"]).replace(".", "").replace("-", "").strip() == "00000000000":
                conn.close()
                raise ValueError("Acesso negado: Professores Tutores não têm permissão para editar contas de Gestores.")
            if perfil == "Gestor":
                conn.close()
                raise ValueError("Acesso negado: Professores Tutores não têm permissão para conceder o perfil de Gestor.")

        perfis_validos = ["Gestor", "Professor Tutor", "Usuário Base", "Coordenador"]
        if perfil not in perfis_validos:
            conn.close()
            raise ValueError(f"Perfil inválido: {perfil}")

        # Validação do Nome
        if not nome or len(nome.strip()) < 3:
            conn.close()
            raise ValueError("O nome completo deve conter pelo menos 3 caracteres.")

        # Validação do CPF
        cpf_bruto = str(cpf).strip()
        cpf_limpo = "".join([c for c in cpf_bruto if c.isdigit()])
        if not cpf_limpo:
            conn.close()
            raise ValueError("O CPF é obrigatório.")

        if not validar_cpf(cpf_limpo, permitir_admin_padrao=True):
            conn.close()
            raise ValueError("O CPF informado é inválido. Por favor, forneça um CPF válido com 11 dígitos e dígitos verificadores corretos.")

        cpf_hash = gerar_hash_cpf(cpf_limpo)
        cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_bruto

        # Checa duplicidade de CPF com outros usuários
        cursor.execute("""
            SELECT id, nome FROM usuarios 
            WHERE ((cpf_hash = %s AND %s != '') 
               OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = %s)
               AND id != %s;
        """, (cpf_hash, cpf_hash, cpf_limpo, usuario_id))
        duplicado_cpf = cursor.fetchone()
        if duplicado_cpf:
            conn.close()
            raise ValueError(f"Já existe outro usuário ({duplicado_cpf['nome']}) cadastrado com este CPF.")

        # Validação do E-mail
        email_limpo = str(email).strip().lower()
        if not email_limpo or "@" not in email_limpo:
            conn.close()
            raise ValueError("O e-mail informado é inválido.")

        cursor.execute("SELECT id, nome FROM usuarios WHERE LOWER(email) = %s AND id != %s;", (email_limpo, usuario_id))
        duplicado_email = cursor.fetchone()
        if duplicado_email:
            conn.close()
            raise ValueError(f"Já existe outro usuário ({duplicado_email['nome']}) cadastrado com este e-mail.")

        # Tratamento de senha opcional
        senha_sql = ""
        params = [
            nome.strip(),
            cpf_formatado,
            cpf_hash,
            email_limpo,
            telefone.strip() if telefone else "",
            perfil,
            cargo.strip() or perfil,
            departamento.strip() or "Comunidade Acadêmica",
            1 if str(ativo) in ["1", "true", "True"] else 0
        ]

        if nova_senha and len(str(nova_senha).strip()) > 0:
            senha_str = str(nova_senha).strip()
            if len(senha_str) < 6:
                conn.close()
                raise ValueError("A nova senha deve possuir no mínimo 6 caracteres.")
            novo_hash = gerar_hash_senha(senha_str)
            senha_sql = ", senha_hash = %s"
            params.append(novo_hash)

        params.append(usuario_id)

        sql_update = f"""
            UPDATE usuarios 
            SET nome = %s,
                cpf = %s,
                cpf_hash = %s,
                email = %s,
                telefone = %s,
                perfil = %s,
                cargo = %s,
                departamento = %s,
                ativo = %s
                {senha_sql}
            WHERE id = %s;
        """
        cursor.execute(sql_update, tuple(params))

        # Se a senha foi alterada, invalida códigos de recuperação pendentes
        if senha_sql:
            cursor.execute("UPDATE recuperacao_senha SET utilizado = 1 WHERE usuario_id = %s;", (usuario_id,))

        # Se virou Professor Tutor, sincroniza com a tabela de tutores
        if perfil == "Professor Tutor":
            cursor.execute("SELECT id FROM tutores WHERE email = %s;", (email_limpo,))
            tutor_existente = cursor.fetchone()
            if not tutor_existente:
                dept = departamento.strip() or "Corpo Docente UNIFACCAMP"
                cursor.execute("""
                    INSERT INTO tutores (nome, email, departamento) VALUES (%s, %s, %s);
                """, (nome.strip(), email_limpo, dept))
            else:
                cursor.execute("UPDATE tutores SET nome = %s WHERE email = %s;", (nome.strip(), email_limpo))

        conn.commit()
        conn.close()
        return True

    @staticmethod
    def excluir_usuario(usuario_id: int, gestor_logado_id: int) -> bool:
        """
        Exclui permanentemente um usuário do sistema (Exclusivo para Gestores).
        Regras de Integridade e Proteção:
        - Não permite excluir o Gestor Geral institucional padrão (CPF: 00000000000).
        - Não permite ao Gestor excluir a própria conta conectada no momento.
        - Exclui registros dependentes na tabela recuperacao_senha.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, nome, cpf, email, perfil FROM usuarios WHERE id = %s;", (usuario_id,))
        alvo = cursor.fetchone()
        if not alvo:
            conn.close()
            raise ValueError("Usuário não encontrado.")

        cpf_alvo = str(alvo["cpf"]).replace(".", "").replace("-", "").strip() if alvo["cpf"] else ""
        if cpf_alvo == "00000000000":
            conn.close()
            raise ValueError("A conta institucional principal do Gestor Geral não pode ser excluída para garantir a administração do sistema.")

        if usuario_id == gestor_logado_id:
            conn.close()
            raise ValueError("Você não pode excluir a sua própria conta conectada no momento.")

        # Invalida/remove quaisquer tokens de recuperação de senha associados
        cursor.execute("DELETE FROM recuperacao_senha WHERE usuario_id = %s;", (usuario_id,))

        # Remove o usuário do banco MySQL
        cursor.execute("DELETE FROM usuarios WHERE id = %s;", (usuario_id,))

        conn.commit()
        conn.close()
        return True


