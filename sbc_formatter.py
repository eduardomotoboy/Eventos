# -*- coding: utf-8 -*-
r"""
Arquivo: sbc_formatter.py
Projeto: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
Descrição: Motor de formatação automática de trabalhos acadêmicos no padrão oficial
           da Sociedade Brasileira de Computação (SBC - sbc_template.pdf / sbc-template.sty).
           Utiliza exclusivamente o conteúdo presente no próprio documento enviado,
           sem acrescentar textos ou metadados externos ao documento.
"""

import os
import io
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle,
    KeepTogether
)
from reportlab.lib import colors


class SBCFormatterService:
    """
    Converte arquivos enviados pelos alunos (.docx, .odt, .pdf, .txt, .md ou imagens)
    para um documento PDF rigorosamente diagramado no padrão SBC (sbc_template.pdf),
    preservando estritamente apenas o conteúdo original do próprio documento.
    """

    TEXT_WIDTH = 15.0 * cm
    MAX_IMG_WIDTH = 12.5 * cm
    MAX_IMG_HEIGHT = 8.5 * cm

    @staticmethod
    def _criar_estilos_sbc() -> dict:
        """
        Define todos os estilos tipográficos oficiais do pacote sbc-template.sty.
        """
        return {
            "titulo": ParagraphStyle(
                name="SBC_Title",
                fontName="Times-Bold",
                fontSize=16,
                leading=20,
                alignment=TA_CENTER,
                spaceBefore=12,
                spaceAfter=12,
            ),
            "autores": ParagraphStyle(
                name="SBC_Authors",
                fontName="Times-Bold",
                fontSize=12,
                leading=14,
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=12,
            ),
            "endereco": ParagraphStyle(
                name="SBC_Address",
                fontName="Times-Roman",
                fontSize=12,
                leading=14,
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=4,
            ),
            "email": ParagraphStyle(
                name="SBC_Email",
                fontName="Courier",
                fontSize=10,
                leading=12,
                alignment=TA_CENTER,
                spaceBefore=6,
                spaceAfter=12,
            ),
            "resumo": ParagraphStyle(
                name="SBC_Abstract",
                fontName="Times-Italic",
                fontSize=12,
                leading=14,
                alignment=TA_JUSTIFY,
                leftIndent=0.8 * cm,
                rightIndent=0.8 * cm,
                spaceBefore=6,
                spaceAfter=6,
            ),
            "secao": ParagraphStyle(
                name="SBC_Section",
                fontName="Times-Bold",
                fontSize=13,
                leading=17,
                alignment=TA_LEFT,
                spaceBefore=14,
                spaceAfter=6,
                keepWithNext=True,
            ),
            "subsecao": ParagraphStyle(
                name="SBC_Subsection",
                fontName="Times-Bold",
                fontSize=12,
                leading=14,
                alignment=TA_LEFT,
                spaceBefore=10,
                spaceAfter=4,
                keepWithNext=True,
            ),
            "paragrafo_primeiro": ParagraphStyle(
                name="SBC_FirstParagraph",
                fontName="Times-Roman",
                fontSize=12,
                leading=14,
                alignment=TA_JUSTIFY,
                firstLineIndent=0,
                spaceBefore=6,
                spaceAfter=0,
            ),
            "paragrafo_indentado": ParagraphStyle(
                name="SBC_IndentedParagraph",
                fontName="Times-Roman",
                fontSize=12,
                leading=14,
                alignment=TA_JUSTIFY,
                firstLineIndent=1.27 * cm,
                spaceBefore=6,
                spaceAfter=0,
            ),
            "item_lista": ParagraphStyle(
                name="SBC_ListItem",
                fontName="Times-Roman",
                fontSize=12,
                leading=14,
                alignment=TA_JUSTIFY,
                leftIndent=1.27 * cm,
                firstLineIndent=0,
                spaceBefore=4,
                spaceAfter=0,
            ),
            "legenda_curta": ParagraphStyle(
                name="SBC_CaptionShort",
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=12,
                alignment=TA_CENTER,
                spaceBefore=6,
                spaceAfter=6,
            ),
            "legenda_longa": ParagraphStyle(
                name="SBC_CaptionLong",
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=12,
                alignment=TA_JUSTIFY,
                leftIndent=0.8 * cm,
                rightIndent=0.8 * cm,
                spaceBefore=6,
                spaceAfter=6,
            ),
            "referencia": ParagraphStyle(
                name="SBC_Reference",
                fontName="Times-Roman",
                fontSize=12,
                leading=14,
                alignment=TA_JUSTIFY,
                leftIndent=0.5 * cm,
                firstLineIndent=-0.5 * cm,
                spaceBefore=6,
                spaceAfter=0,
            ),
        }

    @staticmethod
    def _higienizar_texto(texto: str) -> str:
        if not texto:
            return ""
        limpo = re.sub(r"[ \t\xa0]{2,}", " ", texto.replace("\xa0", " ").strip())
        return escape(limpo)

    @staticmethod
    def _formatar_autores_sbc(texto_autores: str) -> str:
        escapado = SBCFormatterService._higienizar_texto(texto_autores)
        return re.sub(r"([A-Za-zÀ-ÿ])(\d+(?:,\d+)*)(?=\s*,|\s*$)", r"\1<super>\2</super>", escapado)

    @staticmethod
    def _formatar_endereco_sbc(texto_endereco: str) -> str:
        escapado = SBCFormatterService._higienizar_texto(texto_endereco)
        return re.sub(r"^(\d+)([A-Za-zÀ-ÿ])", r"<super>\1</super>\2", escapado)

    @staticmethod
    def _criar_flowable_imagem(img_bytes: bytes, legenda: str, estilos: dict) -> list:
        elementos = []
        try:
            bio = io.BytesIO(img_bytes)
            with PILImage.open(bio) as pil_img:
                largura_px, altura_px = pil_img.size
                if pil_img.mode not in ("RGB", "L"):
                    pil_img = pil_img.convert("RGB")
                out_bio = io.BytesIO()
                pil_img.save(out_bio, format="JPEG", quality=90)
                out_bio.seek(0)

            if largura_px <= 0 or altura_px <= 0:
                return []

            largura_pt = largura_px * 0.75
            altura_pt = altura_px * 0.75

            escala_w = SBCFormatterService.MAX_IMG_WIDTH / largura_pt if largura_pt > SBCFormatterService.MAX_IMG_WIDTH else 1.0
            escala_h = SBCFormatterService.MAX_IMG_HEIGHT / altura_pt if altura_pt > SBCFormatterService.MAX_IMG_HEIGHT else 1.0
            escala = min(escala_w, escala_h)

            largura_final = largura_pt * escala
            altura_final = altura_pt * escala

            rl_img = RLImage(out_bio, width=largura_final, height=altura_final)
            rl_img.hAlign = "CENTER"

            bloco = [Spacer(1, 6), rl_img]
            if legenda:
                legenda_limpa = SBCFormatterService._higienizar_texto(legenda)
                estilo_leg = estilos["legenda_curta"] if len(legenda_limpa) <= 75 else estilos["legenda_longa"]
                bloco.append(Paragraph(legenda_limpa, estilo_leg))
            bloco.append(Spacer(1, 6))
            elementos.append(KeepTogether(bloco))
        except Exception:
            pass
        return elementos

    @staticmethod
    def _extrair_elementos_docx(conteudo_bytes: bytes) -> list:
        itens = []
        ns = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        }
        rel_attr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

        with zipfile.ZipFile(io.BytesIO(conteudo_bytes)) as zf:
            nomes_zip = set(zf.namelist())
            if "word/document.xml" not in nomes_zip:
                return itens

            rels_map = {}
            if "word/_rels/document.xml.rels" in nomes_zip:
                rels_root = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
                for rel in rels_root:
                    r_id = rel.attrib.get("Id")
                    target = rel.attrib.get("Target", "")
                    if r_id and target:
                        caminho_zip = "word/" + target.lstrip("/") if not target.startswith("word/") else target
                        rels_map[r_id] = caminho_zip

            doc_root = ET.fromstring(zf.read("word/document.xml"))
            body = doc_root.find("w:body", ns)
            if body is None:
                return itens

            for elem in body:
                tag_local = elem.tag.split("}")[-1]
                if tag_local == "p":
                    buffer_texto = []
                    for sub in elem.iter():
                        sub_tag = sub.tag.split("}")[-1]
                        if sub_tag == "t" and sub.text:
                            buffer_texto.append(sub.text)
                        elif sub_tag == "blip":
                            texto_acumulado = "".join(buffer_texto).strip()
                            if texto_acumulado:
                                itens.append({"tipo": "texto", "texto": texto_acumulado})
                                buffer_texto = []
                            r_id = sub.attrib.get(rel_attr)
                            caminho_img = rels_map.get(r_id, "")
                            if caminho_img in nomes_zip:
                                itens.append({"tipo": "imagem", "bytes": zf.read(caminho_img)})
                    texto_restante = "".join(buffer_texto).strip()
                    if texto_restante:
                        itens.append({"tipo": "texto", "texto": texto_restante})

                elif tag_local == "tbl":
                    linhas_tabela = []
                    for tr in elem.findall(".//w:tr", ns):
                        celulas = []
                        for tc in tr.findall(".//w:tc", ns):
                            txt_cel = "".join(t.text for t in tc.findall(".//w:t", ns) if t.text).strip()
                            celulas.append(txt_cel)
                        if any(celulas):
                            linhas_tabela.append(celulas)
                    if linhas_tabela:
                        itens.append({"tipo": "tabela", "linhas": linhas_tabela})

        return itens

    @staticmethod
    def _extrair_elementos_odt(conteudo_bytes: bytes) -> list:
        itens = []
        with zipfile.ZipFile(io.BytesIO(conteudo_bytes)) as zf:
            if "content.xml" not in zf.namelist():
                return itens
            root = ET.fromstring(zf.read("content.xml"))
            for elem in root.iter():
                if elem.tag.endswith("}p") or elem.tag.endswith("}h"):
                    txt = "".join(elem.itertext()).strip()
                    if txt:
                        itens.append({"tipo": "texto", "texto": txt})
        return itens

    @staticmethod
    def _pdf_ja_esta_no_padrao_sbc(conteudo_bytes: bytes) -> bool:
        """
        Verifica se um arquivo PDF enviado pelo aluno já está diagramado no padrão de artigo SBC
        (possui Abstract/Resumo na 1ª página e seções numeradas 1. ..., 2. ...).
        Quando verdadeiro, preserva a paginação, diagramas vetoriais e figuras originais do PDF.
        """
        try:
            from pypdf import PdfReader
            leitor = PdfReader(io.BytesIO(conteudo_bytes))
            if len(leitor.pages) == 0:
                return False
            texto_p1 = (leitor.pages[0].extract_text() or "").strip()
            texto_completo = "\n".join((p.extract_text() or "") for p in leitor.pages)

            tem_resumo_p1 = bool(re.search(r"\b(Abstract|Resumo)\s*[\.:]", texto_p1, re.IGNORECASE))
            tem_secao_1 = bool(re.search(r"(?m)^\s*1\.\s+\S+", texto_completo))
            return tem_resumo_p1 and tem_secao_1
        except Exception:
            return False

    @staticmethod
    def _reconstruir_paragrafos_de_linhas_pdf(linhas_brutas: list) -> list:
        """
        Em arquivos PDF não-SBC onde o texto é extraído linha por linha visual,
        agrupa linhas quebradas de um mesmo parágrafo para não indentar cada linha individualmente.
        """
        paragrafos = []
        buffer = ""
        em_cabecalho = True
        em_referencias = False

        for linha in linhas_brutas:
            limpa = re.sub(r"[ \t\xa0]+", " ", linha.replace("\xa0", " ")).strip()
            if not limpa:
                continue
            # Ignora rótulos isolados de subfiguras como (a), (b), (c)
            if re.match(r"^(\([a-z]\)\s*)+$", limpa, re.IGNORECASE):
                continue

            # Detecta início de Abstract / Resumo / Seções / Legendas / Referências
            eh_inicio_abs = bool(re.match(r"^(Abstract|Resumo)\s*[\.:]", limpa, re.IGNORECASE))
            eh_secao = bool(re.match(r"^\d+(\.\d+)?\.?\s+[A-ZÀ-Ÿ]", limpa) and len(limpa) < 120)
            eh_ref_titulo = bool(re.match(r"^(\d+\.\s*)?(Refer[êe]ncias(\s+Bibliogr[áa]ficas)?|Refer[êe]ncia\s+Bibliogr[áa]fica|References)\s*$", limpa, re.IGNORECASE))
            eh_legenda = bool(re.match(r"^(Figura|Figure|Tabela|Table)\s+\d+[\.:]", limpa, re.IGNORECASE))
            eh_item_lista = limpa.startswith(("•", "-", "*"))

            if eh_inicio_abs or eh_secao or eh_ref_titulo:
                em_cabecalho = False
            if eh_ref_titulo:
                em_referencias = True

            if em_cabecalho:
                # No cabeçalho (antes de Abstract/Resumo/1. Seção), se a linha anterior
                # não terminou com pontuação e a próxima continua título/endereço, junta se for título
                if (
                    paragrafos
                    and len(paragrafos) == 1
                    and not re.search(r"\d", limpa)
                    and "@" not in limpa
                ):
                    paragrafos[0] = f"{paragrafos[0]} {limpa}"
                else:
                    paragrafos.append(limpa)
                continue

            if eh_inicio_abs or eh_secao or eh_ref_titulo or eh_legenda or eh_item_lista:
                if buffer:
                    paragrafos.append(buffer)
                    buffer = ""
                if eh_secao or eh_ref_titulo or eh_legenda or eh_item_lista:
                    paragrafos.append(limpa)
                else:
                    buffer = limpa
                continue

            if em_referencias:
                # Nova referência geralmente começa com Sobrenome/Entidade seguido de (Ano)
                eh_nova_ref = bool(re.match(r"^[A-ZÀ-Ÿ][^\(\n]{1,60}\(\d{4}[a-z]?\)", limpa))
                if eh_nova_ref:
                    if buffer:
                        paragrafos.append(buffer)
                    buffer = limpa
                else:
                    buffer = f"{buffer} {limpa}".strip() if buffer else limpa
                continue

            # Corpo do texto e Abstract/Resumo: junta linhas até fechar parágrafo
            if not buffer:
                buffer = limpa
            else:
                if buffer.endswith("-"):
                    buffer = buffer[:-1] + limpa
                else:
                    buffer = f"{buffer} {limpa}"

            # Se a linha termina em ponto final e é significativamente mais curta que uma linha cheia,
            # ou se o próximo bloco iniciar seção, fecha o parágrafo
            if limpa.endswith((".", ":", "!", "?")) and len(limpa) < 72:
                paragrafos.append(buffer)
                buffer = ""

        if buffer:
            paragrafos.append(buffer)

        return [{"tipo": "texto", "texto": p} for p in paragrafos]

    @staticmethod
    def _extrair_elementos_pdf(conteudo_bytes: bytes) -> list:
        itens_linhas = []
        try:
            from pypdf import PdfReader
            leitor = PdfReader(io.BytesIO(conteudo_bytes))
            for pagina in leitor.pages:
                texto_pag = pagina.extract_text() or ""
                for linha in texto_pag.splitlines():
                    if linha.strip():
                        itens_linhas.append(linha)
        except Exception:
            pass
        return SBCFormatterService._reconstruir_paragrafos_de_linhas_pdf(itens_linhas)

    @staticmethod
    def _montar_story_sbc(itens_extraidos: list, estilos: dict) -> list:
        """
        Transforma exclusivamente os elementos presentes no documento enviado
        em Flowables no padrão SBC, sem acrescentar nenhum texto externo.
        """
        story = []

        textos_iniciais = [it["texto"] for it in itens_extraidos[:10] if it["tipo"] == "texto"]
        tem_abstract_ou_resumo = any(
            re.match(r"^(abstract|resumo)\b", t.strip(), re.IGNORECASE)
            for it in itens_extraidos[:15]
            if it["tipo"] == "texto"
            for t in [it["texto"]]
        )

        idx_inicio_corpo = 0

        if tem_abstract_ou_resumo and len(textos_iniciais) >= 2:
            # Identifica onde está a linha de autores (contém vírgulas ou sobrescritos de afiliação antes do endereço/email)
            idx_autores = 1
            for k in range(1, min(4, len(itens_extraidos))):
                if itens_extraidos[k]["tipo"] != "texto":
                    break
                candidato = itens_extraidos[k]["texto"].strip()
                if re.search(r"[A-Za-zÀ-ÿ]\d", candidato) or ("," in candidato and "@" not in candidato and not candidato[0].isdigit()):
                    idx_autores = k
                    break

            # Junta linhas do título caso o título ocupe mais de um parágrafo antes dos autores
            partes_titulo = [
                itens_extraidos[k]["texto"].strip()
                for k in range(0, idx_autores)
                if itens_extraidos[k]["tipo"] == "texto"
            ]
            titulo_doc = " ".join(partes_titulo)
            story.append(Paragraph(SBCFormatterService._higienizar_texto(titulo_doc), estilos["titulo"]))

            for i in range(idx_autores, len(itens_extraidos)):
                item = itens_extraidos[i]
                if item["tipo"] != "texto":
                    idx_inicio_corpo = i
                    break
                txt = item["texto"].strip()
                if re.match(r"^(abstract|resumo)\b", txt, re.IGNORECASE) or re.match(r"^\d+\.\s+", txt):
                    idx_inicio_corpo = i
                    break
                if "@" in txt:
                    story.append(Paragraph(SBCFormatterService._higienizar_texto(txt), estilos["email"]))
                elif i == idx_autores:
                    story.append(Paragraph(SBCFormatterService._formatar_autores_sbc(txt), estilos["autores"]))
                else:
                    story.append(Paragraph(SBCFormatterService._formatar_endereco_sbc(txt), estilos["endereco"]))
        elif textos_iniciais and len(textos_iniciais[0]) < 220 and not re.match(r"^\d+\.\s+", textos_iniciais[0]):
            story.append(Paragraph(SBCFormatterService._higienizar_texto(textos_iniciais[0]), estilos["titulo"]))
            for i, item in enumerate(itens_extraidos):
                if item["tipo"] == "texto" and item["texto"].strip() == textos_iniciais[0]:
                    idx_inicio_corpo = i + 1
                    break

        primeiro_paragrafo_apos_titulo = True
        em_secao_referencias = False
        ultimo_foi_item_lista = False
        contador_figuras = 0
        contador_tabelas = 0
        legenda_pendente_imagem = None

        total_itens = len(itens_extraidos)
        i = idx_inicio_corpo
        while i < total_itens:
            item = itens_extraidos[i]

            if item["tipo"] == "imagem":
                contador_figuras += 1
                if legenda_pendente_imagem:
                    legenda_fig = f"Figura {contador_figuras}. {legenda_pendente_imagem}"
                    legenda_pendente_imagem = None
                else:
                    legenda_fig = ""
                story.extend(SBCFormatterService._criar_flowable_imagem(item["bytes"], legenda_fig, estilos))
                ultimo_foi_item_lista = False
                i += 1
                continue

            if item["tipo"] == "tabela":
                contador_tabelas += 1
                dados_tab = [
                    [Paragraph(SBCFormatterService._higienizar_texto(cel), estilos["paragrafo_primeiro"]) for cel in linha]
                    for linha in item["linhas"]
                ]
                tabela_rl = Table(dados_tab)
                tabela_rl.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(tabela_rl)
                story.append(Spacer(1, 6))
                ultimo_foi_item_lista = False
                i += 1
                continue

            txt = item["texto"].strip()
            if not txt:
                i += 1
                continue

            if (
                i + 1 < total_itens
                and itens_extraidos[i + 1]["tipo"] == "imagem"
                and len(txt) <= 80
                and not re.match(r"^\d+\.", txt)
                and not txt.endswith(".")
            ):
                legenda_pendente_imagem = txt
                i += 1
                continue

            m_abs = re.match(r"^(Abstract|Resumo)\s*[\.:—-]?\s*(.*)$", txt, re.IGNORECASE | re.DOTALL)
            if m_abs and not em_secao_referencias:
                rotulo = "Abstract" if m_abs.group(1).lower() == "abstract" else "Resumo"
                corpo_abs = m_abs.group(2).strip()
                if not corpo_abs and i + 1 < total_itens and itens_extraidos[i + 1]["tipo"] == "texto":
                    corpo_abs = itens_extraidos[i + 1]["texto"].strip()
                    i += 1
                html_abs = f"<b><i>{rotulo}.</i></b> <i>{SBCFormatterService._higienizar_texto(corpo_abs)}</i>"
                story.append(Paragraph(html_abs, estilos["resumo"]))
                ultimo_foi_item_lista = False
                i += 1
                continue

            if re.match(r"^(\d+\.\s*)?(Refer[êe]ncias(\s+Bibliogr[áa]ficas)?|Refer[êe]ncia\s+Bibliogr[áa]fica|References)\s*$", txt, re.IGNORECASE):
                em_secao_referencias = True
                story.append(Paragraph(SBCFormatterService._higienizar_texto(txt), estilos["secao"]))
                primeiro_paragrafo_apos_titulo = True
                ultimo_foi_item_lista = False
                i += 1
                continue

            if re.match(r"^\d+\.\d+\.?\s+\S+", txt) and len(txt) < 140:
                em_secao_referencias = False
                story.append(Paragraph(SBCFormatterService._higienizar_texto(txt), estilos["subsecao"]))
                primeiro_paragrafo_apos_titulo = True
                ultimo_foi_item_lista = False
                i += 1
                continue

            if re.match(r"^\d+\.\s+\S+", txt) and len(txt) < 140:
                em_secao_referencias = False
                story.append(Paragraph(SBCFormatterService._higienizar_texto(txt), estilos["secao"]))
                primeiro_paragrafo_apos_titulo = True
                ultimo_foi_item_lista = False
                i += 1
                continue

            if em_secao_referencias:
                story.append(Paragraph(SBCFormatterService._higienizar_texto(txt), estilos["referencia"]))
                ultimo_foi_item_lista = False
                i += 1
                continue

            if re.match(r"^(Figura|Figure|Tabela|Table)\s+\d+[\.:]", txt, re.IGNORECASE) and len(txt) < 220:
                estilo_leg = estilos["legenda_curta"] if len(txt) <= 75 else estilos["legenda_longa"]
                story.append(Paragraph(SBCFormatterService._higienizar_texto(txt), estilo_leg))
                ultimo_foi_item_lista = False
                i += 1
                continue

            if (
                txt.startswith(("•", "-", "*"))
                or (len(txt) < 120 and txt.endswith(";"))
                or (ultimo_foi_item_lista and len(txt) < 100 and txt[0].islower())
            ):
                texto_item = txt.lstrip("•-* ").strip()
                story.append(Paragraph(f"• {SBCFormatterService._higienizar_texto(texto_item)}", estilos["item_lista"]))
                ultimo_foi_item_lista = txt.endswith(";")
                i += 1
                continue

            estilo_par = estilos["paragrafo_primeiro"] if primeiro_paragrafo_apos_titulo else estilos["paragrafo_indentado"]
            story.append(Paragraph(SBCFormatterService._higienizar_texto(txt), estilo_par))
            primeiro_paragrafo_apos_titulo = False
            ultimo_foi_item_lista = False
            i += 1

        return story

    @staticmethod
    def gerar_pdf_padrao_sbc(
        caminho_original: str,
        caminho_destino_pdf: str,
        metadados_inscricao: dict = None
    ) -> int:
        """
        Gera o arquivo PDF diagramado no padrão SBC (sbc_template.pdf) usando
        apenas o conteúdo original do próprio documento enviado.
        """
        ext = os.path.splitext(caminho_original)[1].lower()
        with open(caminho_original, "rb") as f:
            conteudo_bytes = f.read()

        os.makedirs(os.path.dirname(os.path.abspath(caminho_destino_pdf)), exist_ok=True)

        # Se o arquivo enviado já for um PDF diagramado na estrutura SBC (com Abstract/Resumo,
        # seções numeradas e diagramas/figuras vetoriais originais), preserva o documento PDF
        # fielmente (removendo apenas páginas residuais de rascunho "TÓPICOS RELEVANTES" se houver)
        if ext == ".pdf" and SBCFormatterService._pdf_ja_esta_no_padrao_sbc(conteudo_bytes):
            try:
                from pypdf import PdfReader, PdfWriter
                leitor = PdfReader(io.BytesIO(conteudo_bytes))
                escritor = PdfWriter()
                for pag in leitor.pages:
                    txt_pag = (pag.extract_text() or "").strip()
                    # Ignora páginas de rascunho/anotações extras pós-referências ("TÓPICOS RELEVANTES")
                    if re.match(r"^T[ÓO]PICOS\s+RELEVANTES\b", txt_pag, re.IGNORECASE):
                        continue
                    escritor.add_page(pag)
                with open(caminho_destino_pdf, "wb") as f_out:
                    escritor.write(f_out)
                return os.path.getsize(caminho_destino_pdf)
            except Exception:
                shutil.copyfile(caminho_original, caminho_destino_pdf)
                return os.path.getsize(caminho_destino_pdf)

        itens_extraidos = []
        if ext == ".docx":
            itens_extraidos = SBCFormatterService._extrair_elementos_docx(conteudo_bytes)
        elif ext == ".odt":
            itens_extraidos = SBCFormatterService._extrair_elementos_odt(conteudo_bytes)
        elif ext == ".pdf":
            itens_extraidos = SBCFormatterService._extrair_elementos_pdf(conteudo_bytes)
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            itens_extraidos = [{"tipo": "imagem", "bytes": conteudo_bytes}]
        else:
            try:
                texto_decod = conteudo_bytes.decode("utf-8", errors="replace")
                for linha in texto_decod.splitlines():
                    if linha.strip():
                        itens_extraidos.append({"tipo": "texto", "texto": linha.strip()})
            except Exception:
                pass

        estilos = SBCFormatterService._criar_estilos_sbc()
        story = SBCFormatterService._montar_story_sbc(itens_extraidos, estilos)

        if not story:
            story.append(Spacer(1, 12))

        doc = SimpleDocTemplate(
            caminho_destino_pdf,
            pagesize=A4,
            topMargin=3.5 * cm,
            bottomMargin=2.5 * cm,
            leftMargin=3.0 * cm,
            rightMargin=3.0 * cm,
            title="Artigo Padrão SBC",
            subject="Trabalho Acadêmico Formatado no Padrão SBC (sbc_template.pdf)"
        )

        def _pagina_sem_numeracao(canvas, document):
            pass

        doc.build(story, onFirstPage=_pagina_sem_numeracao, onLaterPages=_pagina_sem_numeracao)
        return os.path.getsize(caminho_destino_pdf)
