# Matriz de Rastreabilidade (Papéis RBAC × Funcionalidades)

Conforme as diretrizes da **Etapa 1 - Análise e Modelagem** do Projeto Extensionista UNIFACCAMP 2026.2, esta matriz correlaciona cada perfil de usuário (**Controle de Acesso Baseado em Papéis - RBAC**) às funcionalidades do sistema do **Módulo 4: Eventos, Inscrições e Amostras Acadêmicas**.

---

## 1. Tabela da Matriz de Rastreabilidade e Permissões

| Funcionalidade / Requisito do Sistema | Gestor do Sistema (CPF: 29156413823) | Coordenador | Professor Tutor | Usuário Base (Aluno / Comunidade) |
| :--- | :---: | :---: | :---: | :---: |
| **Autenticação por CPF e Senha (`/login`)** | ✔ | ✔ | ✔ | ✔ |
| **Auto-cadastro público como Usuário Base (`/cadastro`)** | ✔ | ✔ | ✔ | ✔ |
| **Consultar vitrine de cursos, palestras e amostras** | ✔ | ✔ | ✔ | ✔ |
| **Inscrição online com submissão de trabalho de Amostra** | ✔ | ✔ | ✔ | ✔ |
| **Geração de QR Code individual de credenciamento** | ✔ | ✔ | ✔ | ✔ |
| **Consultar comprovantes e notas de trabalhos (`/minhas-inscricoes`)** | ✔ | ✔ | ✔ | ✔ |
| **Validação pública de autenticidade de certificado digital** | ✔ | ✔ | ✔ | ✔ |
| **Scanner de QR Code via câmera web (`/scanner`)** | ✔ | ✔ | ✔ | |
| **Acesso ao Portal do Tutor e bancas atribuídas (`/tutor/avaliacoes`)** | ✔ | ✔ | ✔ | |
| **Lançamento de notas em rubricas (Domínio, Clareza, Relevância)** | ✔ | | ✔ | |
| **Painel de Gestão de Eventos e CRUD (`/gestao`)** | ✔ | ✔ | | |
| **Definir quantidade de tutores por trabalho de Amostra** | ✔ | | | |
| **Designar professores tutores para bancas examinadoras** | ✔ | | | |
| **Validar e Homologar notas finais para visualização do aluno** | ✔ | | | |
| **Gestão de Usuários e busca por CPF (`/gestao/usuarios`)** | ✔ | | | |
| **Alterar perfil de usuários em tempo real (Promoção a Tutor/Gestor)**| ✔ | | | |
| **Dashboard de KPIs e exportação de dados em CSV** | ✔ | ✔ | | |

---

## 2. Regras Institucionais de Segurança e Atribuição de Perfis

1. **Conta Gestora Raiz:**
   - O usuário com CPF `29156413823` possui o perfil irrestrito de **Gestor Geral do Sistema**, sendo o responsável por homologar notas, criar eventos e delegar papéis aos demais docentes.
2. **Política de Entrada Segura:**
   - Qualquer novo membro da comunidade acadêmica que realize o auto-cadastro pela interface web entra estritamente com o papel **Usuário Base**, impedindo escalada indevida de privilégios.
3. **Promoção de Docentes a Tutores de Banca:**
   - Quando o Gestor altera o perfil de um usuário para **Professor Tutor** na tela `/gestao/usuarios`, o sistema aciona uma rotina no banco de dados MySQL que cadastra automaticamente o docente na tabela `tutores`, tornando-o apto para vinculação em bancas avaliadoras.
4. **Proteção em Camada de Aplicação:**
   - Rotas administrativas e de bancas verificam a sessão assinada criptograficamente via `SessionMiddleware` e bloqueiam requisições não autorizadas, redirecionando com mensagens explicativas.
