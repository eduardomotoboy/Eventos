# Modelagem de Dados: Diagrama MER e Classes (UML)

Este documento descreve as entidades de negócio, seus atributos, cardinalidades, perfis e métodos de manipulação implementados no banco de dados relacional MySQL 8.0 do projeto **Eventos** (Módulo 4 da UNIFACCAMP).

---

## 1. Diagrama de Classes e Entidades (UML)

```mermaid
classDiagram
    class Usuario {
        +Integer id
        +String nome
        +String cpf
        +String email
        +String telefone
        +String tipo_participante
        +String matricula_curso
        +String senha_hash
        +String perfil
        +String cargo
        +String departamento
        +Boolean ativo
        +DateTime criado_em
        +autenticar(cpf, senha)
        +cadastrar(nome, cpf, email, telefone, tipo_participante, matricula_curso, senha)
        +alterar_perfil(novo_perfil)
    }

    class Evento {
        +Integer id
        +String titulo
        +String descricao
        +String categoria
        +String modalidade
        +String local_link
        +String data_inicio
        +String data_fim
        +Integer carga_horaria
        +Integer vagas_totais
        +String palestrante
        +Integer permite_apresentacao
        +Integer qtd_tutores_por_trabalho
        +Integer organizador_id
        +String status
        +DateTime criado_em
        +calcular_vagas_restantes() Integer
        +verificar_disponibilidade() Boolean
    }

    class Participante {
        +Integer id
        +String nome
        +String cpf
        +String email
        +String telefone
        +String tipo_participante
        +String matricula_curso
        +DateTime criado_em
        +validar_cpf() Boolean
    }

    class Inscricao {
        +Integer id
        +String codigo_inscricao
        +Integer evento_id
        +Integer participante_id
        +String tipo_participacao
        +String titulo_trabalho
        +String resumo_trabalho
        +String area_trabalho
        +String autores
        +Decimal nota_final
        +Integer notas_homologadas
        +DateTime data_homologacao
        +String status
        +DateTime data_inscricao
        +DateTime data_checkin
        +realizar_checkin()
        +cancelar()
    }

    class InscricaoParticipante {
        +Integer id
        +Integer inscricao_id
        +String cpf_hash
        +DateTime criado_em
    }

    class Tutor {
        +Integer id
        +String nome
        +String email
        +String departamento
        +DateTime criado_em
    }

    class BancaTutor {
        +Integer id
        +Integer evento_id
        +Integer inscricao_id
        +Integer tutor_id
        +String status_avaliacao
        +DateTime criado_em
    }

    class AvaliacaoApresentacao {
        +Integer id
        +Integer banca_id
        +Integer inscricao_id
        +Integer tutor_id
        +Decimal nota_dominio
        +Decimal nota_clareza
        +Decimal nota_relevancia
        +Decimal nota_media
        +String comentarios
        +DateTime data_avaliacao
    }

    class Certificado {
        +Integer id
        +String codigo_autenticidade
        +Integer inscricao_id
        +Integer evento_id
        +Integer participante_id
        +Integer carga_horaria
        +DateTime data_emissao
        +String status
        +validar() Boolean
    }

    Usuario "1" --> "0..*" Evento : organiza
    Evento "1" --> "0..*" Inscricao : possui
    Participante "1" --> "0..*" Inscricao : realiza
    Inscricao "1" --> "1..*" InscricaoParticipante : compartilha_com
    Inscricao "1" --> "0..1" Certificado : gera
    Inscricao "1" --> "0..*" BancaTutor : submete_para
    Tutor "1" --> "0..*" BancaTutor : avalia
    BancaTutor "1" --> "0..1" AvaliacaoApresentacao : registra
```

---

## 2. Diagrama de Relacionamento de Entidades (MER / DER)

```mermaid
erDiagram
    USUARIOS ||--o{ EVENTOS : "gerencia"
    EVENTOS ||--o{ INSCRICOES : "contem"
    PARTICIPANTES ||--o{ INSCRICOES : "efetua"
    INSCRICOES ||--|{ INSCRICAO_PARTICIPANTES : "vincula_cpfs"
    INSCRICOES ||--o| CERTIFICADOS : "origina"
    INSCRICOES ||--o{ BANCA_TUTORES : "recebe_banca"
    TUTORES ||--o{ BANCA_TUTORES : "integra"
    BANCA_TUTORES ||--o| AVALIACOES_APRESENTACAO : "gera_avaliacao"

    USUARIOS {
        int id PK
        string nome
        string cpf UK
        string email UK
        string telefone
        string tipo_participante
        string matricula_curso
        string senha_hash
        string perfil
        string cargo
        string departamento
        int ativo
        datetime criado_em
    }

    TUTORES {
        int id PK
        string nome
        string email UK
        string departamento
        datetime criado_em
    }

    EVENTOS {
        int id PK
        string titulo
        text descricao
        string categoria
        string modalidade
        string local_link
        string data_inicio
        string data_fim
        int carga_horaria
        int vagas_totais
        string palestrante
        int permite_apresentacao
        int qtd_tutores_por_trabalho
        string status
        datetime criado_em
    }

    PARTICIPANTES {
        int id PK
        string nome
        string cpf UK
        string email
        string telefone
        string tipo_participante
        string matricula_curso
        datetime criado_em
    }

    INSCRICOES {
        int id PK
        string codigo_inscricao UK
        int evento_id FK
        int participante_id FK
        string tipo_participacao
        string titulo_trabalho
        text resumo_trabalho
        string area_trabalho
        text autores
        decimal nota_final
        int notas_homologadas
        datetime data_homologacao
        string status
        datetime data_inscricao
        datetime data_checkin
    }

    INSCRICAO_PARTICIPANTES {
        int id PK
        int inscricao_id FK
        string cpf_hash
        datetime criado_em
    }

    BANCA_TUTORES {
        int id PK
        int evento_id FK
        int inscricao_id FK
        int tutor_id FK
        string status_avaliacao
        datetime criado_em
    }

    AVALIACOES_APRESENTACAO {
        int id PK
        int banca_id FK
        int inscricao_id FK
        int tutor_id FK
        decimal nota_dominio
        decimal nota_clareza
        decimal nota_relevancia
        decimal nota_media
        text comentarios
        datetime data_avaliacao
    }

    CERTIFICADOS {
        int id PK
        string codigo_autenticidade UK
        int inscricao_id FK
        int evento_id FK
        int participante_id FK
        int carga_horaria
        datetime data_emissao
        string status
    }
```

---

## 3. Dicionário de Dados Oficial

### Tabela: `usuarios`
Responsável pela segurança, controle de acesso e permissões (RBAC).

| Campo | Tipo | Nulo | Chave | Descrição e Regras |
| :--- | :--- | :---: | :---: | :--- |
| `id` | INT AUTO_INCREMENT | Não | PK | Identificador numérico primário. |
| `nome` | VARCHAR(255) | Não | - | Nome completo do usuário. |
| `cpf` | VARCHAR(20) | Não | UK | CPF único utilizado para login (formatado ou limpo). |
| `email` | VARCHAR(255) | Não | UK | Endereço eletrônico institucional/pessoal. |
| `telefone` | VARCHAR(50) | Sim | - | Contato telefônico / WhatsApp. |
| `tipo_participante` | VARCHAR(100) | Sim | - | Vínculo/categoria informada no cadastro e reutilizada na inscrição. |
| `matricula_curso` | VARCHAR(150) | Sim | - | Curso, RA ou matrícula reutilizados na inscrição. |
| `senha_hash` | VARCHAR(255) | Não | - | Hash criptográfico SHA-256 da senha. |
| `perfil` | VARCHAR(50) | Não | - | Papel no sistema: **Gestor**, **Professor Tutor**, **Usuário Base**, **Coordenador**. |
| `cargo` | VARCHAR(100) | Sim | - | Título profissional ou acadêmico. |
| `departamento`| VARCHAR(150) | Sim | - | Setor, curso ou pró-reitoria. |
| `ativo` | TINYINT(1) | Não | - | Indicador de usuário ativo (1) ou bloqueado (0). |
| `criado_em` | DATETIME | Não | - | Carimbo de data/hora do cadastro. |

> **Nota de Negócio (RBAC):**
> 1. O usuário **Gestor Geral** é pré-configurado no banco de dados com CPF `00000000000`.
> 2. Todo novo usuário registrado inicia obrigatoriamente com perfil **Usuário Base**.
> 3. O Gestor pode alterar o perfil para **Professor Tutor** a qualquer momento, momento em que o sistema cadastra o usuário automaticamente na tabela `tutores` para permitir composição de bancas examinadoras.

### Tabela: `inscricao_participantes`
Relaciona os CPFs dos integrantes a uma inscrição, permitindo uma única apresentação e nota compartilhada sem exigir que cada integrante já possua conta.

| Campo | Tipo | Nulo | Chave | Descrição e Regras |
| :--- | :--- | :---: | :---: | :--- |
| `id` | INT AUTO_INCREMENT | Não | PK | Identificador do vínculo. |
| `inscricao_id` | INT | Não | FK | Inscrição do grupo; removido em cascata com a inscrição. |
| `cpf_hash` | VARCHAR(64) | Não | UK composta | Blind index HMAC-SHA256 do CPF; permite localizar inscrição e nota sem duplicar o trabalho. |
| `criado_em` | DATETIME | Não | - | Data/hora em que o CPF foi vinculado. |

> **Regra de consulta:** Quando um integrante cria uma conta com o mesmo CPF, a consulta de inscrições autenticada localiza o vínculo e apresenta a nota homologada daquela inscrição.
