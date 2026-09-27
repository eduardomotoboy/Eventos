/**
 * ============================================================================
 * ARQUIVO: static/js/app.js
 * PROJETO: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
 * DESCRIÇÃO: Scripts clientes para aprimoramento progressivo da interface:
 *            - Máscara suave e fatiamento seguro de CPF (000.000.000-00)
 *            - Compatibilidade total com teclados móveis (Android, iOS)
 *            - Validação oficial de CPF (Receita Federal - Módulo 11)
 *            - Máscara automática de Telefone / Celular
 *            - Confirmações de segurança para ações críticas
 *            - Atalho de impressão nativa de certificados
 * REGRA DE CONFORMIDADE: Todo o código possui comentários detalhados e explicativos.
 * ============================================================================
 */

/**
 * Formata dígitos numéricos no padrão visual de CPF: 000.000.000-00
 * Utiliza fatiamento seguro de strings para evitar problemas de regex backreferences.
 * 
 * @param {string} digitos - String contendo apenas dígitos numéricos (até 11 caracteres).
 * @returns {string} - String formatada progressivamente com pontos e traço.
 */
function formatarCPF(digitos) {
    if (!digitos) return "";
    const v = String(digitos).slice(0, 11);
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
    const v = String(digitos).slice(0, 11);
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
 * Aplica máscara com preservação de cursor ao digitar no campo.
 * Evita pulos de cursor e travamentos no teclado de smartphones Android e iOS.
 * 
 * @param {HTMLInputElement} input - Elemento HTML do campo.
 * @param {Function} formatador - Função que recebe os dígitos e retorna o valor formatado.
 */
function aplicarMascaraComCursor(input, formatador) {
    const valorOriginal = input.value;
    const selecaoInicio = input.selectionStart || 0;

    // Quantidade de dígitos numéricos existentes antes da posição atual do cursor
    const digitosAntes = valorOriginal.slice(0, selecaoInicio).replace(/\D/g, "").length;

    const digitosTotal = valorOriginal.replace(/\D/g, "");
    const valorFormatado = formatador(digitosTotal);

    if (input.value !== valorFormatado) {
        input.value = valorFormatado;

        // Se o cursor estava ao final do texto, mantém no final do valor formatado
        if (selecaoInicio >= valorOriginal.length) {
            input.setSelectionRange(valorFormatado.length, valorFormatado.length);
        } else {
            // Posiciona o cursor logo após o mesmo número de dígitos pré-existentes
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
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // ------------------------------------------------------------------------
    // 1. MÁSCARA E VALIDAÇÃO INTEGRADA DE CPF (000.000.000-00)
    // Suporte fluido para desktop e teclados virtuais em dispositivos móveis
    // ------------------------------------------------------------------------
    const cpfInputs = document.querySelectorAll('input[name="cpf"], #cpf');

    cpfInputs.forEach(input => {
        // Assegura atributos HTML essenciais para melhor experiência no celular
        if (!input.getAttribute("inputmode")) input.setAttribute("inputmode", "numeric");
        if (!input.getAttribute("maxlength")) input.setAttribute("maxlength", "14");
        input.setAttribute("autocorrect", "off");
        input.setAttribute("autocapitalize", "off");
        input.setAttribute("spellcheck", "false");

        // Formata valor inicial (se o campo já veio pré-preenchido pelo servidor)
        if (input.value) {
            const digitosIniciais = input.value.replace(/\D/g, "");
            if (digitosIniciais.length > 0) {
                input.value = formatarCPF(digitosIniciais);
            }
        }

        // Evento 'input': Acionado a cada tecla pressionada ou caractere colado
        input.addEventListener("input", (e) => {
            // Se o teclado móvel estiver compondo caracteres, aguarda
            if (e.isComposing) return;

            aplicarMascaraComCursor(input, formatarCPF);

            const digitos = input.value.replace(/\D/g, "");

            // Validação visual sutil:
            // - Enquanto o usuário digita (1 a 10 dígitos), a borda permanece padrão (SEM erro)
            // - Ao completar exatamente 11 dígitos, indica visualmente se é autêntico ou não
            if (digitos.length === 11) {
                if (validarCPF(digitos, true)) {
                    input.style.borderColor = "var(--color-success, #10b981)";
                } else {
                    input.style.borderColor = "var(--color-danger, #ef4444)";
                }
            } else {
                input.style.borderColor = "";
            }
        });

        // Evento 'blur': Acionado quando o usuário sai do campo
        input.addEventListener("blur", () => {
            const digitos = input.value.replace(/\D/g, "");
            if (digitos.length > 0 && digitos.length < 11) {
                // Alerta visual de CPF incompleto apenas após o usuário terminar a digitação e sair do campo
                input.style.borderColor = "var(--color-danger, #ef4444)";
            } else if (digitos.length === 11) {
                if (validarCPF(digitos, true)) {
                    input.style.borderColor = "var(--color-success, #10b981)";
                } else {
                    input.style.borderColor = "var(--color-danger, #ef4444)";
                }
            } else {
                input.style.borderColor = "";
            }
        });

        // Intercepta o envio do formulário associado para garantir que CPF esteja íntegro
        const form = input.closest("form");
        if (form && !form.dataset.cpfValidationBound) {
            form.dataset.cpfValidationBound = "true";

            form.addEventListener("submit", (e) => {
                const digitos = input.value.replace(/\D/g, "");

                // Se o campo for obrigatório ou se o usuário preencheu parcialmente
                if (input.required || digitos.length > 0) {
                    if (digitos.length !== 11) {
                        e.preventDefault();
                        input.style.borderColor = "var(--color-danger, #ef4444)";
                        input.focus();
                        alert("Por favor, digite os 11 dígitos do CPF completo.");
                        return false;
                    }
                    if (!validarCPF(digitos, true)) {
                        e.preventDefault();
                        input.style.borderColor = "var(--color-danger, #ef4444)";
                        input.focus();
                        alert("O CPF informado é inválido conforme o algoritmo da Receita Federal. Verifique os dígitos informados.");
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
        if (!input.getAttribute("inputmode")) input.setAttribute("inputmode", "tel");
        if (!input.getAttribute("maxlength")) input.setAttribute("maxlength", "15");

        if (input.value) {
            const digitosIniciais = input.value.replace(/\D/g, "");
            if (digitosIniciais.length > 0) {
                input.value = formatarTelefone(digitosIniciais);
            }
        }

        input.addEventListener("input", (e) => {
            if (e.isComposing) return;
            aplicarMascaraComCursor(input, formatarTelefone);
        });
    });

    // ------------------------------------------------------------------------
    // 3. CONFIRMAÇÕES DE SEGURANÇA PARA AÇÕES DESTRUTIVAS
    // ------------------------------------------------------------------------
    const deleteButtons = document.querySelectorAll("[data-confirm]");
    deleteButtons.forEach(button => {
        button.addEventListener("click", (e) => {
            const mensagem = button.getAttribute("data-confirm") || "Deseja realmente confirmar esta ação?";
            if (!confirm(mensagem)) {
                e.preventDefault();
            }
        });
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
