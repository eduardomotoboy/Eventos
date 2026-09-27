# -*- coding: utf-8 -*-
"""
Arquivo: app.py
Projeto: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
Descrição: Aplicação Web completa construída em Python utilizando FastAPI, Jinja2,
           banco de dados relacional local (SQLite) e arquitetura Responsive CSS Grid.
           Contempla todo o escopo do Módulo 4:
           - Divulgação de cursos, palestras e Mostras de Extensão (Amostras)
           - Inscrições online com opção de submissão de apresentações de alunos
           - Geração de QR Code único de credenciamento
           - Scanner de QR Code via câmera web para check-in e localização de projetos
           - Designação de professores tutores e quantidades pelo criador do evento
           - Lançamento de notas pelos tutores via webapp (critérios e feedback)
           - Validação e Homologação final das notas pelo criador antes da divulgação online
           - Visualização de notas e pareceres pelos alunos após homologação
           - Emissão e validação pública de certificados digitais
           - Relatórios estatísticos e exportação em CSV
Regra de conformidade: Todo o código possui comentários detalhados e explicativos.
"""

import os
import io
import csv
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Query, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import uvicorn

# Importação dos módulos internos de banco de dados e serviços de negócio
from database import init_db, seed_database_if_empty, get_db_connection
from models import (
    EventoService,
    InscricaoService,
    CertificadoService,
    RelatorioService,
    TutorService,
    AmostraService,
    QRCodeHelper,
    UsuarioService
)

# Caminhos base para arquivos estáticos e templates HTML
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciador de ciclo de vida da aplicação FastAPI.
    Garante que as tabelas do banco MySQL e os dados de exemplo
    sejam inicializados automaticamente assim que o servidor iniciar.
    """
    print("[app.py] Inicializando tabelas do banco de dados MySQL...")
    init_db()
    seed_database_if_empty()
    yield
    print("[app.py] Encerrando aplicação...")


# Criação da instância principal da aplicação FastAPI
app = FastAPI(
    title="Portal de Eventos e Extensão - UNIFACCAMP",
    description="Sistema web para gestão de eventos, amostras de trabalhos, avaliações, QR Code e certificação.",
    version="2.1.0",
    lifespan=lifespan
)

# Habilita gerenciamento de sessões com cookies assinados criptograficamente
# Permite manter o estado do usuário logado (Gestor, Professor Tutor, Usuário Base)
app.add_middleware(
    SessionMiddleware,
    secret_key="unifaccamp-extensao-eventos-secret-session-key-2026",
    session_cookie="eventos_session"
)

# Configuração de arquivos estáticos (CSS e JS)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configuração do motor de templates Jinja2
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def obter_usuario_sessao(request: Request) -> Optional[dict]:
    """
    Função utilitária: Recupera os dados atualizados do usuário autenticado no MySQL
    a partir do ID armazenado na sessão HTTP. Retorna None se não houver sessão ativa
    ou se o usuário estiver inativo.
    """
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return None
    try:
        return UsuarioService.buscar_por_id(usuario_id)
    except Exception:
        return None


# Registra a função como global nos templates Jinja2 para que qualquer página acesse o usuário logado
templates.env.globals["obter_usuario_sessao"] = obter_usuario_sessao


# ============================================================================
# 0. ROTAS DE AUTENTICAÇÃO E GESTÃO DE USUÁRIOS (LOGIN POR CPF & RBAC)
# ============================================================================

@app.get("/login", response_class=HTMLResponse)
async def tela_login(
    request: Request,
    next: str = Query(None),
    msg: str = Query(None),
    erro: str = Query(None)
):
    """
    Exibe o formulário de login por CPF e Senha.
    Caso o usuário já possua uma sessão ativa, redireciona para a página de destino ou catálogo.
    """
    usuario_ativo = obter_usuario_sessao(request)
    if usuario_ativo:
        return RedirectResponse(url=next or "/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "next": next or "",
        "msg": msg,
        "erro": erro
    })


@app.post("/login", response_class=HTMLResponse)
async def processar_login(
    request: Request,
    cpf: str = Form(...),
    senha: str = Form(...),
    next_url: str = Form(None)
):
    """
    Processa a autenticação do usuário por CPF e Senha:
    - Valida as credenciais com verificação segura SHA-256 no MySQL
    - Grava o ID, nome e perfil na sessão HTTP criptografada
    - Redireciona o usuário conforme seu papel ou URL solicitada
    """
    try:
        usuario = UsuarioService.autenticar(cpf=cpf, senha=senha)

        # Salva os dados na sessão
        request.session["usuario_id"] = usuario["id"]
        request.session["usuario_nome"] = usuario["nome"]
        request.session["usuario_perfil"] = usuario["perfil"]
        request.session["usuario_cpf"] = usuario["cpf"]

        # Se houver uma página requisitada previamente, redireciona para ela
        if next_url and next_url.strip():
            return RedirectResponse(url=next_url.strip(), status_code=status.HTTP_303_SEE_OTHER)

        # Destino padrão baseado no privilégio do usuário
        if usuario["perfil"] == "Gestor":
            return RedirectResponse(url="/gestao", status_code=status.HTTP_303_SEE_OTHER)
        elif usuario["perfil"] == "Professor Tutor":
            return RedirectResponse(url="/tutor/avaliacoes", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    except ValueError as erro_auth:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "next": next_url or "",
            "cpf_preenchido": cpf,
            "erro": str(erro_auth)
        })


@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro(request: Request):
    """
    Exibe o formulário de cadastro de novos usuários.
    Conforme especificado, todo cadastro inicia obrigatoriamente com o perfil 'Usuário Base'.
    """
    usuario_ativo = obter_usuario_sessao(request)
    if usuario_ativo:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("cadastro.html", {
        "request": request
    })


@app.post("/cadastro", response_class=HTMLResponse)
async def processar_cadastro(
    request: Request,
    nome: str = Form(...),
    cpf: str = Form(...),
    email: str = Form(...),
    telefone: str = Form(""),
    senha: str = Form(...),
    confirmar_senha: str = Form(...)
):
    """
    Processa o cadastro de um novo usuário:
    - Valida igualdade de senhas
    - Cria o registro no MySQL com perfil primário 'Usuário Base'
    - Autentica imediatamente o usuário na sessão
    """
    if senha != confirmar_senha:
        return templates.TemplateResponse("cadastro.html", {
            "request": request,
            "erro": "As senhas informadas não coincidem. Digite novamente.",
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "telefone": telefone
        })

    try:
        novo_id = UsuarioService.cadastrar(
            nome=nome,
            cpf=cpf,
            email=email,
            telefone=telefone,
            senha=senha
        )

        # Autentica automaticamente o usuário recém-cadastrado
        usuario = UsuarioService.buscar_por_id(novo_id)
        request.session["usuario_id"] = usuario["id"]
        request.session["usuario_nome"] = usuario["nome"]
        request.session["usuario_perfil"] = usuario["perfil"]
        request.session["usuario_cpf"] = usuario["cpf"]

        return RedirectResponse(
            url="/?msg=Cadastro realizado com sucesso! Você está conectado como Usuário Base.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except ValueError as erro_cad:
        return templates.TemplateResponse("cadastro.html", {
            "request": request,
            "erro": str(erro_cad),
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "telefone": telefone
        })


@app.get("/logout")
async def processar_logout(request: Request):
    """
    Encerra a sessão HTTP do usuário e o redireciona para a tela de login.
    """
    request.session.clear()
    return RedirectResponse(
        url="/login?msg=Você encerrou sua sessão com sucesso.",
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/gestao/usuarios", response_class=HTMLResponse)
async def pagina_gestao_usuarios(
    request: Request,
    busca: str = Query(None),
    msg: str = Query(None),
    erro: str = Query(None)
):
    """
    Página exclusiva de Gestão de Usuários e Privilégios (Acesso exclusivo para Gestor):
    - Permite buscar usuários por CPF ou Nome
    - Lista todos os usuários cadastrados
    - Permite ao gestor promover ou alterar o perfil de qualquer usuário a qualquer tempo
    """
    usuario = obter_usuario_sessao(request)
    if not usuario:
        return RedirectResponse(
            url="/login?next=/gestao/usuarios&erro=Acesso restrito ao Gestor do Sistema. Efetue login com suas credenciais.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    if usuario.get("perfil") != "Gestor":
        return RedirectResponse(
            url="/?erro=Acesso negado: apenas o Gestor do Sistema pode gerenciar contas e privilégios de acesso.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    usuarios = UsuarioService.listar_todos(busca_cpf_nome=busca)
    return templates.TemplateResponse("gestao_usuarios.html", {
        "request": request,
        "usuario_logado": usuario,
        "usuarios": usuarios,
        "busca": busca or "",
        "msg": msg,
        "erro": erro
    })


@app.post("/gestao/usuarios/{usuario_id}/alterar-perfil")
async def alterar_perfil_usuario(
    request: Request,
    usuario_id: int,
    novo_perfil: str = Form(...)
):
    """
    Ação exclusiva do Gestor para alterar o perfil de um usuário:
    - Perfis: 'Gestor', 'Professor Tutor', 'Usuário Base', 'Coordenador'
    - Se alterado para 'Professor Tutor', sincroniza automaticamente na tabela de tutores
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") != "Gestor":
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas o Gestor pode alterar privilégios.")

    try:
        UsuarioService.alterar_perfil(usuario_id=usuario_id, novo_perfil=novo_perfil)
        alvo = UsuarioService.buscar_por_id(usuario_id)
        nome_alvo = alvo["nome"] if alvo else "Usuário"
        return RedirectResponse(
            url=f"/gestao/usuarios?msg=O perfil de '{nome_alvo}' foi alterado com sucesso para '{novo_perfil}'.",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as ex:
        return RedirectResponse(
            url=f"/gestao/usuarios?erro={str(ex)}",
            status_code=status.HTTP_303_SEE_OTHER
        )


# ============================================================================
# 1. ROTAS PÚBLICAS: VITRINE E DETALHES DE EVENTOS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def pagina_inicial(
    request: Request,
    busca: str = Query(None),
    categoria: str = Query(None),
    msg: str = Query(None),
    erro: str = Query(None)
):
    """
    Rota principal: Renderiza o catálogo de cursos e eventos de extensão.
    Permite busca por termo e filtro por categoria, além de exibir mensagens de alerta.
    """
    eventos = EventoService.listar_todos(
        filtro_categoria=categoria if categoria else None,
        filtro_status="Inscrições Abertas",
        termo_busca=busca if busca else None
    )
    return templates.TemplateResponse("index.html", {
        "request": request,
        "eventos": eventos,
        "busca": busca,
        "categoria": categoria,
        "mensagem_sucesso": msg,
        "mensagem_erro": erro
    })


@app.get("/evento/{evento_id}", response_class=HTMLResponse)
async def detalhe_evento(request: Request, evento_id: int):
    """
    Exibe os detalhes completos de um evento específico e o formulário de inscrição.
    Se o evento for do tipo 'Amostra', habilita campos para cadastro do trabalho a ser apresentado.
    """
    evento = EventoService.buscar_por_id(evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não localizado.")

    return templates.TemplateResponse("evento_detalhe.html", {
        "request": request,
        "evento": evento
    })


@app.post("/evento/{evento_id}/inscrever", response_class=HTMLResponse)
async def processar_inscricao(
    request: Request,
    evento_id: int,
    nome: str = Form(...),
    cpf: str = Form(...),
    email: str = Form(...),
    telefone: str = Form(None),
    tipo_participante: str = Form(...),
    matricula_curso: str = Form(None),
    tipo_participacao: str = Form("Ouvinte"),
    titulo_trabalho: str = Form(None),
    resumo_trabalho: str = Form(None),
    area_trabalho: str = Form(None),
    autores: str = Form(None)
):
    """
    Processa o formulário de inscrição online:
    - Suporta participantes como ouvintes ou apresentadores de trabalhos
    - Valida integridade e vagas restantes
    - Impede inscrição duplicada para o mesmo CPF
    - Emite o protocolo e redireciona para o comprovante com QR Code
    """
    dados_participante = {
        "nome": nome,
        "cpf": cpf,
        "email": email,
        "telefone": telefone,
        "tipo_participante": tipo_participante,
        "matricula_curso": matricula_curso,
        "tipo_participacao": tipo_participacao,
        "titulo_trabalho": titulo_trabalho,
        "resumo_trabalho": resumo_trabalho,
        "area_trabalho": area_trabalho,
        "autores": autores
    }

    try:
        codigo_inscricao = InscricaoService.realizar_inscricao(evento_id, dados_participante)
        return RedirectResponse(
            url=f"/inscricao/comprovante/{codigo_inscricao}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as erro:
        evento = EventoService.buscar_por_id(evento_id)
        return templates.TemplateResponse("evento_detalhe.html", {
            "request": request,
            "evento": evento,
            "mensagem_erro": str(erro)
        })


@app.get("/inscricao/comprovante/{codigo_inscricao}", response_class=HTMLResponse)
async def exibir_comprovante(request: Request, codigo_inscricao: str):
    """
    Renderiza o comprovante oficial de inscrição com o código alfanumérico e o QR Code gerado.
    """
    inscricao = InscricaoService.buscar_por_codigo(codigo_inscricao)
    if not inscricao:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada.")

    return templates.TemplateResponse("inscricao_sucesso.html", {
        "request": request,
        "inscricao": inscricao
    })


# ============================================================================
# 2. ROTAS DE AUTOATENDIMENTO: MINHAS INSCRIÇÕES E NOTAS DO ALUNO
# ============================================================================

@app.get("/minhas-inscricoes", response_class=HTMLResponse)
async def minhas_inscricoes(request: Request, busca: str = Query(None)):
    """
    Permite ao participante consultar todas as suas inscrições a partir do CPF ou e-mail,
    acessar o QR Code para credenciamento e visualizar notas homologadas de apresentações.
    Se o usuário estiver autenticado e não informou termo de busca, utiliza seu próprio CPF automaticamente.
    """
    usuario = obter_usuario_sessao(request)
    if not busca and usuario and usuario.get("cpf"):
        busca = usuario["cpf"]

    inscricoes = []
    if busca:
        inscricoes = InscricaoService.listar_por_cpf(busca)

    return templates.TemplateResponse("minhas_inscricoes.html", {
        "request": request,
        "usuario_logado": usuario,
        "busca": busca,
        "inscricoes": inscricoes
    })


@app.get("/minhas-inscricoes/trabalho/{inscricao_id}/resultado", response_class=HTMLResponse)
async def visualizar_resultado_trabalho(request: Request, inscricao_id: int):
    """
    Tela onde o aluno visualiza as notas e pareceres da sua apresentação:
    - Se as notas NÃO foram homologadas pelo criador do evento, exibe aviso de que está em avaliação.
    - Se as notas foram homologadas pelo criador, exibe a nota final, critérios e comentários dos tutores.
    """
    trabalho = AmostraService.obter_resultado_aluno(inscricao_id)
    if not trabalho:
        raise HTTPException(status_code=404, detail="Apresentação não encontrada.")

    return templates.TemplateResponse("amostra_resultado.html", {
        "request": request,
        "trabalho": trabalho
    })


# ============================================================================
# 3. SCANNER DE QR CODE PARA CHECK-IN E LOCALIZAÇÃO DE PROJETOS
# ============================================================================

class QRCheckinPayload(BaseModel):
    codigo: str


@app.get("/scanner", response_class=HTMLResponse)
async def scanner_geral(request: Request, evento_id: int = Query(None)):
    """
    Página do scanner de QR Code via câmera do celular ou upload de imagem.
    Permite aos professores organizadores lerem o QR Code do aluno, localizarem o projeto
    e registrarem o check-in instantâneo de presença.
    """
    evento = None
    if evento_id:
        evento = EventoService.buscar_por_id(evento_id)

    return templates.TemplateResponse("scanner.html", {
        "request": request,
        "evento": evento,
        "evento_id": evento_id
    })


@app.post("/api/checkin/qr")
async def api_checkin_qr(payload: QRCheckinPayload):
    """
    Endpoint assíncrono para o Scanner de QR Code:
    Recebe o código escaneado via câmera e realiza a busca e credenciamento imediato.
    """
    resultado = InscricaoService.registrar_checkin_por_codigo(payload.codigo)
    return JSONResponse(content=resultado)


# ============================================================================
# 4. ROTAS DO PROFESSOR TUTOR (LANÇAMENTO DE NOTAS VIA APLICAÇÃO WEB)
# ============================================================================

@app.get("/tutor/avaliacoes", response_class=HTMLResponse)
async def portal_tutor(request: Request, tutor_id: int = Query(None)):
    """
    Portal onde o Professor Tutor visualiza os trabalhos e apresentações designados para ele.
    Verifica se o usuário está logado e, caso seja Professor Tutor, auto-seleciona seu cadastro.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario:
        return RedirectResponse(
            url="/login?next=/tutor/avaliacoes&erro=Efetue login com suas credenciais para acessar a área de tutoria.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Permite acesso para Professor Tutor e Gestor Geral
    if usuario.get("perfil") not in ["Professor Tutor", "Gestor", "Coordenador"]:
        return RedirectResponse(
            url="/?erro=Acesso restrito: seu perfil atual é de 'Usuário Base'. Solicite a promoção para Professor Tutor ao Gestor.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    tutores = TutorService.listar_todos()

    # Se logado como Professor Tutor e não passou tutor_id na URL, auto-seleciona pelo e-mail
    if not tutor_id and usuario.get("perfil") == "Professor Tutor":
        for t in tutores:
            if t["email"].strip().lower() == usuario["email"].strip().lower():
                tutor_id = t["id"]
                break

    trabalhos_atribuidos = []
    tutor_selecionado = None

    if tutor_id:
        tutor_selecionado = TutorService.buscar_por_id(tutor_id)
        trabalhos_atribuidos = AmostraService.listar_trabalhos_atribuidos_ao_tutor(tutor_id)

    return templates.TemplateResponse("tutor_avaliacoes.html", {
        "request": request,
        "usuario_logado": usuario,
        "tutores": tutores,
        "tutor_id": tutor_id,
        "tutor_selecionado": tutor_selecionado,
        "trabalhos": trabalhos_atribuidos
    })


@app.get("/tutor/avaliar/{inscricao_id}", response_class=HTMLResponse)
async def formulario_avaliacao_tutor(request: Request, inscricao_id: int, tutor_id: int = Query(...)):
    """
    Formulário para o professor tutor atribuir notas aos critérios (1 a 5)
    e registrar seu parecer/feedback técnico sobre a apresentação.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario:
        return RedirectResponse(url=f"/login?next=/tutor/avaliar/{inscricao_id}?tutor_id={tutor_id}", status_code=status.HTTP_303_SEE_OTHER)

    tutor = TutorService.buscar_por_id(tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor não localizado.")

    trabalho = AmostraService.obter_resultado_aluno(inscricao_id)
    if not trabalho:
        raise HTTPException(status_code=404, detail="Trabalho não localizado.")

    # Busca avaliação prévia se já preenchida utilizando sintaxe segura MySQL (%s)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nota_dominio, nota_clareza, nota_relevancia, nota_media, comentarios
        FROM avaliacoes_apresentacao
        WHERE inscricao_id = %s AND tutor_id = %s;
    """, (inscricao_id, tutor_id))
    avaliacao_existente = cursor.fetchone()
    conn.close()

    return templates.TemplateResponse("tutor_avaliar_form.html", {
        "request": request,
        "usuario_logado": usuario,
        "tutor": tutor,
        "trabalho": trabalho,
        "avaliacao": avaliacao_existente
    })


@app.post("/tutor/avaliar/{inscricao_id}")
async def salvar_avaliacao_tutor(
    request: Request,
    inscricao_id: int,
    tutor_id: int = Form(...),
    nota_dominio: float = Form(...),
    nota_clareza: float = Form(...),
    nota_relevancia: float = Form(...),
    comentarios: str = Form("")
):
    """
    Persiste as notas do professor tutor.
    As notas ficam salvas no sistema e aguardam validação final pelo criador do evento.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    AmostraService.salvar_avaliacao_tutor(
        inscricao_id, tutor_id, nota_dominio, nota_clareza, nota_relevancia, comentarios
    )
    return RedirectResponse(
        url=f"/tutor/avaliacoes?tutor_id={tutor_id}&sucesso=1",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ============================================================================
# 5. GESTÃO DE EVENTOS DE AMOSTRA, DESIGNAÇÃO DE TUTORES E HOMOLOGAÇÃO DE NOTAS
# ============================================================================

@app.get("/gestao/evento/{evento_id}/amostra", response_class=HTMLResponse)
async def gestao_amostra(request: Request, evento_id: int):
    """
    Painel exclusivo do criador/organizador da Amostra:
    - Define a quantidade desejada de tutores por trabalho
    - Designa os professores tutores para as bancas
    - Acompanha as notas lançadas em tempo real
    - Valida e Homologa as notas para torná-las visíveis online para os alunos
    """
    usuario = obter_usuario_sessao(request)
    if not usuario:
        return RedirectResponse(
            url=f"/login?next=/gestao/evento/{evento_id}/amostra&erro=Efetue login com o perfil de Gestor para acessar.",
            status_code=status.HTTP_303_SEE_OTHER
        )
    if usuario.get("perfil") != "Gestor":
        return RedirectResponse(
            url="/?erro=Acesso restrito: apenas o Gestor pode configurar bancas e homologar notas.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    evento = EventoService.buscar_por_id(evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    apresentacoes = AmostraService.listar_apresentacoes_evento(evento_id)
    todos_tutores = TutorService.listar_todos()

    return templates.TemplateResponse("gestao_amostra.html", {
        "request": request,
        "usuario_logado": usuario,
        "evento": evento,
        "apresentacoes": apresentacoes,
        "tutores": todos_tutores
    })


@app.post("/gestao/evento/{evento_id}/amostra/configurar-tutores")
async def configurar_tutores_amostra(
    request: Request,
    evento_id: int,
    qtd_tutores_por_trabalho: int = Form(...)
):
    """
    Permite ao criador estipular a quantidade de tutores que quer para cada apresentação.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") != "Gestor":
        raise HTTPException(status_code=403, detail="Acesso restrito ao Gestor.")

    AmostraService.definir_qtd_tutores_evento(evento_id, qtd_tutores_por_trabalho)
    return RedirectResponse(url=f"/gestao/evento/{evento_id}/amostra", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/gestao/evento/{evento_id}/amostra/designar-tutor")
async def designar_tutor_banca(
    request: Request,
    evento_id: int,
    inscricao_id: int = Form(...),
    tutor_id: int = Form(...)
):
    """
    O criador do evento associa um professor tutor à banca da apresentação do aluno.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") != "Gestor":
        raise HTTPException(status_code=403, detail="Acesso restrito ao Gestor.")

    AmostraService.designar_tutor(evento_id, inscricao_id, tutor_id)
    return RedirectResponse(url=f"/gestao/evento/{evento_id}/amostra", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/gestao/evento/{evento_id}/amostra/remover-tutor")
async def remover_tutor_banca(
    request: Request,
    evento_id: int,
    banca_id: int = Form(...)
):
    """
    Remove um tutor da banca de avaliação.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") != "Gestor":
        raise HTTPException(status_code=403, detail="Acesso restrito ao Gestor.")

    AmostraService.remover_tutor_banca(banca_id)
    return RedirectResponse(url=f"/gestao/evento/{evento_id}/amostra", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/gestao/inscricao/{inscricao_id}/homologar-notas")
async def homologar_notas_trabalho(
    request: Request,
    inscricao_id: int,
    evento_id: int = Query(...)
):
    """
    Ação do criador do evento para validar as notas da apresentação individual:
    Oficializa a média dos tutores e disponibiliza as notas para o aluno ver online.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") != "Gestor":
        raise HTTPException(status_code=403, detail="Acesso restrito ao Gestor.")

    try:
        AmostraService.homologar_notas_trabalho(inscricao_id)
    except ValueError as erro:
        print(f"[app.py] Erro ao homologar: {erro}")
    return RedirectResponse(url=f"/gestao/evento/{evento_id}/amostra", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/gestao/evento/{evento_id}/homologar-todas-notas")
async def homologar_todas_notas_evento(
    request: Request,
    evento_id: int
):
    """
    Ação em lote do criador para validar e homologar todas as notas da Amostra de uma vez.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") != "Gestor":
        raise HTTPException(status_code=403, detail="Acesso restrito ao Gestor.")

    AmostraService.homologar_todas_notas_evento(evento_id)
    return RedirectResponse(url=f"/gestao/evento/{evento_id}/amostra", status_code=status.HTTP_303_SEE_OTHER)


# ============================================================================
# 6. ROTAS DE CERTIFICAÇÃO E VALIDAÇÃO PÚBLICA
# ============================================================================

@app.get("/validar-certificado", response_class=HTMLResponse)
async def validar_certificado(request: Request, codigo: str = Query(None)):
    """
    Interface pública de validação de autenticidade de certificados por código hash.
    """
    cert = None
    if codigo:
        cert = CertificadoService.validar_certificado(codigo)

    return templates.TemplateResponse("validar_certificado.html", {
        "request": request,
        "codigo": codigo,
        "cert": cert
    })


@app.get("/certificado/{codigo_autenticidade}", response_class=HTMLResponse)
async def visualizar_certificado(request: Request, codigo_autenticidade: str):
    """
    Exibe o certificado oficial digital formatado com selo de autenticidade para impressão.
    """
    cert = CertificadoService.validar_certificado(codigo_autenticidade)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado inválido ou não encontrado.")

    return templates.TemplateResponse("certificado_view.html", {
        "request": request,
        "cert": cert
    })


# ============================================================================
# 7. ROTAS ADMINISTRATIVAS: GESTÃO DE EVENTOS (CRUD)
# ============================================================================

@app.get("/gestao", response_class=HTMLResponse)
async def painel_gestao(request: Request):
    """
    Painel de controle para coordenadores e professores organizadores.
    Lista todos os eventos cadastrados e status de ocupação.
    Verifica se o usuário logado possui privilégios de 'Gestor' ou 'Coordenador'.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario:
        return RedirectResponse(
            url="/login?next=/gestao&erro=Faça login com perfil de Gestor para acessar o painel de controle.",
            status_code=status.HTTP_303_SEE_OTHER
        )
    if usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        return RedirectResponse(
            url="/?erro=Acesso restrito: seu perfil de 'Usuário Base' não possui permissão para gerenciar eventos.",
            status_code=status.HTTP_303_SEE_OTHER
        )

    eventos = EventoService.listar_todos()
    return templates.TemplateResponse("gestao_eventos.html", {
        "request": request,
        "usuario_logado": usuario,
        "eventos": eventos
    })


@app.get("/gestao/evento/novo", response_class=HTMLResponse)
async def formulario_novo_evento(request: Request):
    """
    Exibe o formulário de cadastro de um novo evento ou curso.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        return RedirectResponse(url="/login?next=/gestao/evento/novo", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("evento_form.html", {
        "request": request,
        "usuario_logado": usuario,
        "evento": None
    })


@app.post("/gestao/evento/novo")
async def salvar_novo_evento(
    request: Request,
    titulo: str = Form(...),
    descricao: str = Form(...),
    categoria: str = Form(...),
    modalidade: str = Form(...),
    local_link: str = Form(...),
    data_inicio: str = Form(...),
    data_fim: str = Form(...),
    carga_horaria: int = Form(...),
    vagas_totais: int = Form(...),
    palestrante: str = Form(...),
    permite_apresentacao: int = Form(0),
    qtd_tutores_por_trabalho: int = Form(2),
    status: str = Form("Inscrições Abertas")
):
    """
    Persiste um novo evento no banco de dados MySQL.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        raise HTTPException(status_code=403, detail="Acesso negado para criação de eventos.")

    dados = {
        "titulo": titulo,
        "descricao": descricao,
        "categoria": categoria,
        "modalidade": modalidade,
        "local_link": local_link,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "carga_horaria": carga_horaria,
        "vagas_totais": vagas_totais,
        "palestrante": palestrante,
        "permite_apresentacao": permite_apresentacao,
        "qtd_tutores_por_trabalho": qtd_tutores_por_trabalho,
        "status": status
    }
    novo_id = EventoService.criar_evento(dados)
    return RedirectResponse(url="/gestao", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/gestao/evento/{evento_id}/editar", response_class=HTMLResponse)
async def formulario_editar_evento(request: Request, evento_id: int):
    """
    Carrega o formulário preenchido para edição de um evento existente.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        return RedirectResponse(url=f"/login?next=/gestao/evento/{evento_id}/editar", status_code=status.HTTP_303_SEE_OTHER)

    evento = EventoService.buscar_por_id(evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    return templates.TemplateResponse("evento_form.html", {
        "request": request,
        "usuario_logado": usuario,
        "evento": evento
    })


@app.post("/gestao/evento/{evento_id}/editar")
async def salvar_edicao_evento(
    request: Request,
    evento_id: int,
    titulo: str = Form(...),
    descricao: str = Form(...),
    categoria: str = Form(...),
    modalidade: str = Form(...),
    local_link: str = Form(...),
    data_inicio: str = Form(...),
    data_fim: str = Form(...),
    carga_horaria: int = Form(...),
    vagas_totais: int = Form(...),
    palestrante: str = Form(...),
    permite_apresentacao: int = Form(0),
    qtd_tutores_por_trabalho: int = Form(2),
    status: str = Form(...)
):
    """
    Salva as alterações de um evento existente no MySQL.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        raise HTTPException(status_code=403, detail="Acesso negado para edição.")

    dados = {
        "titulo": titulo,
        "descricao": descricao,
        "categoria": categoria,
        "modalidade": modalidade,
        "local_link": local_link,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "carga_horaria": carga_horaria,
        "vagas_totais": vagas_totais,
        "palestrante": palestrante,
        "permite_apresentacao": permite_apresentacao,
        "qtd_tutores_por_trabalho": qtd_tutores_por_trabalho,
        "status": status
    }
    EventoService.atualizar_evento(evento_id, dados)
    return RedirectResponse(url="/gestao", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/gestao/evento/{evento_id}/excluir")
async def excluir_evento(request: Request, evento_id: int):
    """
    Remove um evento e suas inscrições associadas do banco de dados MySQL.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") != "Gestor":
        raise HTTPException(status_code=403, detail="Acesso restrito ao Gestor Geral.")

    EventoService.excluir_evento(evento_id)
    return RedirectResponse(url="/gestao", status_code=status.HTTP_303_SEE_OTHER)


# ============================================================================
# 8. ROTAS DE CONTROLE DE PARTICIPANTES, PRESENÇA (CHECK-IN) E CERTIFICAÇÃO
# ============================================================================

@app.get("/gestao/evento/{evento_id}/participantes", response_class=HTMLResponse)
async def gerenciar_participantes(request: Request, evento_id: int):
    """
    Lista todos os participantes inscritos em um determinado evento.
    Permite registrar presença (Check-in), emitir certificados ou cancelar inscrições.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        return RedirectResponse(url=f"/login?next=/gestao/evento/{evento_id}/participantes", status_code=status.HTTP_303_SEE_OTHER)

    evento = EventoService.buscar_por_id(evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    inscritos = InscricaoService.listar_por_evento(evento_id)
    return templates.TemplateResponse("participantes.html", {
        "request": request,
        "usuario_logado": usuario,
        "evento": evento,
        "inscritos": inscritos
    })


@app.post("/gestao/inscricao/{inscricao_id}/checkin")
async def registrar_checkin(
    request: Request,
    inscricao_id: int,
    retorno: str = Query("/gestao")
):
    """
    Registra a presença do participante no dia do evento (Credenciamento / Check-in).
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador", "Professor Tutor"]:
        raise HTTPException(status_code=403, detail="Acesso negado para credenciamento.")

    InscricaoService.registrar_checkin(inscricao_id)
    return RedirectResponse(url=retorno, status_code=status.HTTP_303_SEE_OTHER)


@app.post("/gestao/inscricao/{inscricao_id}/emitir-certificado")
async def emitir_certificado(
    request: Request,
    inscricao_id: int,
    retorno: str = Query("/gestao")
):
    """
    Emite o certificado digital para participantes com presença confirmada.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        raise HTTPException(status_code=403, detail="Acesso negado para emissão.")

    try:
        CertificadoService.emitir_certificado(inscricao_id)
    except ValueError as erro:
        print(f"[app.py] Aviso ao emitir certificado: {erro}")
    return RedirectResponse(url=retorno, status_code=status.HTTP_303_SEE_OTHER)


@app.post("/gestao/inscricao/{inscricao_id}/cancelar")
async def cancelar_inscricao(
    request: Request,
    inscricao_id: int,
    retorno: str = Query("/gestao")
):
    """
    Cancela a inscrição de um participante liberando a vaga.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        raise HTTPException(status_code=403, detail="Acesso negado para cancelamento.")

    InscricaoService.cancelar_inscricao(inscricao_id)
    return RedirectResponse(url=retorno, status_code=status.HTTP_303_SEE_OTHER)


# ============================================================================
# 9. ROTAS DE RELATÓRIOS E EXPORTAÇÃO CSV
# ============================================================================

@app.get("/relatorios", response_class=HTMLResponse)
async def visualizar_relatorios(request: Request):
    """
    Dashboard de estatísticas e métricas do ecossistema de eventos.
    """
    usuario = obter_usuario_sessao(request)
    if not usuario or usuario.get("perfil") not in ["Gestor", "Coordenador"]:
        return RedirectResponse(url="/login?next=/relatorios", status_code=status.HTTP_303_SEE_OTHER)

    stats = RelatorioService.obter_estatisticas_gerais()
    return templates.TemplateResponse("relatorios.html", {
        "request": request,
        "usuario_logado": usuario,
        "stats": stats
    })


@app.get("/relatorios/exportar-todos-csv")
async def exportar_todos_csv():
    """
    Exporta todas as inscrições do sistema em formato CSV estruturado (compatível com Excel).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """
        SELECT 
            i.codigo_inscricao, e.titulo AS evento, e.categoria, e.modalidade, e.data_inicio,
            p.nome AS participante, p.cpf, p.email, p.telefone, p.tipo_participante,
            i.tipo_participacao, i.titulo_trabalho, i.nota_final, i.notas_homologadas,
            i.status AS status_inscricao, i.data_inscricao, i.data_checkin,
            c.codigo_autenticidade AS certificado
        FROM inscricoes i
        JOIN eventos e ON i.evento_id = e.id
        JOIN participantes p ON i.participante_id = p.id
        LEFT JOIN certificados c ON i.id = c.inscricao_id
        ORDER BY e.data_inicio DESC, p.nome ASC;
    """
    cursor.execute(sql)
    linhas = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        "Codigo Inscricao", "Evento", "Categoria", "Modalidade", "Data Inicio",
        "Participante", "CPF", "E-mail", "Telefone", "Tipo Participante",
        "Participacao", "Titulo Trabalho", "Nota Final Homologada", "Homologado",
        "Status Inscricao", "Data Inscricao", "Data Check-in", "Codigo Certificado"
    ])
    for l in linhas:
        writer.writerow([
            l["codigo_inscricao"], l["evento"], l["categoria"], l["modalidade"], l["data_inicio"],
            l["participante"], l["cpf"], l["email"], l["telefone"], l["tipo_participante"],
            l["tipo_participacao"], l["titulo_trabalho"] or "", l["nota_final"] or "Sem Nota",
            "Sim" if l["notas_homologadas"] == 1 else "Nao",
            l["status_inscricao"], l["data_inscricao"], l["data_checkin"], l["certificado"] or "Nao Emitido"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=relatorio_geral_eventos_2026.csv"}
    )


@app.get("/relatorios/evento/{evento_id}/exportar-csv")
async def exportar_evento_csv(evento_id: int):
    """
    Exporta a lista de inscritos e presenças de um evento específico em CSV.
    """
    evento = EventoService.buscar_por_id(evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    inscritos = InscricaoService.listar_por_evento(evento_id)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Codigo", "Nome", "CPF", "Email", "Telefone", "Categoria", "Tipo", "Trabalho", "Nota Final", "Status", "Data Check-in", "Certificado"])
    for p in inscritos:
        writer.writerow([
            p["codigo_inscricao"], p["nome"], p["cpf"], p["email"], p["telefone"],
            p["tipo_participante"], p["tipo_participacao"], p["titulo_trabalho"] or "",
            p["nota_final"] or "Sem Nota",
            p["status_inscricao"], p["data_checkin"] or "",
            p["certificado_codigo"] or "Nao Emitido"
        ])

    output.seek(0)
    nome_arquivo = f"inscritos_evento_{evento_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )


# ============================================================================
# PONTO DE ENTRADA PRINCIPAL PARA EXECUÇÃO DIRETA (python app.py)
# Configurado para escutar em todas as interfaces de rede (0.0.0.0), permitindo
# que qualquer computador ou celular conectado na rede local acesse via http://192.168.0.23:8000.
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("[UNIFACCAMP] Portal de Eventos e Amostras Acadêmicas")
    print("Servidor iniciado com sucesso e disponível nas seguintes interfaces:")
    print("👉 Acesso neste computador (Local):      http://localhost:8000")
    print("👉 Acesso por outros aparelhos na rede:  http://192.168.0.23:8000")
    print("=" * 70)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

