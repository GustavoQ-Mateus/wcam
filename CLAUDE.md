# WCam, regras do projeto

WCam transforma a câmera do celular em webcam do PC sem fio. O PC roda um agente local; o celular abre uma página pelo QR code, na mesma rede Wi-Fi, e envia vídeo por WebRTC. O agente publica os quadros numa câmera virtual que Meet, Teams, Zoom e qualquer app enxergam como webcam comum.

Projeto open source de portfólio e estudo. O planejamento completo está em `docs/planejamento.md`.

## Critérios de aceitação do produto
Detalhados em `docs/planejamento.md` e dominantes sobre qualquer spec:
- CA-1: a câmera é reconhecida por Meet, Teams, Zoom, Discord, OBS e sites com `getUserMedia`.
- CA-2: sem perda de qualidade entre o celular e a câmera virtual: mesma resolução e fps da captura (1080p30), sem redimensionar nem converter cor, SSIM de pelo menos 0,98.
- CA-3: pareamento por QR mostrado no PC e lido pelo celular; console (`/`) e celular (`/cam`) são interfaces totalmente diferentes, nenhuma é versão responsiva da outra.
- CA-4: segurança mínima das portas abertas: console só em localhost, porta da LAN só com o agente ativo, firewall restrito à rede privada local. Autorização só pelo QR: token de uso único no fragmento da URL, guardado como hash, válido só na janela do QR e só para IP da mesma sub-rede, com limite de tentativas. Nada no celular é instalado e nenhum aparelho fica lembrado.

## Repositório
Monorepo único, conta `GustavoQ-Mateus` no GitHub.

| Pasta | Stack | Papel |
|---|---|---|
| `agent` | Python 3.13, uv, FastAPI + uvicorn, aiortc, PyAV, pyvirtualcam, SQLite, pystray, pywebview, PyInstaller, pytest | Servidor local: HTTPS na LAN, pareamento, WebRTC, câmera virtual, API e eventos |
| `web` | React + Vite + TypeScript + SCSS, Vitest, Playwright | Duas superfícies: `/cam` (celular, captura) e `/` (console no PC) |
| `docs` | Markdown | Planejamento, specs, ADRs |
| `installer` | Inno Setup | Instalador Windows e regra de firewall |
| raiz | Docker Compose | Ambiente de desenvolvimento e CI |

## Papéis das sessões
- A sessão aberta na raiz é o **orquestrador**: define escopo e contrato, escreve planejamento, specs, ADRs e handoffs, revisa diffs contra a spec e contra este arquivo e roda a revisão antes do PR. Não implementa código.
- As sessões **implementadoras** são abertas pelo usuário, cada uma no seu escopo, e só mexem nele. O orquestrador envia o trabalho por `docs/handoff-*.md` e recebe o fechamento por `docs/relatorio-*.md`.
- Mudança que atravessa escopos (contrato, chave de idioma compartilhada, porta, variável de ambiente) é decidida pelo orquestrador e registrada na spec e no handoff antes do código.

## Specs e ADRs (Specification-Driven Development)
- A fonte da verdade de cada trabalho é a spec aprovada em `docs/specs/spec-vX.Y.Z.md`, mais as ADRs em `docs/adr/`. Só implemente o que a spec pede; escopo novo vira nova versão da spec antes de virar código. Se a spec for ambígua ou contradizer o código, pergunte antes de implementar.
- Versionamento SemVer: MAJOR muda contrato ou arquitetura de forma incompatível, MINOR adiciona escopo compatível, PATCH corrige detalhe. Cada versão é um arquivo novo; nunca reescreva uma spec já entregue.
- Fluxo: spec em `Status: Draft` → o usuário aprova (`Status: Aprovada`) → código → `Status: Entregue` com changelog. Código só depois da aprovação.
- Os critérios de aceitação (CA) da spec são dominantes. Nada é dado como pronto sem cumprir e verificar todos os CA; se código ou decisão divergirem da spec, vale a spec e a divergência é corrigida antes de seguir.
- Decisão de arquitetura vira ADR nova numerada em `docs/adr/`. ADR aceita trava a decisão; mudar exige ADR nova que a substitua.
- O contrato entre `web` e `agent` (rotas HTTP, mensagens do DataChannel, eventos SSE) vive em `docs/contrato.md`. Mudou o contrato, muda o documento na mesma spec, antes do código.

## Código
- Simplicidade proporcional ao problema. KISS e YAGNI. Não adicione camadas, padrões, generalizações ou configurações que a spec não pede.
- Sem código documentado. Não escreva comentários explicativos nem docstrings; nomes claros explicam o código. Comentário só em caso raro e genuinamente não óbvio, e curto. Exceção: `summary`/`description` das rotas FastAPI, que geram o OpenAPI.
- Siga o estilo já presente no módulo. Não reformate código existente sem pedido.
- Nada de dependência nova sem necessidade real; justifique na spec.
- Nunca use travessão em nada gerado.
- Não alinhe colunas com espaços extras (SQL, atribuições, listas). Um espaço só entre os elementos.
- Mudança de comportamento vem com teste, no padrão dos testes que já existem.
- Não altere contrato nem schema do banco sem a spec pedir. Schema muda só por migration nova em `agent/src/wcam/persistence/migrations/`.
- Não altere `README.md` sem pedido explícito; avise em vez de editar.

## Estrutura de código
Princípios: Clean Code, SOLID, KISS e YAGNI, na medida da spec.

Geral
- Sem linha em branco entre declarações do mesmo tipo em sequência. Linha em branco só separa blocos diferentes.
- Ordem dos membros: constantes, campos, construtor, propriedades, métodos públicos, métodos privados.
- Linha até ~120 colunas; passou disso, um argumento por linha.
- Retorno antecipado em vez de `if` aninhado; no máximo dois níveis de aninhamento.
- Métodos curtos, uma responsabilidade. Trecho que pediria comentário vira método com nome.
- Sem número mágico: constante com nome ou configuração.
- Nomes descritivos, sem abreviação. Código em inglês.
- Texto de interface fala a língua de quem usa, não a da arquitetura. Para o usuário existem "o WCam no computador" e "o celular"; nunca "agente", "servidor", "sessão", "token", "pareamento", "requisição", "interface" ou nomes de protocolo. Métricas técnicas (fps, bitrate, codec, CPU) só numa área de detalhes, nunca na mensagem principal. Glossário em `docs/planejamento.md` §5.7.
- Interface em inglês e português do Brasil. Nenhum texto de interface escrito no código: tudo em `locales/en.json` e `locales/pt-BR.json`, usados pelo web e pela bandeja. Chave nova entra nos dois arquivos no mesmo commit.

Python
- `ruff check` e `ruff format` limpos, `pyright` em modo strict sem erros. Type hints em toda assinatura pública.
- Pacotes por domínio em `agent/src/wcam/<dominio>` (`pairing`, `media`, `virtualcam`, `persistence`, `api`, `network`). Domínio não importa FastAPI nem aiortc; quem conhece framework é a borda.
- Integração com hardware ou SO atrás de `Protocol` (`VirtualCameraSink`, por exemplo), com implementação falsa para teste.
- `snake_case` para funções, variáveis e módulos; `PascalCase` para classes; `UPPER_SNAKE_CASE` para constantes. DTO como `dataclass(frozen=True, slots=True)` ou modelo Pydantic na borda HTTP.
- Assíncrono de ponta a ponta no caminho de rede. Trabalho de CPU pesado (conversão de quadro) fora do event loop, em executor.
- Erros de API sempre no formato `{"error":{"code","message"}}`; o cliente roteia por `code`, nunca pela mensagem.
- Tarefas `asyncio` com dono e cancelamento explícito; nada de `create_task` solto.

TypeScript/React
- Componente funcional, um por arquivo, sem `any`, TypeScript estrito; dados em hooks ou módulos em `data/`, fora do JSX.
- Arquivos em `kebab-case` (`pairing-qr.tsx`); componentes e tipos em `PascalCase`; hooks `useAlgo`; constantes de módulo em `UPPER_SNAKE_CASE`.
- Funções puras de dados testadas com Vitest.
- SCSS com tokens em variáveis CSS; nada de cor ou espaçamento solto.
- APIs de navegador (getUserMedia, RTCPeerConnection, Wake Lock) encapsuladas em hooks ou módulos em `media/`, nunca chamadas direto no componente.

SQL
- Palavras-chave em minúsculo, uma coluna por linha em `select` e `create table`, `snake_case`, tabelas no plural, script idempotente.

Testes
- Nome no formato cenário e resultado (`test_expired_pairing_token_is_rejected`); um comportamento por teste.

## Front
- Todo trabalho de interface usa as skills de design instaladas: `taste-skill` (direção de arte e anti-slop), `impeccable` (`/impeccable shape`, `audit`, `polish`), `emil-design-eng` (polimento e detalhes), `mobile-native` (página do celular) e, para movimento, `animate`, `review-animations` e `animation-performance`. A spec do front registra qual skill guiou cada decisão.
- Regras anti AI slop valem sempre: sem gradiente roxo, sem glassmorphism decorativo, sem grade de cards genérica, sem emoji como ícone, sem texto de marketing vazio, sem sombra e borda arredondada em tudo. Cada elemento visual tem função.
- Duas superfícies com papéis diferentes: `/cam` é um visor de câmera em tela cheia, operado com uma mão; `/` é o console do PC (QR, estado da conexão, prévia, métricas, controles). Sem login, cadastro ou landing page dentro do app.
- Tempo real do console por SSE; controles do celular pelo DataChannel do WebRTC.
- Controles nos dois lados: pausar, desconectar e trocar câmera existem na bandeja, no console e no celular, e qualquer mudança aparece nos três em menos de 300 ms (tabela em `docs/planejamento.md` §5.4).
- Tokens de cor de `docs/planejamento.md` §5.6, estilo `true-black-flat`: elevação só por luminosidade, cor só em dado e estado, tally "ao vivo" em `--data`. Cor nunca é o único sinal de estado.
- Verificado no navegador (e num celular real para `/cam`) antes de declarar pronto; se não foi visto, diga.

## Verificação antes de commitar
- Agent, a partir de `agent`: `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` e `uv run pytest`.
- Web, a partir de `web`: `npm run build` (inclui `tsc -b`) sem avisos, `npm run lint` e `npm test`.
- Não declarar pronto o que não foi verificado. Se algo não foi testado, dizer.

## Verificação antes de abrir PR
- No estado final da branch (depois de `git merge origin/main`), rodar a verificação completa acima, `npm run test:e2e` (Playwright com câmera falsa do Chromium) e o fluxo real: `uv run wcam`, escanear o QR com o celular, ver a imagem no console e conferir a câmera virtual nos apps do CA-1 que a spec tocar. Registrar o resultado no changelog da spec. Falhou um CA, não abre PR.

## Git flow
- `main` é a linha estável. Cada spec tem sua branch de integração `feature/<nome-curto>` criada a partir de `origin/main`, com PR para `main`. Nunca commit ou push direto na `main`, nunca force push.
- Na branch de integração o orquestrador coloca o que é compartilhado (handoffs, `docs/contrato.md`, `locales/`). Cada sessão implementadora trabalha em `feature/<nome-curto>-<sessão>` (`-agent`, `-web`), criada a partir da integração, num worktree próprio em `.worktrees/<sessão>`, com PR para a branch de integração. Só a sessão dona mexe no seu worktree.
- `.worktrees/` fica fora do git, do contexto Docker e da busca do editor.
- Ao entregar uma versão da spec, tag `vX.Y.Z` no merge. Antes do PR, `version` em `agent/pyproject.toml` e em `web/package.json` fica igual à versão da spec, mesmo que um dos lados não tenha outro trabalho nela.
- PR: título no padrão do commit. Corpo:
  ```
  Spec: docs/specs/spec-vX.Y.Z.md
  Descrição: <resumo em uma ou duas frases>

  O que foi feito:
  <frase curta por mudança, dizendo o que mudou e como era antes>
  ```
  Sem a linha "Generated with Claude Code" e sem referência a Claude ou Anthropic.
- O `gh` local tem duas contas, `GustavoQ-Mateus` e `Gustavo-QMateus`. O remote é da `GustavoQ-Mateus`; confira com `gh auth status` que ela é a ativa antes de push ou PR.

## Commits
- Curtos, uma linha, Conventional Commits: `tipo(escopo): descrição`. Escopos: `agent`, `web`, `docs`, `ci`.
- Tipos: feat, fix, refactor, test, docs, chore, build, ci.
- Descrição no imperativo, minúscula, sem ponto final.
- Um commit por unidade lógica de mudança.
- NUNCA incluir "Co-Authored-By: Claude" nem qualquer referência à Anthropic.

## Ambiente
- Produto: app Windows nativo (bandeja + janela WebView2), porque a câmera virtual depende do SO. No celular, só o navegador. Linux (v4l2loopback) e macOS ficam para depois.
- Desenvolvimento e CI: `docker compose up` sobe agente headless com câmera falsa, web e Playwright. A câmera virtual real só é testada fora do Docker, no Windows.
- Portas: console `127.0.0.1:8080` (HTTP, só local), celular `0.0.0.0:8443` (HTTPS na LAN), Vite em dev `5173`.
- O certificado TLS autoassinado e o banco SQLite ficam no diretório de dados do usuário (`%LOCALAPPDATA%\wcam`), nunca no repositório.
- Nunca commitar segredos, `.env`, certificados ou chaves. Configuração de dev só em `.env.example`.

## Comunicação
- Responder sempre em português do Brasil.
