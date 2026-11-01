# Handoff v0.3.0, sessão web

De: orquestrador
Para: sessão `web`
Spec: `docs/specs/spec-v0.3.0.md` (Aprovada)
Contrato: `docs/contrato.md` (versão 0.3.0)

## Onde trabalhar

- Pasta: `G:\Dev\Projetos\WCam\.worktrees\web-pareamento` (worktree já criado). Faça `cd` para ela e trabalhe só dentro dela.
- Branch: `feature/pareamento-web`, criada a partir de `feature/pareamento`. PR futuro para `feature/pareamento`.
- Não edite `agent/`, `locales/`, arquivos da raiz nem `docs/`, exceto `docs/design-v0.3.0-cam.md` e o relatório.
- A sessão agent trabalha ao mesmo tempo. O ponto de encontro é o contrato: siga-o à risca. Se algo nele não fechar, pare e me pergunte.

## Fase 1: forma dos estados novos da `/cam`

Mesmo processo da v0.2.0, com as quatro skills (`taste-skill`, `impeccable shape`, `mobile-native`, `emil-design-eng`):
- os sete estados novos da tabela da spec;
- a tally no topo do trilho, já reservado no design da v0.2.0;
- o código de confirmação em tamanho grande, legível de relance com o celular no suporte;
- a revisão dos textos `cam.*` novos, que já estão em `locales/` com o texto inicial da spec.

Entregue `docs/design-v0.3.0-cam.md` com a skill de cada decisão, faça commit e push e me avise. **Pare aí.** A aprovação do usuário vem antes de qualquer código de tela da `/cam`.

Enquanto espera a aprovação, você pode adiantar a parte que não é tela da `/cam`: `data/confirmation-code.ts` com os três vetores do contrato, `media/use-publisher.ts` e os estados novos em `data/cam-state.ts`, com testes.

## Fase 2

- A `/cam` com os estados aprovados.
- O console provisório da seção "Escopo da sessão web" da spec. Não tem passada de design, mas segue as regras anti AI slop e os tokens.
- Os e2e no compose contra o agente real. O fluxo completo:
  1. o teste pede `POST /api/pairing` no console e monta a URL da `/cam` com o token;
  2. a `/cam` com câmera falsa chega a `awaiting_confirmation`, com o mesmo código que `GET /api/status` mostra;
  3. o teste confirma;
  4. a `/cam` mostra `live` e o status passa a ter `video`.

  Mais os e2e de token reutilizado (`pairing_failed`) e de recusa (`ended`).
- `impeccable audit` dos estados novos (CA 12), e taste `lint.mjs` e `inspect.mjs --app` como na v0.2.0, registrados no relatório.
- Versão 0.3.0 em `web/package.json`.

Os textos estão todos em `locales/`. Se a fase 1 propuser ajustes nas chaves `cam.*`, eu aplico na integração e você faz merge.

## Verificação antes de cada commit

A partir de `.worktrees/web-pareamento/web`: `npm run build` sem avisos, `npm run lint` e `npm test`. Antes do relatório, o e2e no compose.

## Commits e relatório

Conventional Commits com escopo `web` ou `docs`, sem referência a Claude ou Anthropic. Push liberado; PR não. No fim, `docs/relatorio-v0.3.0-web.md`, e me avise (`wcam-c8`).
