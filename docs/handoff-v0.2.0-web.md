# Handoff v0.2.0, sessão web

De: orquestrador
Para: sessão `web`
Spec: `docs/specs/spec-v0.2.0.md` (Aprovada)
Contrato: `docs/contrato.md` (sem mudança nesta versão)

## Onde trabalhar

- Pasta nova: `G:\Dev\Projetos\WCam\.worktrees\web-captura` (worktree já criado). Faça `cd` para ela e trabalhe só dentro dela. O worktree antigo `.worktrees\web` é da v0.1.0 e não deve mais ser usado.
- Branch: `feature/captura-web`, criada a partir de `feature/captura`. PR futuro para `feature/captura`.
- Não edite `agent/`, `locales/`, arquivos da raiz nem `docs/`, com duas exceções: `docs/design-v0.2.0-cam.md` (fase 1) e `docs/relatorio-v0.2.0-web.md` (fechamento).

## Fase 1: forma

Antes de qualquer código de tela, faça a passada de design da `/cam` com as skills do CLAUDE.md. Carregue cada uma pela ferramenta de skills:

1. `taste-skill`: leia `references/app-screens.md` inteiro (regras de app screen, §12 do celular, §13 regras da casa). A `/cam` é uma tela de uso, não uma página de marketing.
2. `impeccable`, com `/impeccable shape`, para os oito estados da spec.
3. `mobile-native` para o comportamento de celular da seção "Comportamento de celular" da spec.
4. `emil-design-eng` para toque, transição entre estados e detalhes.

Restrições já decididas que a fase 1 não muda:
- Paleta e estilo de `docs/planejamento.md` §5.6 (`true-black-flat`): elevação só por luminosidade, cor só em dado e estado, tally em `--data` (a tally real entra na v0.3.0; nesta versão o estado `ready` não está "ao vivo").
- Ideia de §5.1: linguagem de estúdio de transmissão. A `/cam` é o visor da câmera: tela cheia, sem moldura, quase nada além da imagem.
- Regras anti AI slop do CLAUDE.md.

Entregue `docs/design-v0.2.0-cam.md` com o que a spec pede na fase 1: layout de cada estado em paisagem e em retrato, hierarquia, controles e tamanhos, tipografia (uma família, com justificativa), tokens novos de espaço e tipo, movimento, revisão dos textos da tabela "Textos" e, em cada decisão, a skill que a guiou. Faça commit e push e me avise. **Pare aí**: a fase 2 só começa depois da aprovação do usuário, que eu repasso.

## Fase 2: implementação

Depois da aprovação:
- Faça `git merge origin/feature/captura`, que vai trazer as chaves novas de `locales/` adicionadas por mim a partir da fase 1.
- Implemente a seção "Fase 2" da spec, com os testes Vitest e Playwright listados.
- Rode `impeccable audit` na `/cam` e registre o resultado (CA 12).
- O teste no celular real (CA 2, 4, 5, 6 e 7) é feito pelo usuário com o agente rodando. Deixe tudo pronto e me avise.

## Verificação antes de cada commit

A partir de `.worktrees/web-captura/web`: `npm run build` sem avisos, `npm run lint` e `npm test`. Antes do relatório final, também `npm run test:e2e` contra o compose (`docker compose --profile e2e up --build --exit-code-from e2e`, a partir da raiz do worktree).

## Commits

Conventional Commits com escopo `web` ou `docs`, um por unidade lógica, sem qualquer referência a Claude ou Anthropic. Push para `origin/feature/captura-web` liberado. Não abra PR.

## Relatório

No fim da fase 2, escreva `docs/relatorio-v0.2.0-web.md` no mesmo formato da v0.1.0: o que foi feito, cada CA com estado e evidência, divergências, dependências novas e perguntas. Depois me avise (`wcam-c8`).
