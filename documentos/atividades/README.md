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
    S --> S2[Se houver arquivo anexado, salvar no disco e registrar em inscricao_arquivos]
    S2 --> T[Gerar um protocolo e comprovante para o grupo]
    T --> EndSuccess([Inscrição Confirmada])
```

Os integrantes não precisam ter conta no momento da inscrição. Quando criarem uma conta com um CPF vinculado, a consulta autenticada localizará a inscrição e a nota homologada do trabalho.

---

## 2. Fluxo de Credenciamento e Check-in de Presença

```mermaid
flowchart TD
    Start([Participante chega ao evento]) --> A[Apresentar Código ou CPF na Recepção]
    A --> B[Organizador lê o QR Code único da inscrição do grupo]
    B --> C{Inscrição existe e está ativa?}
    
    C -- Não --> D[Informar cadastro inexistente ou cancelado]
    D --> EndCancel([Acesso Não Autorizado])
    
    C -- Sim --> E{Já foi realizado Check-in?}
    E -- Sim --> F[Informar que presença já foi registrada]
    F --> EndOk([Acesso Liberado])
    
    E -- Não --> G[Registrar Check-in no sistema]
    G --> H[Gravar data/hora na inscrição única]
    H --> I[Atualizar status compartilhado para 'Presente']
    I --> J[Aplicar presença a todos os CPFs vinculados]
    J --> K[Cada integrante consulta a inscrição e presença pelo próprio CPF]
    K --> L[Habilitar certificado individual por CPF vinculado]
    L --> EndOk
```

---

## 3. Fluxo de Emissão e Validação de Certificado Digital

```mermaid
flowchart TD
    Start([Solicitar Certificado]) --> A[Sistema consulta histórico do participante]
    A --> B{Status da Inscrição é 'Presente'?}
    
    B -- Não --> C[Bloquear emissão: Exige confirmação de presença]
    C --> EndCertFail([Emissão Recusada])
    
    B -- Sim --> D[Localizar CPFs vinculados à inscrição]
    D --> E[Gerar ou recuperar um código por CPF]
    E --> F[Gravar certificados por CPF hash sem coletar nomes]
    F --> G[Consultar nome no cadastro da aplicação ao imprimir ou validar]
    
    G --> H[Renderizar Certificado Oficial UNIFACCAMP com carga horária]
    H --> I[Disponibilizar impressão e download em PDF]
    I --> J[Permitir validação pública por terceiros em /validar-certificado]
    J --> EndSuccess([Certificado Válido])
```
