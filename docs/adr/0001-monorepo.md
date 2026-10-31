# 0001. Monorepo com agent e web

Status: Aceita
Data: 2026-10-31

## Contexto
O WCam tem um agente no PC e uma interface web servida por ele. Os dois mudam juntos: o contrato entre eles (rotas, DataChannel, SSE) é interno ao produto e não tem outros consumidores.

## Decisão
Um repositório único com `agent/` (Python), `web/` (React), `installer/`, `locales/` e `docs/`. Specs, ADRs e contrato ficam em `docs/` e valem para o repositório inteiro.

## Consequências
- Uma mudança de contrato sai num único PR, com os dois lados verificados juntos.
- O CI roda jobs separados por pasta.
- Não há versionamento independente entre agente e web; a versão é a do produto.
