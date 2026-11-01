# Handoff v0.1.0, sessão agent

De: orquestrador
Para: sessão `agent`
Spec: `docs/specs/spec-v0.1.0.md` (Aprovada)
Contrato: `docs/contrato.md`

## Onde trabalhar

- Pasta: `G:\Dev\Projetos\WCam\.worktrees\agent` (worktree já criado). Faça `cd` para ela antes de qualquer coisa e trabalhe só dentro dela.
- Branch: `feature/fundacao-agent`, criada a partir de `feature/fundacao`. PR para `feature/fundacao`, nunca para `main`.
- Não edite `docs/`, `locales/` nem `web/`. Precisou mudar algo neles, registre no relatório e o orquestrador decide.
- uv: instalado em `C:\Users\gusta\AppData\Roaming\Python\Python312\Scripts`, fora do PATH. Acrescente esse caminho ao PATH da sessão. O Python 3.13 já está instalado pelo uv.

## Ponto de partida

O worktree já contém um rascunho de `agent/` escrito antes da divisão de sessões, **sem commit e sem verificação completa**. Ele cobre `config.py`, `i18n.py`, `network/` (lan, certificates, subnet_guard), `api/` (errors, host_guard, health, console_routes, phone_routes, static), `app.py`, `cli.py` e 23 testes. A última rodada teve uma falha (faixas de documentação tratadas como privadas), corrigida em `network/lan.py` sem nova rodada.

Trate o rascunho como código de outra pessoa: revise contra a spec e o CLAUDE.md, rode a verificação completa, corrija o que divergir e só então faça commit. Pode reescrever o que achar necessário.

## Escopo

Da spec v0.1.0:

- §1 Repositório: `.gitignore` (inclui `.worktrees/`), `.gitattributes` com `* text=auto eol=lf` (o git local está com `autocrlf`), `.editorconfig`, `.dockerignore` na raiz (exclui `.worktrees/`, `.git/`, `**/node_modules`, `**/.venv`, `**/dist`), `LICENSE` MIT com titular "Gustavo Queiroz" e ano 2026, `README.md` mínimo. O `docs/contrato.md` já foi escrito pelo orquestrador; confira que o código bate com ele.
- §2 Agente completo.
- §5 Docker: `agent/Dockerfile` e `docker-compose.yml` na raiz.
  - `agent/Dockerfile` com contexto na raiz, em dois estágios: build do web (`web/package.json`, `web/package-lock.json`, `npm ci`, `npm run build`, com `locales/` copiado para `/app/locales`) e agente em `python:3.13-slim` com uv, `uv sync --frozen --no-dev`, copiando `web/dist` e `locales/`.
  - Compose: serviço `agent` com `WCAM_CONSOLE_BIND=0.0.0.0`, `WCAM_EXTRA_ALLOWED_HOSTS=["agent:8080","agent:8443"]`, portas publicadas só em `127.0.0.1` (`127.0.0.1:8080:8080` e `127.0.0.1:8443:8443`) e healthcheck em `http://127.0.0.1:8080/api/health`. Serviço `web` construído por `web/Dockerfile` (da sessão web), com `./web` e `./locales` montados, volume anônimo para `/app/web/node_modules`, `VITE_AGENT_URL=http://agent:8080` e porta `127.0.0.1:5173:5173`. Serviço `e2e` (profile `e2e`) construído por `web/e2e.Dockerfile` (da sessão web), com `E2E_CONSOLE_URL=http://agent:8080` e `E2E_PHONE_URL=https://agent:8443`, dependendo do `agent` saudável.
  - A porta 8443 publicada só em `127.0.0.1` é intencional: pelo Docker o celular não chega ao agente, e o NAT do Docker anularia a checagem de sub-rede. Celular real só com `uv run wcam` nativo.
- §6 CI: `.github/workflows/ci.yml`, `.github/workflows/codeql.yml` e `.github/dependabot.yml`, exatamente como na spec. Os jobs `web` e `e2e` rodam os comandos da spec dentro de `web/`; eles só ficam verdes depois da integração com a branch web.
- §7 Testes do agente: todos os nomes listados na spec, mais os que o rascunho acrescentou.

Fora do seu escopo: tudo em `web/` (incluindo `web/Dockerfile` e `web/e2e.Dockerfile`), `locales/` e `docs/`.

## Critérios de aceitação sob sua responsabilidade

CA 1, 3, 4, 5 e 9 (lado agente) da spec, verificados na sua branch.

CA 2 (celular real), 8 (compose) e 10 (CI) dependem da integração com a branch web. Deixe tudo pronto e registre no relatório o que já deu para verificar sozinho. Para o CA 2 você pode testar o agente sozinho: com a pasta `web/dist` ausente, `/cam` responde `503 web_not_built`, o que já prova HTTPS, certificado e checagem de sub-rede vindos do celular.

## Verificação antes de cada commit

A partir de `.worktrees/agent/agent`: `uv run ruff check`, `uv run ruff format --check`, `uv run pyright`, `uv run pytest`. Nada de aviso.

## Commits

Conventional Commits com escopo `agent`, `ci` ou `docs`, um por unidade lógica, sem qualquer referência a Claude ou Anthropic. Push para `origin/feature/fundacao-agent` liberado; PR só quando o orquestrador pedir.

## Relatório

Ao terminar, escreva `docs/relatorio-v0.1.0-agent.md` na sua branch (é a única exceção à regra de não editar `docs/`), com:

1. O que foi feito, uma linha por mudança.
2. Cada CA sob sua responsabilidade: verificado, não verificado ou falhou, com a evidência (comando e resultado resumido).
3. Divergências da spec ou do contrato, com o motivo.
4. Dependências novas além das da spec, com justificativa.
5. Perguntas em aberto para o orquestrador.

Depois avise o orquestrador (`wcam-c8`) por mensagem.
