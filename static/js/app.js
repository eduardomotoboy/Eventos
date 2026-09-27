/**
 * ============================================================================
 * ARQUIVO: static/js/app.js
 * PROJETO: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
 * DESCRIÇÃO: Scripts clientes para aprimoramento progressivo da interface:
 *            - Máscara automática de CPF (000.000.000-00) e Telefone
 *            - Confirmação de cancelamento e ações críticas
 *            - Validação de formulários no cliente
 *            - Impressão nativa do certificado
 * REGRA DE CONFORMIDADE: Todo o código possui comentários detalhados e explicativos.
 * ============================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
    // ------------------------------------------------------------------------
    // 1. MÁSCARA AUTOMÁTICA DE CPF
    // Formata o campo de texto enquanto o usuário digita no padrão: 000.000.000-00
    // ------------------------------------------------------------------------
    const cpfInputs = document.querySelectorAll('input[name="cpf"], #cpf');
    cpfInputs.forEach(input => {
        input.addEventListener("input", (e) => {
            let valor = e.target.value.replace(/\D/g, ""); // Remove tudo que não for dígito numérico
            if (valor.length > 11) valor = valor.slice(0, 11); // Limita a 11 dígitos

            // Aplica pontuação progressiva conforme o comprimento da string
            if (valor.length > 9) {
                valor = valor.replace(/^(\d{3})(\d{3})(\d{3})(\d{1,2})$/, "$1.$2.$3-$4");
            } else if (valor.length > 6) {
                valor = valor.replace(/^(\d{3})(\d{3})(\d{1,3})$/, "$1.$2.$3");
            } else if (valor.length > 3) {
                valor = valor.replace(/^(\d{3})(\d{1,3})$/, "$1.$2");
            }
            e.target.value = valor;
        });
    });

    // ------------------------------------------------------------------------
    // 2. MÁSCARA AUTOMÁTICA DE TELEFONE / CELULAR
    // Formata nos padrões: (00) 00000-0000 ou (00) 0000-0000
    // ------------------------------------------------------------------------
    const phoneInputs = document.querySelectorAll('input[name="telefone"], #telefone');
    phoneInputs.forEach(input => {
        input.addEventListener("input", (e) => {
            let valor = e.target.value.replace(/\D/g, "");
            if (valor.length > 11) valor = valor.slice(0, 11);

            if (valor.length > 10) {
                valor = valor.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
            } else if (valor.length > 6) {
                valor = valor.replace(/^(\d{2})(\d{4})(\d{0,4})$/, "($1) $2-$3");
            } else if (valor.length > 2) {
                valor = valor.replace(/^(\d{2})(\d{0,5})$/, "($1) $2");
            }
            e.target.value = valor;
        });
    });

    // ------------------------------------------------------------------------
    // 3. CONFIRMAÇÕES DE SEGURANÇA PARA AÇÕES DESTRUTIVAS
    // Exibe diálogo de confirmação antes de excluir eventos ou cancelar inscrições
    // ------------------------------------------------------------------------
    const deleteButtons = document.querySelectorAll("[data-confirm]");
    deleteButtons.forEach(button => {
        button.addEventListener("click", (e) => {
            const mensagem = button.getAttribute("data-confirm") || "Deseja realmente confirmar esta ação?";
            if (!confirm(mensagem)) {
                e.preventDefault(); // Cancela o envio se o usuário desistir
            }
        });
    });

    // ------------------------------------------------------------------------
    // 4. ATALHO PARA IMPRESSÃO DE CERTIFICADO
    // Aciona a caixa de diálogo nativa de impressão/salvar como PDF do navegador
    // ------------------------------------------------------------------------
    const printBtn = document.getElementById("btn-print-certificate");
    if (printBtn) {
        printBtn.addEventListener("click", () => {
            window.print();
        });
    }
});
