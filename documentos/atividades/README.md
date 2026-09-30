# Diagramas de Atividade (UML) - Módulo Eventos (UNIFACCAMP)

Este documento apresenta os fluxos de processo de negócio modelados como **Diagramas de Atividade UML**, contemplando o caminho feliz (fluxo normal), tomadas de decisão, caminhos alternativos e tratamento de exceções.

---

## 1. Fluxo de Inscrição Online no Evento

```mermaid
flowchart TD
    Start([Início]) --> A[Acessar catálogo público /]
    A --> B[Selecionar evento e clicar em Inscrever-se]
    B --> C{Sessão autenticada?}

    C -- Não --> D{Já possui conta?}
    D -- Sim --> E[Entrar com CPF e senha]
    D -- Não --> F[Criar conta e informar vínculo, curso ou RA]
    E --> G[Retornar ao evento solicitado]
    F --> H[Autenticar automaticamente e retornar ao evento]
    C -- Sim --> I[Abrir inscrição do evento]
    G --> I
    H --> I
    I --> J{Há vagas disponíveis?}
    
    J -- Não --> K[Exibir mensagem 'Vagas Esgotadas']
    K --> EndFail([Fim sem inscrição])
    
    J -- Sim --> L[Preencher dados automaticamente com o perfil]
    L --> M{Apresentador de trabalho?}
    M -- Sim --> N[Informar projeto e CPFs dos integrantes]
    M -- Não --> O[Confirmar dados do usuário]
    N --> P[Validar CPFs e duplicidade]
    O --> P
    P --> Q{Dados válidos e equipe sem inscrição duplicada?}
    
    Q -- Não --> R[Exibir erro e manter inscrição não confirmada]
    R --> EndFail
    
    Q -- Sim --> S[Gravar uma inscrição e vínculos CPF-hash da equipe no MySQL]
    S --> T[Gerar um protocolo e comprovante para o grupo]
    T --> EndSuccess([Inscrição Confirmada])
```

Os integrantes não precisam ter conta no momento da inscrição. Quando criarem uma conta com um CPF vinculado, a consulta autenticada localizará a inscrição e a nota homologada do trabalho.

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
