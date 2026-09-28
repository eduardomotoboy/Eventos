/**
 * ============================================================================
 * ARQUIVO: static/js/app.js
 * PROJETO: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
 * DESCRIÇÃO: Scripts clientes para aprimoramento progressivo da interface:
 *            - Máscara suave e fatiamento seguro de CPF (000.000.000-00)
 *            - Suporte fluido a digitação rápida e teclados móveis (Android, iOS)
 *            - Validação oficial de CPF (Receita Federal - Módulo 11)
 *            - Máscara automática de Telefone / Celular
 *            - Confirmações de segurança para ações críticas
 *            - Atalho de impressão nativa de certificados
 * REGRA DE CONFORMIDADE: Todo o código possui comentários detalhados e explicativos.
 * ============================================================================
 */

/**
 * Formata dígitos numéricos no padrão visual de CPF: 000.000.000-00
 * Utiliza fatiamento seguro de strings para evitar problemas de regex.
 * 
 * @param {string} digitos - String contendo apenas dígitos numéricos (até 11 caracteres).
 * @returns {string} - String formatada progressivamente com pontos e traço.
 */
function formatarCPF(digitos) {
    if (!digitos) return "";
    const v = String(digitos).replace(/\D/g, "").slice(0, 11);
    if (v.length > 9) {
        return `${v.slice(0, 3)}.${v.slice(3, 6)}.${v.slice(6, 9)}-${v.slice(9)}`;
    }
    if (v.length > 6) {
        return `${v.slice(0, 3)}.${v.slice(3, 6)}.${v.slice(6)}`;
    }
    if (v.length > 3) {
        return `${v.slice(0, 3)}.${v.slice(3)}`;
    }
    return v;
}

/**
 * Validação oficial de CPF através do algoritmo dos dois dígitos verificadores
 * (Módulo 11) estabelecido pela Receita Federal do Brasil.
 * Permite opcionalmente o CPF institucional padrão do Gestor (00000000000).
 * 
 * @param {string} cpf - CPF com ou sem máscara.
 * @param {boolean} permitirAdmin - Se True, aceita o CPF padrão 00000000000 do Gestor.
 * @returns {boolean} - True se o CPF for autêntico e válido; False caso contrário.
 */
function validarCPF(cpf, permitirAdmin = true) {
    if (!cpf) return false;
    const digitos = String(cpf).replace(/\D/g, "");
    if (digitos.length !== 11) return false;

    // Exceção controlada para o Gestor institucional padrão
    if (permitirAdmin && digitos === "00000000000") {
        return true;
    }

    // Rejeita sequências formadas por dígitos repetidos (ex: 111.111.111-11)
    if (/^(\d)\1{10}$/.test(digitos)) return false;

    // 1º Dígito Verificador (pesos de 10 a 2)
    let soma1 = 0;
    for (let i = 0; i < 9; i++) {
        soma1 += parseInt(digitos.charAt(i), 10) * (10 - i);
    }
    let resto1 = (soma1 * 10) % 11;
    let d1 = (resto1 === 10 || resto1 === 11) ? 0 : resto1;
    if (d1 !== parseInt(digitos.charAt(9), 10)) return false;

    // 2º Dígito Verificador (pesos de 11 a 2)
    let soma2 = 0;
    for (let i = 0; i < 10; i++) {
        soma2 += parseInt(digitos.charAt(i), 10) * (11 - i);
    }
    let resto2 = (soma2 * 10) % 11;
    let d2 = (resto2 === 10 || resto2 === 11) ? 0 : resto2;
    return d2 === parseInt(digitos.charAt(10), 10);
}

/**
 * Formata dígitos numéricos no padrão de telefone nacional:
 * (00) 00000-0000 (celular 11 dígitos) ou (00) 0000-0000 (fixo 10 dígitos).
 * 
 * @param {string} digitos - String com apenas dígitos numéricos (até 11 caracteres).
 * @returns {string} - String formatada com DDD entre parênteses e hífen.
 */
function formatarTelefone(digitos) {
    if (!digitos) return "";
    const v = String(digitos).replace(/\D/g, "").slice(0, 11);
    if (v.length > 10) {
        return `(${v.slice(0, 2)}) ${v.slice(2, 7)}-${v.slice(7)}`;
    }
    if (v.length > 6) {
        return `(${v.slice(0, 2)}) ${v.slice(2, 6)}-${v.slice(6)}`;
    }
    if (v.length > 2) {
        return `(${v.slice(0, 2)}) ${v.slice(2)}`;
    }
    return v;
}

/**
 * Aplica máscara suave preservando a posição do cursor.
 * Não apaga campos e não bloqueia a digitação do usuário.
 * 
 * @param {HTMLInputElement} input - Elemento HTML do campo.
 * @param {Function} formatador - Função que formata a sequência de dígitos.
 */
function aplicarMascaraSuave(input, formatador) {
    const valorOriginal = input.value;
    
    // Suporte a login híbrido (CPF ou E-mail):
    // Se o usuário estiver digitando letras ou arroba, não aplica máscara de CPF
    if (input.dataset.tipoLogin === "hibrido" || /[a-zA-Z@]/.test(valorOriginal)) {
        input.style.borderColor = "";
        return;
    }

    const apenasDigitos = valorOriginal.replace(/\D/g, "").slice(0, 11);
    if (!apenasDigitos) {
        if (input.value !== "") input.value = "";
        input.style.borderColor = "";
        return;
    }

    const valorFormatado = formatador(apenasDigitos);

    if (input.value !== valorFormatado) {
        const selecaoInicio = input.selectionStart || 0;
        const digitosAntes = valorOriginal.slice(0, selecaoInicio).replace(/\D/g, "").length;

        input.value = valorFormatado;

        try {
            if (selecaoInicio >= valorOriginal.length) {
                input.setSelectionRange(valorFormatado.length, valorFormatado.length);
            } else {
                let novoCursor = 0;
                let digitosContados = 0;
                while (novoCursor < valorFormatado.length && digitosContados < digitosAntes) {
                    if (/\d/.test(valorFormatado[novoCursor])) {
                        digitosContados++;
                    }
                    novoCursor++;
                }
                input.setSelectionRange(novoCursor, novoCursor);
            }
        } catch (e) {
            // Ignora se o navegador não suportar setSelectionRange
        }
    }

    // Feedback visual somente quando o CPF estiver completo (11 dígitos)
    // Durante a digitação (1 a 10 dígitos), a borda é neutra e NÃO dá erro!
    if (apenasDigitos.length === 11) {
        if (validarCPF(apenasDigitos, true)) {
            input.style.borderColor = "#10b981"; // Verde
        } else {
            input.style.borderColor = "#ef4444"; // Vermelho
        }
    } else {
        input.style.borderColor = "";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // ------------------------------------------------------------------------
    // 1. MÁSCARA E VALIDAÇÃO DE CPF (000.000.000-00)
    // ------------------------------------------------------------------------
    const cpfInputs = document.querySelectorAll('input[name="cpf"], #cpf');

    cpfInputs.forEach(input => {
        input.setAttribute("autocomplete", "off");
        input.setAttribute("autocorrect", "off");
        input.setAttribute("autocapitalize", "off");
        input.setAttribute("spellcheck", "false");
        
        // Garante maxlength compatível com CPF formatado (14 chars)
        if (!input.dataset.tipoLogin && (!input.getAttribute("maxlength") || parseInt(input.getAttribute("maxlength")) < 14)) {
            input.setAttribute("maxlength", "14");
        }

        // Formata valor inicial se já vier pré-preenchido do servidor
        if (input.value && !/[a-zA-Z@]/.test(input.value)) {
            const digitosIniciais = input.value.replace(/\D/g, "");
            if (digitosIniciais.length > 0) {
                input.value = formatarCPF(digitosIniciais);
            }
        }

        // Evento 'input': acionado ao digitar ou colar
        input.addEventListener("input", (e) => {
            if (e.isComposing) return;
            aplicarMascaraSuave(input, formatarCPF);
        });

        // Evento 'blur': acionado quando o usuário clica fora do campo
        input.addEventListener("blur", () => {
            if (input.dataset.tipoLogin === "hibrido" && /[a-zA-Z@]/.test(input.value)) {
                return; // Não valida como CPF se for e-mail
            }
            const digitos = input.value.replace(/\D/g, "");
            if (digitos.length > 0 && digitos.length < 11) {
                input.style.borderColor = "#ef4444"; // Incompleto
            } else if (digitos.length === 11) {
                input.style.borderColor = validarCPF(digitos, true) ? "#10b981" : "#ef4444";
            } else {
                input.style.borderColor = "";
            }
        });

        // Submissão do formulário: valida sem travar com alert
        const form = input.closest("form");
        if (form && !form.dataset.cpfValidationBound) {
            form.dataset.cpfValidationBound = "true";

            form.addEventListener("submit", (e) => {
                // Se for login híbrido com e-mail, permite passar direto para validação do backend
                if (input.dataset.tipoLogin === "hibrido" && /[a-zA-Z@]/.test(input.value)) {
                    return true;
                }

                const digitos = input.value.replace(/\D/g, "");
                if (input.required || digitos.length > 0) {
                    if (digitos.length !== 11 || !validarCPF(digitos, true)) {
                        e.preventDefault();
                        input.style.borderColor = "#ef4444";
                        input.focus();
                        
                        // Mostra ou atualiza mensagem visual de aviso sem popup invasivo
                        let helper = form.querySelector(".cpf-error-msg");
                        if (!helper) {
                            helper = document.createElement("div");
                            helper.className = "cpf-error-msg";
                            helper.style.cssText = "color: #dc2626; font-size: 0.85rem; font-weight: 600; margin-top: 0.4rem; padding: 0.4rem 0.6rem; background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 4px;";
                            input.parentNode.appendChild(helper);
                        }
                        helper.textContent = (digitos.length !== 11)
                            ? "Por favor, preencha os 11 dígitos do CPF completo."
                            : "O CPF informado possui dígitos verificadores inválidos. Verifique os números informados.";
                        return false;
                    }
                }
            });
        }
    });

    // ------------------------------------------------------------------------
    // 2. MÁSCARA AUTOMÁTICA DE TELEFONE / CELULAR
    // Padrão: (00) 00000-0000 ou (00) 0000-0000
    // ------------------------------------------------------------------------
    const phoneInputs = document.querySelectorAll('input[name="telefone"], #telefone');
    phoneInputs.forEach(input => {
        input.setAttribute("maxlength", "15");

        if (input.value) {
            const digitosIniciais = input.value.replace(/\D/g, "");
            if (digitosIniciais.length > 0) {
                input.value = formatarTelefone(digitosIniciais);
            }
        }

        input.addEventListener("input", (e) => {
            if (e.isComposing) return;
            aplicarMascaraSuave(input, formatarTelefone);
        });
    });

    // ------------------------------------------------------------------------
    // 3. CONFIRMAÇÕES DE SEGURANÇA PARA AÇÕES CRÍTICAS
    // ------------------------------------------------------------------------
    const confirmElements = document.querySelectorAll("[data-confirm]");
    confirmElements.forEach(el => {
        if (el.tagName === "FORM") {
            // Em formulários, confirma apenas no evento 'submit' (evita interceptar cliques em selects ou inputs)
            el.addEventListener("submit", (e) => {
                const mensagem = el.getAttribute("data-confirm") || "Deseja realmente confirmar esta ação?";
                if (!confirm(mensagem)) {
                    e.preventDefault();
                }
            });
        } else {
            // Em botões e links de ação direta, confirma no 'click'
            el.addEventListener("click", (e) => {
                const mensagem = el.getAttribute("data-confirm") || "Deseja realmente confirmar esta ação?";
                if (!confirm(mensagem)) {
                    e.preventDefault();
                }
            });
        }
    });

    // ------------------------------------------------------------------------
    // 4. ATALHO PARA IMPRESSÃO DE CERTIFICADO DIGITAL
    // ------------------------------------------------------------------------
    const printBtn = document.getElementById("btn-print-certificate");
    if (printBtn) {
        printBtn.addEventListener("click", () => {
            window.print();
        });
    }
});
