# Spec v0.1.0, Fundação

Status: Aprovada (2026-10-31)
Branch: `feature/fundacao`
Referências: `docs/planejamento.md`, ADRs 0001 a 0010

## Objetivo

Deixar o repositório pronto para todas as specs seguintes: estrutura do monorepo, ferramentas de qualidade, CI, ambiente Docker de desenvolvimento e um agente que já sobe os dois servidores com HTTPS e checagem de rede. Ao fim, o celular escaneia um QR no terminal e abre a página `/cam` servida pelo PC.

Nenhum vídeo nesta versão.

## Escopo

### 1. Repositório
- `.gitignore` cobrindo `.venv`, `node_modules`, `dist`, `.env`, `*.pem`, `*.key`, `*.sqlite3`, `.taste-skill/`, artefatos do PyInstaller e do Playwright.
- `.editorconfig` (UTF-8, LF, 4 espaços em Python, 2 em TS, JSON, YAML e SCSS).
- `LICENSE` MIT.
- `README.md` mínimo: o que é, estado atual (em desenvolvimento), como rodar em desenvolvimento.
- `docs/contrato.md` inicial com as rotas desta versão e o formato de erro.

### 2. Agente (`agent/`)

Projeto uv com Python 3.13, pacote `wcam` em `src/`, script `wcam = "wcam.cli:main"`.

Dependências de execução, com justificativa:

| Pacote | Por quê |
|---|---|
| fastapi | rotas HTTP e OpenAPI dos dois servidores |
| uvicorn[standard] | servidor ASGI com TLS |
| cryptography | gerar e ler o certificado ECDSA autoassinado |
| segno | QR no terminal (e SVG no console nas próximas versões) |
| pydantic-settings | configuração tipada por variável de ambiente |
| psutil | interfaces de rede com máscara de sub-rede (a biblioteca padrão não expõe a máscara no Windows); depois, uso de CPU para as métricas |

Desenvolvimento: ruff, pyright, pytest, pytest-asyncio, httpx.

Fora desta versão: aiortc, PyAV, pyvirtualcam, pystray, pywebview, PyInstaller (entram na versão que os usa).

Módulos:

- `config.py`: `Settings` com prefixo `WCAM_`.
  - `console_port` (8080), `phone_port` (8443), `console_bind` (`127.0.0.1`), `lan_ip` (opcional, sobrepõe a detecção), `data_dir` (padrão `%LOCALAPPDATA%\wcam` no Windows, `$XDG_DATA_HOME/wcam` ou `~/.local/share/wcam` no resto), `web_dist` (padrão `web/dist`), `extra_allowed_hosts` (lista, vazia por padrão; usada só no compose).
- `network/lan.py`: escolhe a interface da LAN. Regra: a interface IPv4 ativa usada pela rota padrão (descoberta por um socket UDP conectado a um endereço de documentação, sem enviar pacote), com IP privado (RFC 1918). Devolve `LanInterface(ip, network)`. Com `lan_ip` configurado, usa a interface que tem esse IP. Sem interface válida, o agente encerra com mensagem clara e código de saída diferente de zero.
- `network/certificates.py`: `load_or_create_certificate(data_dir, lan_ip)`. ECDSA P-256, SAN com o IP da LAN, validade de 825 dias, arquivos `tls/cert.pem` e `tls/key.pem` no diretório de dados. Reaproveita o certificado existente se o IP estiver no SAN e ele não estiver vencido; senão, gera outro. Devolve o caminho dos arquivos e a impressão digital SHA-256.
- `network/subnet_guard.py`: middleware ASGI do servidor da LAN. IP de origem fora de `LanInterface.network` recebe `403` com `{"error":{"code":"not_same_network","message":...}}`.
- `api/host_guard.py`: middleware nos dois servidores. `Host` fora da lista recebe `400` com código `invalid_host`. Lista do console: `127.0.0.1:<porta>` e `localhost:<porta>`. Lista da LAN: `<ip-da-lan>:<porta>`. Mais `extra_allowed_hosts`.
- `api/errors.py`: formato único de erro e handler para exceções não tratadas (`internal_error`, sem detalhe interno na resposta).
- `api/console_routes.py` e `api/phone_routes.py`: `GET /api/health` em cada um, `{"status":"ok","version":"0.1.0","surface":"console"|"phone"}`.
- `api/static.py`: serve o build do web. Console: `/` e os assets. LAN: `/cam` e só os assets. Qualquer outra rota da LAN fora de `/cam`, `/assets/*` e `/api/*` responde `404`. Sem build presente, as páginas respondem `503` com código `web_not_built`.
- `app.py`: monta as duas aplicações FastAPI e os dois `uvicorn.Server`, rodando juntos no mesmo event loop; encerra os dois em Ctrl+C ou SIGTERM.
- `cli.py`: `wcam` inicia tudo e imprime, em inglês ou português conforme o idioma do sistema: endereço do console, endereço da `/cam`, impressão digital do certificado e o QR da URL da `/cam` no terminal. `wcam --version`.

Textos do terminal vêm de `locales/`, como todo texto de interface.

### 3. Web (`web/`)
- Vite + React + TypeScript estrito (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`).
- SCSS com `styles/tokens.scss` contendo todos os tokens de `docs/planejamento.md` §5.6 e `styles/base.scss` (reset, foco visível com `--focus`, `color-scheme: dark`).
- `router.tsx`: escolhe a superfície pelo caminho, sem biblioteca. `/cam` carrega `cam/cam-page.tsx` e `/` carrega `console/console-page.tsx`, ambos por `lazy()`.
- Páginas desta versão, provisórias, seguindo as regras anti AI slop:
  - console: nome do produto e o estado do agente lido de `GET /api/health` ("Agent running" ou "Agente ativo"; falha mostra o erro pelo `code`).
  - `/cam`: nome do produto e a instrução de parear pelo PC.
  - A direção visual definitiva fica para a spec de front; aqui só tokens e tipografia do sistema.
- `data/i18n.ts`: carrega `locales/<idioma>.json`, idioma por `navigator.language` (`pt*` vira `pt-BR`, qualquer outro vira `en`), função `t(key)` com chaves tipadas a partir de `en.json`.
- `data/api-client.ts`: `fetch` tipado que converte o formato de erro em `ApiError` com `code`.
- `vite.config.ts`: proxy de `/api` para `http://127.0.0.1:8080` em desenvolvimento; build em `web/dist`.
- ESLint (flat config com typescript-eslint strict e react-hooks), Prettier, Vitest, Playwright.
- Scripts: `dev`, `build` (`tsc -b && vite build`), `lint`, `test`, `test:e2e`.

### 4. Idiomas (`locales/`)
- `en.json` e `pt-BR.json` com as mesmas chaves, organizadas por superfície (`terminal.*`, `console.*`, `cam.*`, `errors.<code>`).

### 5. Docker (raiz)
- `agent/Dockerfile`: `python:3.13-slim` com uv, roda `wcam`.
- `web/Dockerfile`: Node LTS, roda `vite` em modo dev.
- `docker-compose.yml`:
  - `agent`: `WCAM_CONSOLE_BIND=0.0.0.0` dentro do container, publicado só em `127.0.0.1:8080` no host; `8443` publicada; `extra_allowed_hosts` com o nome do serviço; build do web montado.
  - `web`: Vite em `127.0.0.1:5173`, proxy para `agent:8080`.
  - `e2e` (profile `e2e`): imagem oficial do Playwright, roda `npm run test:e2e` contra o `agent`.
- O compose é para desenvolvimento e CI. Teste com celular real usa `uv run wcam` nativo (ADR 0008).

### 6. CI (`.github/`)
- `workflows/ci.yml`, em push e pull request:
  - `agent` em matriz `windows-latest` e `ubuntu-latest`: `uv sync`, `ruff check`, `ruff format --check`, `pyright`, `pytest`, `pip-audit`.
  - `web` em `ubuntu-latest`: `npm ci`, `lint`, `build`, `test`, `npm audit --audit-level=high`.
  - `e2e` em `ubuntu-latest`: `docker compose --profile e2e up --build --exit-code-from e2e`.
- `workflows/codeql.yml`: Python e JavaScript/TypeScript.
- `dependabot.yml`: uv, npm, github-actions e docker, semanal.

### 7. Testes

Agente (`agent/tests/`):
- `test_lan_selects_private_interface_of_default_route`
- `test_lan_uses_configured_ip_when_set`
- `test_lan_without_private_interface_raises`
- `test_certificate_is_created_with_lan_ip_in_san`
- `test_certificate_is_reused_when_ip_matches`
- `test_certificate_is_regenerated_when_ip_changes`
- `test_certificate_is_regenerated_when_expired`
- `test_request_from_same_subnet_is_accepted`
- `test_request_from_other_subnet_is_rejected_with_not_same_network`
- `test_unknown_host_header_is_rejected_with_invalid_host`
- `test_console_health_reports_console_surface`
- `test_phone_health_reports_phone_surface`
- `test_phone_server_does_not_serve_console_page`
- `test_missing_web_build_returns_web_not_built`
- `test_unhandled_error_returns_internal_error_without_details`

Os testes de rota usam `httpx.ASGITransport` com o endereço de cliente controlado; a detecção de interface recebe as interfaces por parâmetro, sem depender da máquina.

Web (Vitest):
- `locales have the same keys in every language`
- `language detection maps pt variants to pt-BR and others to en`
- `api client turns error body into ApiError with code`

E2E (Playwright, no compose):
- console abre e mostra o agente ativo;
- `/cam` abre por HTTPS (certificado ignorado no teste) e mostra a instrução de pareamento;
- a página da `/cam` não carrega o chunk do console.

## Fora do escopo
WebRTC, pareamento por token, código de confirmação, câmera virtual, banco, bandeja, janela WebView2, instalador, regra de firewall, direção visual definitiva.

## Critérios de aceitação

1. `uv run wcam` no Windows sobe os dois servidores e imprime o endereço do console, o endereço da `/cam`, a impressão digital do certificado e o QR, no idioma do sistema.
2. Um celular na mesma rede Wi-Fi lê o QR do terminal com a câmera nativa, aceita o aviso de certificado e vê a página `/cam` no idioma do navegador. Registrar no changelog o aparelho e o navegador testados; o sistema não testado (Android ou iOS) fica registrado como não testado.
3. Do celular, `http://<ip-do-pc>:8080` não conecta: o console não é alcançável pela rede.
4. Requisição ao servidor da LAN vinda de fora da sub-rede recebe `403 not_same_network`; `Host` desconhecido recebe `400 invalid_host` (testes automatizados).
5. O certificado é reaproveitado entre execuções (mesma impressão digital) e regenerado quando o IP da LAN muda ou ele vence (testes automatizados).
6. O build gera chunks separados para console e `/cam`, e a `/cam` não carrega o chunk do console (e2e).
7. Os dois idiomas têm as mesmas chaves, e nenhum texto de interface está escrito no código (teste e revisão do diff).
8. `docker compose up` sobe agente e web; `docker compose --profile e2e up --build --exit-code-from e2e` termina com sucesso.
9. Verificação local completa sem erros nem avisos: `ruff check`, `ruff format --check`, `pyright` e `pytest` no agente; `npm run build`, `npm run lint` e `npm test` no web.
10. CI verde no GitHub nos jobs `agent` (Windows e Linux), `web` e `e2e`, e CodeQL sem alerta. Depende do remote criado pelo usuário; até lá, registrar como não verificado.
11. `docs/contrato.md` descreve exatamente as rotas e erros implementados.

## Decisões registradas na aprovação
1. `LICENSE` MIT com titular Gustavo Queiroz (identidade do git do usuário).
2. Repositório `GustavoQ-Mateus/wcam`, público, criado com `gh` na conta `GustavoQ-Mateus`.
3. Exceção única: o primeiro commit (CLAUDE.md e docs) vai direto na `main`, para que a `main` exista. Todo o resto segue o git flow.

## Changelog
Vazio até a entrega.
