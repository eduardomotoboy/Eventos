# 🎓 Eventos - Sistema de Inscrição e Extensão Universitária

[![Licença MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.14+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CSS Grid](https://img.shields.io/badge/CSS-Responsive%20Grid-264de4.svg?logo=css3&logoColor=white)](static/css/style.css)
[![MySQL](https://img.shields.io/badge/Database-MySQL%208.0-4479A1.svg?logo=mysql&logoColor=white)](database.py)

> **Centro Universitário Campo Limpo Paulista (UNIFACCAMP)**  
> **Projeto Extensionista — 2026 Semestre 2**  
> **Módulo 4: Eventos, Inscrições e Amostras Acadêmicas**  
> **Repositório GitHub:** [https://github.com/eduardomotoboy/Eventos.git](https://github.com/eduardomotoboy/Eventos.git)

---

## 📌 1. Visão Geral do Projeto

O projeto **Eventos** é a aplicação web desenvolvida para operacionalizar o **Módulo 4 (Eventos e Inscrição)** do *Ecossistema de Extensão* da **UNIFACCAMP**, integrando-se aos módulos de Avaliação, Controle e Acervo.

### Funcionalidades Chave:
- **Autenticação Segura por CPF (Login & Sessão):** Acesso com CPF e controle de permissões por papéis (RBAC).
- **Gestão de Usuários pelo Gestor (`/gestao/usuarios`):** Busca ágil por CPF/nome e alteração de privilégios (`Gestor`, `Professor Tutor`, `Usuário Base`, `Coordenador`) a qualquer momento.
- **Auto-cadastro de Usuário Base (`/cadastro`):** Qualquer visitante ou estudante cadastra-se primariamente como `Usuário Base`.
- **Amostras Extensionistas e Bancas Avaliadoras:** Inscrição com submissão de resumo de trabalho de pesquisa/extensão; o criador do evento estipula a quantidade desejada de tutores e designa os avaliadores.
- **Portal do Professor Tutor (`/tutor/avaliacoes`):** Docentes atribuem notas (1 a 5) em critérios pedagógicos (*Domínio do Tema*, *Clareza*, *Relevância Extensionista*) e parecer técnico.
- **Validação e Homologação Final pelo Criador:** O organizador do evento valida e homologa as notas antes de disponibilizá-las para os alunos visualizarem online.
- **Scanner de QR Code via Câmera (`/scanner`):** Leitura instantânea de QR Code para localização de projetos de alunos e credenciamento presencial (Check-in).
- **Certificados Digitais:** Emissão automatizada com código hash de validação pública.
- **Relatórios Analíticos e Exportação:** Painel com KPIs e download de dados em formato CSV compatível com Excel.

---

## 🔐 2. Credenciais de Acesso e Perfis (RBAC)

O sistema possui controle rigoroso de acesso e conta com o usuário Gestor pré-configurado:

| Perfil | Identificador (Login) | Senha Padrão | Privilégios |
| :--- | :--- | :--- | :--- |
| **Gestor do Sistema** | CPF: `29156413823` | `29156413823` ou `Eventos@2026` | Acesso total: criação/edição/exclusão de eventos, homologação de notas, gestão de usuários e promoção de perfis. |
| **Professor Tutor** | CPF cadastrado | Senha cadastrada | Acesso ao Portal do Tutor, bancas examinadoras e Scanner de QR Code. |
| **Usuário Base** | CPF cadastrado | Senha cadastrada | Inscrição em eventos, submissão de trabalhos, consulta de notas homologadas e certificados. |

> **Nota de Promoção de Docentes:** Quando o Gestor altera o perfil de um usuário para **Professor Tutor**, o sistema sincroniza automaticamente seus dados com a tabela `tutores`, permitindo sua designação para bancas examinadoras de Amostras.

---

## 🌐 3. Acesso em Rede Local (LAN)

A aplicação está configurada para escutar em `0.0.0.0:8000`, permitindo acesso direto tanto pelo notebook local quanto por qualquer outro dispositivo (celulares, tablets e computadores) conectado na mesma rede Wi-Fi/LAN:

- **Acesso neste Computador (Localhost):** [http://localhost:8000](http://localhost:8000)
- **Acesso por Dispositivos na Rede Local:** [http://192.168.0.23:8000](http://192.168.0.23:8000)

*(Caso outro dispositivo na rede não consiga conectar, execute o script em lote `definicoes/scripts_teste/liberar_firewall_porta_8000.bat` como Administrador no Windows para liberar a porta 8000 no Firewall).*

---

## 🗄️ 4. Banco de Dados MySQL 8.0

O sistema utiliza banco de dados **MySQL 8.0** local com tabelas InnoDB e integridade referencial:

- **Host:** `localhost:3306`
- **Banco de Dados (Schema):** `eventos`
- **Usuário:** `Eventos_extencionista`
- **Senha:** `Eventos_extencionista`

---

## 📐 5. Arquitetura Responsive CSS Grid

A interface do projeto foi desenvolvida seguindo estritamente a especificação do diagrama **Responsive CSS Grid** (`definicoes/responsive css grid.jpeg`):

```css
/* Estrutura Desktop (> 768px): Colunas 240px 1fr 240px */
.page {
  display: grid;
  grid-template-columns: 240px 1fr 240px;
  grid-template-rows: auto 1fr auto;
  grid-template-areas:
    "header header header"
    "nav    main   aside"
    "footer footer footer";
  min-height: 100vh;
}

/* Estrutura Mobile (<= 768px): Coluna única em cascata */
@media (max-width: 768px) {
  .page {
    grid-template-columns: 1fr;
    grid-template-areas:
      "header"
      "main"
      "nav"
      "aside"
      "footer";
  }
}
```

---

## 🚀 6. Como Executar a Aplicação Localmente

### Pré-requisitos
- Python 3.10 ou superior instalado.
- MySQL 8.0 em execução na porta 3306 com as credenciais acima.

### Passo 1: Instalar as Dependências
```bash
pip install -r requirements.txt
```

### Passo 2: Executar a Aplicação
No Windows, dê dois cliques em `run.bat` ou execute no terminal:
```bash
python app.py
```

O servidor inicializará automaticamente em:
- 👉 **[http://localhost:8000](http://localhost:8000)** (Local)
- 👉 **[http://192.168.0.23:8000](http://192.168.0.23:8000)** (Rede Local)

---

## 🧪 7. Scripts de Teste Automatizados (`definicoes/scripts_teste/`)

Conforme diretriz do projeto, todos os scripts de validação e teste estão centralizados em `definicoes/scripts_teste/`:

- `python definicoes/scripts_teste/test_auth_and_roles.py`: Valida autenticação do Gestor por CPF, auto-cadastro de Usuário Base, busca por CPF, promoção para Professor Tutor e sincronização automática com a tabela de tutores.
- `python definicoes/scripts_teste/test_app_endpoints.py`: Valida rotas HTTP via `TestClient`, proteção de endpoints administrativos, bloqueio de Usuário Base e alteração de perfil via POST.
- `python definicoes/scripts_teste/test_tutor_isolation.py`: Valida isolamento estrito de bancas examinadoras para Professores Tutores (bloqueio 403 em GET/POST de outros tutores) e acesso irrestrito de auditoria para o Gestor.
- `python definicoes/scripts_teste/test_mysql_conn.py`: Valida a conectividade ativa com o MySQL Server 8.0.

---

## 🗂️ 8. Estrutura de Documentação Acadêmica (`/documentos`)

- [Casos de Uso UML (Perfis e Atores)](documentos/caso-de-uso/README.md)
- [Diagramas de Atividade UML](documentos/atividades/README.md)
- [Modelagem de Entidades e Classes MER/DER](documentos/entidades/README.md)
- [Diagramas de Estados UML](documentos/estados/README.md)
- [Matriz de Rastreabilidade (Atores × Funcionalidades)](documentos/matriz-rastreabilidade/README.md)

---

## 📜 9. Licença e Atribuição

Este projeto está licenciado sob a **Licença MIT** — consulte o arquivo [LICENSE](LICENSE) para maiores detalhes.

> SANTOS, Eduardo et al. **Eventos: Sistema Web de Extensão Universitária**. Centro Universitário Campo Limpo Paulista (UNIFACCAMP), 2026.
