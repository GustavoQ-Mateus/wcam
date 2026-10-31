# 0006. SQLite como banco local

Status: Aceita
Data: 2026-10-31

## Contexto
O agente é um app desktop de um usuário. Guarda preferências, histórico de sessões e amostras agregadas de métricas. O usuário final não tem Docker nem servidor de banco.

## Decisão
SQLite pelo `sqlite3` da biblioteca padrão, num arquivo no diretório de dados do usuário. Schema por migrations SQL numeradas em `agent/src/wcam/persistence/migrations/`, aplicadas na inicialização. Sem ORM.

## Consequências
- Zero instalação para o usuário.
- Sem Postgres no projeto, nem em desenvolvimento.
- Nada guardado no banco autoriza conexão futura (ADR 0009).
