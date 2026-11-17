# Backlog de ideias (a validar)

Registrado em 2026-11-16 a pedido do usuário. Nada aqui está aprovado: cada ideia passa pela validação abaixo antes de virar linha do roteiro (`docs/planejamento.md` §6) e spec.

## Princípios que valem para todas

- **Segurança altíssima.** O WCam transmite a câmera de uma pessoa. Nenhuma ideia pode abrir porta, rota, descoberta na rede ou caminho de autorização além do QR (CA-4). Toda ideia nova entra no modelo de ameaças (`docs/seguranca.md`, spec v0.15.0) antes da spec.
- **Local.** Nada sai do PC: sem nuvem, servidor de repasse, fila ou banco externos. O SQLite continua (ADR 0006).
- **Sem fio.** O diferencial do WCam é o Wi-Fi. Cabo e Bluetooth já existem em outros produtos.
- **Arquitetura.** Domínio sem framework, integrações atrás de `Protocol` ou interface, contrato documentado antes do código.
- **Stack.** Python no agente, C# no `vcam` e no que for nativo do Windows. A stack principal do usuário é C#: quando as duas servirem, C# tem preferência.

## Validação de cada ideia

1. **Possível?** Spike curto com medição no PC do usuário (i5-8500, UHD 630) e no iPhone.
2. **Útil?** Qual problema real de quem usa o WCam resolve.
3. **Segurança:** ameaças novas e mitigação, no modelo STRIDE.
4. **Interferência:** o que muda no CA-2 (qualidade), no CA-4, no desempenho da v0.10.0, no contrato e nas versões já planejadas.
5. **Custo:** dependências novas, sessões envolvidas e se é MINOR ou MAJOR.

O resultado vai numa seção da própria ideia abaixo. Aprovada pelo usuário, ela vira linha do §6.

## Funcionalidades

| # | Ideia | Notas para validar |
|---|---|---|
| F1 | Vários celulares, com troca de câmera pelo console como cenas | Destaque do usuário. Cada celular com o seu QR e o seu token; limite de aparelhos; uma sessão por celular muda o modelo de "uma sessão por vez" (MAJOR provável); CPU de várias decodificações (ADR 0018). |
| F2 | Microfone do celular como microfone do PC | Ideia do usuário. Opus pelo WebRTC já existe; dispositivo de áudio virtual no Windows exige driver (difícil) ou dispositivo de terceiros como primeiro passo; sincronia com o vídeo; indicador de microfone ligado no celular e no PC. |
| F3 | Efeitos com IA no PC: fundo desfocado ou trocado, enquadramento que segue o rosto, correção de luz | ONNX Runtime com DirectML (C#); modelos offline e com hash conferido; desligado por padrão com exceção ao CA-2 em ADR, como o recorte da v0.11.0; custo na placa de vídeo junto da decodificação. |
| F4 | Gravação local do que a câmera mostra, em MP4 | Media Foundation com codificação na placa (C#); onde o arquivo fica e quem acessa; aviso visível de gravando no PC e no celular. |
| F5 | Sobreposições: nome, logo, legenda | Composição no PC; desligado por padrão com exceção ao CA-2; textos e imagens só locais. |
| F6 | Integrações: Stream Deck, atalhos globais do Windows, WebSocket do OBS | C#. Toda porta ou canal novo só em localhost e com autorização própria; nada exposto na LAN. |
| F7 | Spike de transporte e codec: WebCodecs com WebTransport, HEVC ou AV1 do celular | Ganho real de latência e qualidade contra o WebRTC atual; suporte no Safari e no Chrome; mexe na ADR 0014 e no contrato. |

## Engenharia e qualidade

As da spec futura v0.15.0 (benchmark em PR, OpenTelemetry com o painel do Aspire, ETW no `vcam`, `tc netem`, modelo de ameaças, fuzzing, testes por propriedade, SBOM e proveniência, falhas provocadas) continuam lá. Somam-se:

| # | Ideia | Notas para validar |
|---|---|---|
| E1 | Contrato gerado de uma fonte só: OpenAPI do FastAPI e JSON Schema do DataChannel geram os tipos TypeScript e os modelos Python, e o CI falha se divergirem | Substitui parte do `docs/contrato.md` escrito à mão; custo da migração. |
| E2 | Testes de arquitetura: import-linter no agente, NetArchTest no `vcam` | As regras do CLAUDE.md (domínio sem FastAPI e aiortc) viram teste. |
| E3 | Analisadores Roslyn próprios (C#) | Por exemplo: exceção escapando de método COM, texto de interface fora de locales. |
| E4 | Teste de mutação: Stryker.NET, mutmut, Stryker no web | Tempo de CI; rodar só agendado. |
| E5 | Regressão visual e acessibilidade: prints do Playwright comparados e axe-core | Estabilidade dos prints no CI. |
| E6 | Comunicação entre o host C# e o agente: named pipes ou gRPC local | Só se o 1.0.0 virar host em C#; pipe com ACL do usuário, nunca porta na rede. |
| E7 | Guia de profiling: py-spy, Scalene, dotnet-trace, PerfView, WPA | Documento, sem código no produto. |

## Entrega e manutenção

| # | Ideia | Notas para validar |
|---|---|---|
| D1 | Versão e changelog automáticos: release-please e commitlint | Convivência com o fluxo de spec e tag atual. |
| D2 | Renovate ou Dependabot com os testes como barreira | Revisão de dependência nova continua pelo orquestrador. |
| D3 | Instalador assinado: Azure Trusted Signing ou SignPath (gratuito para open source) | Tira o aviso do SmartScreen; junto do 1.0.0. |
| D4 | Publicação no WinGet | Junto do 1.0.0. |
| D5 | Site de documentação: DocFX ou MkDocs com ADRs, contrato e solução de problemas | Sem dado do usuário publicado. |

## Já no roteiro como proposta

- 1.0.0 com host em C# (WinUI e Native AOT) e o agente Python como processo filho (§6).
- 2.0.0 com a imagem na placa de vídeo de ponta a ponta (§6, ADR 0018).

## Descartadas

- **Conexão por cabo USB e Bluetooth:** já existem em outros produtos; o WCam é sem fio (usuário, 2026-11-16).
- **Descoberta na rede por mDNS:** anuncia na LAN que há uma câmera disponível e quebra a regra de nada além do QR (usuário, 2026-11-16).
- **Servidor na nuvem, repasse de mídia, fila ou banco externos, Kubernetes, Kafka, RabbitMQ:** o WCam é local e não tem serviços distribuídos.
- **SQL Server ou LocalDB:** exigiriam instalar um serviço no PC de cada usuário, sem ganho.
- **Reescrever o agente em C#:** sem medição publicada de recepção H.264 em 4K no SIPSorcery, e o custo da passagem entre nativo e .NET é um problema conhecido; risco alto para trocar o que funciona.
