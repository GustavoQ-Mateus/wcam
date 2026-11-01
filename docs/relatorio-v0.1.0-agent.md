# Relatório v0.1.0, sessão agent

De: sessão `agent`
Para: orquestrador
Spec: `docs/specs/spec-v0.1.0.md`
Branch: `feature/fundacao-agent`

## 1. O que foi feito

- `.gitignore`, `.gitattributes` (`* text=auto eol=lf`), `.editorconfig` e `.dockerignore` na raiz; antes não existiam. O índice ficou todo em LF.
- `LICENSE` MIT (Gustavo Queiroz, 2026) e `README.md` mínimo (o que é, estado, como rodar).
- Agente: o rascunho foi revisado contra a spec e entrou com as correções abaixo.
- `network/certificates.py`: `ExtendedKeyUsageOID` passou a vir de `cryptography.x509.oid`; antes o pyright strict acusava 1 erro.
- `network/lan.py`: a escolha da interface segue a regra da spec à risca (IP da rota padrão ou `lan_ip`, e esse IP precisa ser RFC 1918). Antes, quando a rota padrão não batia, o rascunho caía para a primeira interface privada, que pode ser o adaptador virtual do WSL ou do Hyper-V e geraria um QR inalcançável. O parâmetro `required` saiu.
- `app.py`: os dois `uvicorn.Config` usam `proxy_headers=False`. Antes o uvicorn aceitava `X-Forwarded-For` vindo de `127.0.0.1` (ou de `FORWARDED_ALLOW_IPS`), e a checagem de sub-rede depende do IP de origem.
- `cli.py`: a saída do terminal passa a ser UTF-8 quando redirecionada. Antes, no Windows, `wcam > arquivo` caía com `UnicodeEncodeError` no QR (cp1252).
- Revisão do orquestrador: `subnet_guard.py` foi de `network/` para `api/`, e a checagem pura de sub-rede (`is_in_network`, com IPv4 mapeado em IPv6) ficou em `network/lan.py`; antes o middleware ficava em `network/` e importava framework. Erro do framework fora da tabela agora vira `invalid_request` (4xx) ou `internal_error` (5xx); antes virava `http_error`.
- Testes: 29 no total. Os 15 da spec; os extras do rascunho (`test_extra_allowed_host_is_accepted`, `test_console_server_does_not_serve_phone_page`, `test_corrupted_certificate_is_regenerated`, `test_lan_with_unknown_configured_ip_raises`, os 3 de i18n); e 3 novos: `test_lan_without_default_route_raises` (substitui o teste do fallback), `test_servers_ignore_forwarded_client_address` e `test_redirected_output_is_switched_to_utf8`; depois da revisão, `test_client_error_outside_table_returns_invalid_request`, `test_server_error_outside_table_returns_internal_error`, `test_ipv4_mapped_ipv6_address_inside_network_is_accepted` e `test_invalid_address_is_outside_network`.
- `agent/Dockerfile`: dois estágios com contexto na raiz (build do web em `node:24-slim` com `locales/` em `/app/locales`; agente em `python:3.13-slim` com uv 0.13.6, `uv sync --frozen --no-dev`, copiando `web/dist` e `locales/`). Roda como usuário sem root `wcam`.
- `docker-compose.yml`: serviços `agent`, `web` e `e2e` (profile `e2e`) como no handoff. O healthcheck usa `python -c urllib...`, porque a imagem slim não tem curl.
- `.github/workflows/ci.yml`, `.github/workflows/codeql.yml` e `.github/dependabot.yml` como na spec.

Commits: `de86698`, `50f0f2b`, `e02f418`, `cd715e6`, `a2050ec`, `7cd0762`, `366323e` (relatório), o merge `e851138` de `origin/feature/fundacao`, `e47ac5c` (ajustes da revisão) e a atualização deste relatório.

## 2. Critérios de aceitação

| CA | Estado | Evidência |
|---|---|---|
| 1 | Verificado, com ressalva | `uv run wcam` no Windows 11 imprimiu título, `Console neste computador: http://127.0.0.1:8080/`, `Página do celular: https://192.168.100.24:8443/cam`, impressão digital e QR, em pt-BR (idioma do sistema). Em inglês foi visto no container (sem `LANG`). `curl` respondeu nos dois servidores. Encerramento: `signal.raise_signal(SIGINT)` e `SIGTERM` dentro do processo param os dois servidores em cerca de 0,2 s. **Não verificado**: Ctrl+C num terminal interativo, porque este ambiente não tem console (`GetConsoleWindow() == 0`). Peço ao usuário que confira. |
| 3 | Verificado pelo PC, não pelo celular | `curl http://192.168.100.24:8080/api/health` com `exit 7` (conexão recusada), porque o console escuta só em `127.0.0.1`. Pelo celular falta testar, junto com o CA 2. |
| 4 | Verificado | Testes `test_request_from_other_subnet_is_rejected_with_not_same_network` e `test_unknown_host_header_is_rejected_with_invalid_host`. Também na execução real: `Host: evil:8443` recebeu `400 invalid_host`, e `X-Forwarded-For: 8.8.8.8` não muda o IP de origem. |
| 5 | Verificado | 4 testes de certificado mais o de arquivo corrompido. Na execução real, duas execuções seguidas deram a mesma impressão digital, igual à do certificado servido (`openssl s_client`), com `IP Address:192.168.100.24` no SAN. |
| 9 (agent) | Verificado | Em `agent/`: `uv run ruff check` (All checks passed), `uv run ruff format --check` (26 files already formatted), `uv run pyright` (0 errors, 0 warnings), `uv run pytest` (29 passed). `pip-audit` no lock exportado: No known vulnerabilities found. |
| 2 | Não verificado | Depende de celular real e do build do web. Sem `web/dist`, `/cam` responde `503 web_not_built` por HTTPS na LAN (visto com `curl` pelo IP da LAN). |
| 8 | Parcial | Com um `web/` falso (o `build` só gera `dist/index.html`): a imagem do agente foi construída, `docker compose up agent` ficou `healthy`, o console respondeu em `127.0.0.1:8080`, e de outro container na rede do compose `https://agent:8443/api/health`, `https://agent:8443/cam` e `http://agent:8080/api/health` responderam 200. `docker compose --profile e2e config` é válido. Os serviços `web` e `e2e` dependem de `web/Dockerfile` e `web/e2e.Dockerfile`. |
| 10 | Não verificado | Nada foi enviado ao GitHub além do push desta branch. Os jobs `web` e `e2e` só passam depois da integração. |
| 11 (lado agent) | Verificado | Rotas e códigos implementados batem com `docs/contrato.md` depois do merge de `33fda5f`: `GET /api/health` nos dois servidores; `not_same_network`, `invalid_host`, `web_not_built`, `not_found`, `method_not_allowed`, `invalid_request` e `internal_error`, sem código fora da tabela. |

## 3. Divergências da spec ou do contrato

1. `network/lan.py`: o fallback do rascunho foi removido para seguir a spec ("Sem interface válida, o agente encerra"). Consequência: numa LAN sem gateway (sem rota padrão), o agente encerra e é preciso usar `WCAM_LAN_IP`.
2. `proxy_headers=False` nos dois servidores. Não muda o contrato; fecha a falsificação do IP de origem.
3. Spec §5 diz "build do web montado" no `agent`; segui o handoff, que copia o build para dentro da imagem no estágio de web.
4. Resolvidos na revisão (commit `33fda5f` do orquestrador e `e47ac5c` desta branch): o código `http_error` saiu; `errors.method_not_allowed` e `errors.invalid_request` entraram em `locales/`; `subnet_guard` foi para `api/`.
5. Hosts do celular no compose: só `agent:8443` (e o IP do container). Abrir `https://127.0.0.1:8443/cam` no navegador do host com o compose de pé dá `400 invalid_host`. É o comportamento da lista do contrato; registro para não surpreender.
6. CI: `uv sync --frozen` em vez de `uv sync`, e `pip-audit` rodado por `uvx` sobre `uv export --frozen --no-emit-project`, sem entrar como dependência.

## 4. Dependências além da spec

- `types-psutil` (desenvolvimento): stubs para o pyright strict, porque o psutil não traz tipos próprios.
- Imagens: `node:24-slim`, `python:3.13-slim`, `ghcr.io/astral-sh/uv:0.13.6`. Actions: `actions/checkout@v5`, `astral-sh/setup-uv@v7`, `actions/setup-node@v6`, `github/codeql-action@v4`; o Dependabot cuida das atualizações.

## 5. Perguntas para o orquestrador

As perguntas 1 a 3 foram respondidas e aplicadas. Seguem abertas:

1. Confirmação, com a sessão web, de que `web/Dockerfile` usa `WORKDIR /app/web`.
2. Ctrl+C num terminal real e o fluxo com celular (CA 2 e CA 3 pelo celular) ficam com o usuário.
