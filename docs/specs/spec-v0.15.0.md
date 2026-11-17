# Spec v0.15.0, Engenharia e observabilidade

Status: Draft (spec futura, registrada em 2026-11-16 a pedido do usuário; revisar antes de aprovar, depois da v0.14.0)
Branch de integração: `feature/engineering`
Sessões: `agent`, `vcam`, `web` (pouco), `ci`
Referências: `docs/planejamento.md` §1 (CA-2, CA-4), §6; ADR 0006 (SQLite), ADR 0011 (câmera nativa), ADR 0018 (decodificação em processo separado); spec v0.10.0 (medição manual de desempenho).

## Objetivo

Provar com ferramentas de mercado o que hoje é medido à mão: desempenho medido em cada PR, telemetria num padrão aberto, rede ruim simulada, segurança verificada e falhas provocadas de propósito. Tudo continua local: nada sai do PC, sem servidor, fila ou banco externos (decisão do usuário em 2026-11-16). O banco continua o SQLite da ADR 0006. A versão também amplia a parte em C#.

## 1. Desempenho medido em cada PR

- Benchmark do agente: decodificação, tradução de cor e entrega com fluxos H.264 gravados (1080p30 e 2160p30) e o vídeo de teste HEVC, em software (o CI não tem placa de vídeo). O resultado é p50, p95 e CPU por etapa.
- Benchmark do `vcam` com BenchmarkDotNet: cópia do quadro para o buffer do Media Foundation e a troca de formato.
- O resultado de cada PR é comparado com o da `main`. Piora acima de um limite (definido com a medição da v0.10.0) falha o check; o histórico fica publicado nas páginas do repositório.

## 2. Telemetria com OpenTelemetry

- Os tempos por etapa do `/dev` passam a ser também métricas OpenTelemetry. Cada quadro amostrado vira um trace com um span por etapa: celular, rede, decodificar, cópia da placa, cor, entrega.
- Exportação OTLP só para `127.0.0.1` e só com `WCAM_OTLP_ENDPOINT` definido; sem a variável, nada é exportado e o custo é zero.
- No `docker compose`, um perfil opcional `observability` sobe o painel standalone do Aspire (`mcr.microsoft.com/aspire/dashboard`), que recebe OTLP e mostra traces e métricas sem nenhum outro serviço.
- No `vcam` (processo do Frame Server, sem rede): eventos por `EventSource` (ETW) para início, parada, troca de formato e quadro atrasado, mais um perfil do Windows Performance Recorder no repositório para capturar o Frame Server junto do agente.
- O `/dev` continua sendo a tela do usuário; a telemetria é para quem desenvolve.

## 3. Rede ruim simulada

- No e2e, o tráfego entre o celular falso e o agente passa por `tc netem`: perdas de 1%, 5% e 10%, atraso de 50 a 200 ms, jitter e queda de 5 s.
- Cada cenário verifica que a imagem volta sem novo QR, quanto tempo leva e quantos quadros congelam. Os números vão para o changelog e servem de base para a v0.13.0 (robustez), se ela vier antes.

## 4. Segurança verificada (CA-4)

- Modelo de ameaças STRIDE em `docs/seguranca.md`: porta da LAN, QR e token, DataChannel, upload de vídeo, câmera no Frame Server.
- Fuzzing das mensagens do DataChannel, das rotas HTTP do celular e do upload de vídeo (Atheris, ou Hypothesis com geração de bytes).
- Testes por propriedade com Hypothesis: regras da linha do tempo, uso único e expiração do token, limite de tentativas.
- `dotnet test` do `vcam` com entradas inválidas nas funções exportadas, sem exceção escapando para o Frame Server.
- No CI: SBOM em CycloneDX (Python, npm e .NET), varredura de dependências e proveniência SLSA dos artefatos do build.

## 5. Falhas provocadas

- Testes que derrubam no meio do fluxo o processo de decodificação (ADR 0018), o backend da câmera virtual e a conexão do celular, e verificam que a sessão sobrevive ou termina com o motivo certo.
- Teste de vazamento: 2 h de fluxo simulado com memória, handles e threads do agente e do Frame Server medidos no começo e no fim.

## Fora do escopo

- Servidor na nuvem, repasse de mídia (TURN), fila ou banco externos: o WCam é local (decisão do usuário em 2026-11-16).
- Kubernetes, Kafka e RabbitMQ: não há serviços distribuídos para orquestrar.
- Trocar o SQLite: SQL Server ou LocalDB exigiriam instalar um serviço no PC do usuário, sem ganho para um usuário só.

## Critérios de aceitação

1. Benchmark do agente e do `vcam` em todo PR, comparado com a `main`, falhando acima do limite; histórico publicado.
2. Com `WCAM_OTLP_ENDPOINT`, traces e métricas por etapa aparecem no painel do Aspire do perfil `observability`; sem a variável, a CPU fica igual à da versão anterior.
3. Eventos ETW do `vcam` capturados pelo perfil do WPR durante uma reunião.
4. Cenários de `tc netem` no e2e com os tempos de recuperação registrados.
5. `docs/seguranca.md` com o modelo de ameaças, fuzzing e testes por propriedade no CI sem falha, SBOM e proveniência nos artefatos.
6. Testes de falha provocada e de vazamento passando.
7. Verificação completa do CLAUDE.md.
