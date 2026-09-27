# Diagramas de Atividade (UML) - Módulo Eventos (UNIFACCAMP)

Este documento apresenta os fluxos de processo de negócio modelados como **Diagramas de Atividade UML**, contemplando o caminho feliz (fluxo normal), tomadas de decisão, caminhos alternativos e tratamento de exceções.

---

## 1. Fluxo de Inscrição Online no Evento

```mermaid
flowchart TD
    Start([Início]) --> A[Acessar Vitrine de Eventos]
    A --> B[Selecionar Evento Desejado]
    B --> C{Há vagas disponíveis?}
    
    C -- Não --> D[Exibir mensagem 'Vagas Esgotadas']
    D --> EndFail([Fim sem inscrição])
    
    C -- Sim --> E[Preencher Formulário: Nome, CPF, E-mail, Tipo]
    E --> F[Submeter Inscrição]
    F --> G{CPF já cadastrado no evento?}
    
    G -- Sim --> H[Exibir alerta: Participante já inscrito]
    H --> EndFail
    
    G -- Não --> I[Persistir Inscrição no Banco Local SQLite]
    I --> J[Gerar Código Único INS-2026-XXXX]
    J --> K[Atualizar contador de vagas ocupadas]
    K --> L[Exibir Comprovante de Inscrição Oficial]
    L --> EndSuccess([Inscrição Confirmada])
```

---

## 2. Fluxo de Credenciamento e Check-in de Presença

```mermaid
flowchart TD
    Start([Participante chega ao evento]) --> A[Apresentar Código ou CPF na Recepção]
    A --> B[Organizador localiza inscrição no Painel de Gestão]
    B --> C{Inscrição existe e está ativa?}
    
    C -- Não --> D[Informar cadastro inexistente ou cancelado]
    D --> EndCancel([Acesso Não Autorizado])
    
    C -- Sim --> E{Já foi realizado Check-in?}
    E -- Sim --> F[Informar que presença já foi registrada]
    F --> EndOk([Acesso Liberado])
    
    E -- Não --> G[Registrar Check-in no sistema]
    G --> H[Gravar data/hora de presença no banco local]
    H --> I[Atualizar status para 'Presente']
    I --> J[Habilitar direito à emissão de certificado]
    J --> EndOk
```

---

## 3. Fluxo de Emissão e Validação de Certificado Digital

```mermaid
flowchart TD
    Start([Solicitar Certificado]) --> A[Sistema consulta histórico do participante]
    A --> B{Status da Inscrição é 'Presente'?}
    
    B -- Não --> C[Bloquear emissão: Exige confirmação de presença]
    C --> EndCertFail([Emissão Recusada])
    
    B -- Sim --> D{Certificado já emitido?}
    D -- Sim --> E[Recuperar código de autenticidade existente]
    D -- Não --> F[Calcular hash SHA-256 único CERT-2026-XXXXX]
    F --> G[Gravar registro na tabela de certificados]
    G --> E
    
    E --> H[Renderizar Certificado Oficial UNIFACCAMP com carga horária]
    H --> I[Disponibilizar impressão e download em PDF]
    I --> J[Permitir validação pública por terceiros em /validar-certificado]
    J --> EndSuccess([Certificado Válido])
```
