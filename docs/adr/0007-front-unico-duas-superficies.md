# 0007. Front único com duas superfícies servido pelo agente

Status: Aceita
Data: 2026-10-31

## Contexto
O PC e o celular têm interfaces totalmente diferentes em papel, uso e layout (CA-3), mas compartilham tokens de design, idiomas e os tipos do contrato.

## Decisão
Um app React + Vite + TypeScript com duas rotas carregadas por `lazy()`: `/` (console do PC) e `/cam` (celular). Nenhuma tela é compartilhada nem é versão responsiva da outra. O build estático é servido pelo agente: o console pelo servidor local, a `/cam` pelo servidor da LAN. Sem biblioteca de rotas.

## Consequências
- O celular baixa só o código da `/cam`.
- Não existe servidor Node em produção.
- Compartilhados entre as superfícies: `styles/tokens.scss`, `data/contract.ts` e os textos de `locales/`.
