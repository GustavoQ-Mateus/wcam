# Relatório v0.1.0, sessão web

Spec: `docs/specs/spec-v0.1.0.md`
Handoff: `docs/handoff-v0.1.0-web.md`
Branch: `feature/fundacao-web` (com `origin/feature/fundacao` em 33fda5f já integrada)

## 1. O que foi feito

- `web/` criado do zero, sem template: Vite + React + TypeScript com `strict`, `noUncheckedIndexedAccess` e `exactOptionalPropertyTypes` em `tsconfig.app.json` e `tsconfig.node.json`, com referências a partir de `tsconfig.json`.
- `styles/tokens.scss` com todos os tokens de cor de `docs/planejamento.md` §5.6 em `:root`, mais tokens de tipografia, espaçamento e foco (ver divergência 1).
- `styles/base.scss`: reset, `color-scheme: dark`, foco visível com `--focus` em 2px e 2px de afastamento, sem destaque de toque.
- `router.tsx` sem biblioteca: `/cam` (com ou sem barra final) carrega `cam/cam-page.tsx`, o resto carrega `console/console-page.tsx`, ambos por `lazy()`.
- `data/i18n.ts` puro: `resolveLanguage` (`pt*` vira `pt-BR`, o resto vira `en`), `translate` com chaves tipadas a partir de `locales/en.json` e placeholders `{nome}`, `errorMessageKey(code)` com queda para `errors.unknown`. O tipo também obriga `pt-BR.json` a ter todas as chaves de `en.json` em tempo de compilação.
- `data/language.ts`: único lugar que lê `navigator.language`; `main.tsx` define `document.documentElement.lang` e `document.title`.
- `data/api-client.ts`: `requestJson` e `fetchHealth`; corpo de erro do contrato vira `ApiError` com `code` e `status`; falha de rede vira `network_error` com `status` 0; resposta de erro fora do formato vira código local `unknown` (cai em `errors.unknown`).
- `data/contract.ts`: `Surface`, `Health` e `ErrorBody`.
- `data/use-health.ts`: hook com estados `checking`, `running` e `failed`, cancelado no desmonte.
- Console provisório: nome do produto e o estado do agente, com texto e forma (anel vazio verificando, círculo verde ativo, quadrado vermelho em erro).
- `/cam` provisória: nome e `cam.pair_instruction` em tela cheia, com `100dvh` e áreas seguras.
- `index.html` com `viewport-fit=cover`, `theme-color` preto e `color-scheme` escuro.
- `vite.config.ts`: proxy de `/api` para `VITE_AGENT_URL` ou `http://127.0.0.1:8080` com `changeOrigin`, `server.fs.allow` na raiz do repositório, build em `web/dist`, Vitest só em `src/**/*.test.ts`.
- ESLint flat (`@eslint/js`, `typescript-eslint` strict, `react-hooks` recommended), Prettier (largura 120), Vitest, Playwright; scripts `dev`, `build`, `lint` (ESLint e `prettier --check`), `test`, `test:e2e`.
- Testes Vitest: os três da spec e mais três (placeholders, queda para `errors.unknown`, `network_error`).
- E2E: console mostra o agente ativo; `/cam` abre por HTTPS e mostra a instrução; `/cam` não pede nenhum arquivo com `console-page` no nome. Leem `E2E_CONSOLE_URL` e `E2E_PHONE_URL` e falham com mensagem clara se faltarem; ignoram erro de certificado; locale fixo `en-US`; textos esperados vêm de `translate`, não do código.
- `web/Dockerfile` (Node 24, `WORKDIR /app/web`, `npm ci`, `npm run dev -- --host 0.0.0.0`) e `web/e2e.Dockerfile` (`mcr.microsoft.com/playwright:v1.64.1-noble`, copia `web/` e `locales/`, `npm ci`, `npx playwright test`), ambos com contexto na raiz.
- `web/Dockerfile.dockerignore` e `web/e2e.Dockerfile.dockerignore` para não copiar `node_modules`, `dist` e `agent/` do host (o BuildKit lê `<Dockerfile>.dockerignore` sem precisar de arquivo na raiz).
- `web/.gitignore` com `node_modules`, `dist`, `*.tsbuildinfo`, `playwright-report` e `test-results`, porque a raiz ainda não tem `.gitignore` nesta branch.

Commits: d579fe2, cfa7f8f, 7636de5.

## 2. Critérios de aceitação

| CA | Situação | Evidência |
|---|---|---|
| 6 | Verificado no build e em e2e contra servidor falso; falta e2e contra o agente real | `npm run build` gera `assets/console-page-*.js` e `assets/cam-page-*.js` separados, e o `dist/index.html` não pré-carrega `console-page`. Os três e2e passaram (Chromium local) contra um servidor Node descartável que serve o `dist` real em HTTP e em HTTPS autoassinado, com `/api/health` do contrato. O e2e no compose depende da integração com o agente. |
| 7 | Verificado (lado web) | Teste `locales have the same keys in every language` passa; nenhum texto de interface no código: páginas e título usam `t()`, e os e2e esperam textos vindos de `translate`. O tipo de `MESSAGES` também falha a compilação se faltar chave em `pt-BR`. |
| 9 | Verificado (lado web) | Em `web/`: `npm run build` sem avisos, `npm run lint` sem erros nem avisos (ESLint e Prettier), `npm test` com 6 testes passando. |

Verificado também no navegador (Playwright com Chromium): console em `en` e `pt-BR`, `lang` do documento correto, erro de rede e `not_same_network` mostrando o texto de `errors.<code>`, `/cam` em viewport de celular (Pixel 7) em `pt-BR`. Não verificado em celular real: a `/cam` só fica alcançável com o agente servindo na LAN.

Docker: as duas imagens constroem a partir da raiz; o contêiner de dev sobe o Vite em `0.0.0.0:5173`, serve `/cam` e lê `/app/locales` pelo `fs.allow`; a imagem de e2e tem Playwright 1.64.1, igual ao `package-lock.json`. Não testado: `docker compose` (arquivo da sessão agent).

## 3. Divergências

1. `tokens.scss` tem, além das cores de §5.6, tokens de tipografia (`--font-system`, tamanhos, alturas de linha, peso), espaçamento (`--space-*`), largura de texto, foco e indicador. Motivo: o CLAUDE.md proíbe espaçamento solto no SCSS e §5.6 só define cores. Valores provisórios até a spec de front.
2. `index.html` não tem `<title>`; o título vem de `t("app.name")` em `main.tsx`, para não escrever texto de interface no HTML.
3. Imports de JSON usam `with { type: "json" }`. Motivo: o Playwright carrega `src/data/i18n.ts` como ESM nativo do Node, que exige o atributo.
4. Resposta de erro sem o corpo do contrato (por exemplo, proxy sem agente) vira código local `unknown`. O contrato não define esse caso; a tela mostra `errors.unknown`.
5. `package.json` tem `overrides` com `minimatch` 11.0.3: o `minimatch` 10.2.6 puxado pelo ESLint tinha alerta moderado (GHSA-g3hv-75wg-m249). Com o override, `npm audit` fica sem vulnerabilidades.
6. Skills de design não foram usadas: o handoff deixa a direção visual para a spec de front. Apliquei só tokens, tipografia do sistema, regras anti AI slop e o básico de `mobile-native` (`100dvh`, áreas seguras, sem destaque de toque).

## 4. Versões fixadas (exatas)

| Pacote | Versão |
|---|---|
| react, react-dom | 19.3.1 |
| vite | 8.3.5 |
| @vitejs/plugin-react | 6.1.2 |
| typescript | 6.0.3 |
| @playwright/test | 1.64.1 (imagem `mcr.microsoft.com/playwright:v1.64.1-noble`) |
| vitest | 5.0.5 |
| eslint | 10.14.0 |
| typescript-eslint | 8.72.1 |
| eslint-plugin-react-hooks | 7.1.1 |
| prettier | 3.9.10 |
| sass-embedded | 1.107.1 |
| @types/node | 24.19.2 (linha do Node 24) |

## 5. Perguntas para o orquestrador

1. Falta `.gitattributes` na raiz com `* text=auto eol=lf`. Com `core.autocrlf=true` no Windows, um checkout novo traz CRLF e o `prettier --check` do `npm run lint` falha. Proposta: entrar na sessão que cuida da raiz.
2. O compose monta `./web` em `/app/web`: com o `.dockerignore` por Dockerfile o build fica limpo, mas o volume anônimo em `/app/web/node_modules` é obrigatório para não usar o `node_modules` do Windows. Só confirmando que fica assim.
3. Em dev, com o agente fora do ar, o proxy do Vite responde 502 sem corpo e o console mostra `errors.unknown`, não `errors.network_error`. Em produção não acontece (o próprio agente serve o console). Se quiser `network_error` também em dev, é uma linha no `api-client` (502/504 sem corpo do contrato vira `network_error`); não fiz porque o contrato não pede.
4. A raiz ainda não tem `.gitignore` (§1 da spec); por isso existe `web/.gitignore`. Quando o da raiz entrar, posso remover o meu ou manter, como preferir.
