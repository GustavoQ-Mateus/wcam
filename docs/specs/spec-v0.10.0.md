# Spec v0.10.0, Desempenho

Status: Aprovada (2026-11-15)
Branch de integração: `feature/performance`
Sessões: `agent`, `web` (pouco), `vcam` só se a ADR da §4 pedir
Referências: `docs/planejamento.md` §1 (CA-1, CA-2), §6 (linha 0.10.0); ADR 0014 (H.264 e decodificação no hardware como próximo passo); ADR 0016 e 0017 (vídeo como câmera); spec v0.8.0, changelog (quedas de fps no `/dev`, limite do indicador); spec v0.9.0, changelog (CA 8, CPU do HEVC 4K); spec v0.7.0 §1.3 (formato pendente até o app reabrir a câmera).

## Objetivo

Deixar a imagem lisa em 4K e o WCam leve no PC. Hoje o custo está no processador: a decodificação do celular em 2160p30 leva de 19 a 23 ms por quadro (ADR 0014), a tradução de cor cerca de 16 ms em 1080p com picos de mais de 100 ms (v0.8.0), e um vídeo 4K HEVC da biblioteca usa cerca de 2,4 núcleos (v0.9.0). Esta versão passa a decodificação para a placa de vídeo, tira a tradução de cor do caminho que trava, explica as quedas de fps vistas em reunião e resolve a troca de formato com o app aberto.

Base para medir: PC do usuário (i5-8500, 6 núcleos, Intel UHD 630), iPhone do usuário, `IMG_0641.MOV` (4K HEVC). Toda medição de "antes" é feita na v0.9.0, no começo da versão, com o mesmo procedimento do "depois".

## 1. Agent

### 1.1 Decodificação na placa de vídeo

- O H.264 do celular e os vídeos da biblioteca (H.264 e HEVC) são decodificados na placa de vídeo quando ela suporta o codec e o perfil. Caminho escolhido pelo spike da §1.6 e registrado em ADR nova, preferindo o que o PyAV já traz (FFmpeg com `d3d11va` ou `dxva2`) antes de qualquer dependência nova.
- Fallback para a decodificação em software do PyAV, sem derrubar a sessão nem parar o vídeo: placa sem suporte, driver ausente, erro ao abrir ou erro no meio do fluxo. Na falha no meio, o próximo quadro-chave já sai em software; o celular recebe um pedido de quadro-chave (PLI) para não esperar o intervalo normal.
- CA-2: a decodificação de H.264 é exata pela norma, então o quadro na placa de vídeo tem que ser igual, byte a byte, ao quadro em software. Teste com o vídeo de referência do e2e no Windows: mesmos planos Y, U e V nos dois caminhos.
- A cópia da placa de vídeo para a memória e a passagem para I420 (de NV12, quando for o caso) ficam fora do event loop e são medidas como etapa própria no `/dev`.
- `WCAM_HW_DECODE` (`auto` padrão, `off` força software) para medir os dois caminhos e para o CI, que não tem placa de vídeo.
- Emenda de 2026-11-18 (ADR 0019, medição com o celular real): com `auto`, o celular ao vivo é decodificado no processador e só o vídeo da biblioteca usa a placa de vídeo; `on` força a placa também no celular. Limite de atraso nos dois caminhos: quadro do celular mais de 200 ms atrás do relógio é descartado até o próximo quadro-chave, com pedido de quadro-chave ao celular. Teste: fila que não cresce com decodificação mais lenta que o tempo do quadro.

### 1.2 Tradução de cor

- A tradução de cor (faixa cheia para limitada, curva de exibição da v0.6.0, retrato com faixas, espelho) não pode prender o event loop nem disputar o GIL com a recepção. Técnica escolhida pelo agent com medição (operações que liberam o GIL, swscale do PyAV com faixa e matriz explícitas, tabela aplicada num só passo, ou junto da etapa da §1.1), registrada no relatório.
- Resultado igual ao de hoje: teste de igualdade de bytes contra a implementação da v0.9.0 em quadros de faixa cheia, limitada, retrato e espelhado. SSIM do e2e continua acima de 0,98.

### 1.3 Quedas de fps em reunião

- Investigação com o `/dev`: reunião de 30 min no Meet em 2160p30 e em 1080p30, CSV exportado, separando o que é do celular (`qualityLimitationReason`, fps enviado), da rede (ida e volta, perdas, jitter) e do PC (tempos por etapa, descartes, CPU).
- O que for do PC é corrigido nesta versão. O que for do celular ou da rede fica registrado no relatório com os números, sem correção.

### 1.4 Troca de formato com o app aberto

- Hoje o formato novo espera o app reabrir a câmera (spec v0.7.0 §1.3). Spike: reiniciar a câmera virtual no formato novo com o app aberto e medir, em Meet, Teams, Zoom, Discord, OBS e app Câmera, se o app volta sozinho, em quanto tempo e com que formato.
- ADR nova com a tabela por app. Se a maioria voltar sozinha em até 3 s, a troca passa a ser imediata (com o console avisando do piscar); senão, o comportamento atual fica e a ADR diz por quê. Mudança no `vcam` só se a ADR pedir, com sessão própria.

### 1.5 Vídeo como câmera

- A reprodução da biblioteca (ADR 0017) usa a decodificação da §1.1. O vídeo 4K HEVC mantém o CA 8 da v0.9.0 (abaixo de 1% de quadros repetidos ou pulados por atraso) com a câmera em 4K.

### 1.6 Spike de decodificação (primeiro)

Antes do código da §1.1, o agent mede e me manda:
- quais `hwaccel` o PyAV instalado oferece no Windows e quais perfis a UHD 630 decodifica (H.264 High, HEVC Main e Main 10);
- se dá para usar o decodificador na placa de vídeo dentro da recepção do aiortc sem copiar o aiortc (ponto de extensão ou troca do decodificador da faixa), e o custo de cada opção;
- tempo por quadro e CPU em 1080p30 e 2160p30, software contra placa de vídeo, com a cópia para a memória incluída.

Se o PyAV não tiver um caminho usável, o spike lista as alternativas com custo (decodificador do Media Foundation pelo `vcam`, outra biblioteca) e eu decido com o usuário antes de seguir.

## 2. Web

- Detalhes do console: como o PC está decodificando a imagem, "placa de vídeo" ou "processador", só na área de detalhes (métrica técnica, §5.7).
- `/dev`: a etapa nova de cópia da placa de vídeo nos tempos por etapa; o indicador "Processamento p95" com o limite revisto pelo agent a partir das medições (hoje fica em atenção o tempo todo em 1080p, changelog da v0.8.0). Mesmo estilo de gráfico.
- Melhoria anotada na v0.9.0, se couber sem atrasar: zoom da linha do tempo também por Ctrl com a roda do mouse sobre a faixa.

## 3. Contrato (`docs/contrato.md` vai para 0.10.0)

- `session.video.decoder` e `videoSource.decoder`: `hardware` ou `software` (`null` sem quadro); mudança conta para o SSE do console.
- `GET /api/dev/events`: etapa `transfer` nos tempos por etapa (passagem para I420 e cópia entre processos; a cópia da placa entra em `decode`, porque o PyAV a faz dentro da decodificação; 0 em software; emenda de 2026-11-16); evento `decoder` (`{"source": "phone" | "video", "decoder", "reason"}`) quando o caminho muda, com o motivo do fallback.
- `WCAM_HW_DECODE` na tabela de variáveis.
- Troca de formato: só muda se a ADR da §1.4 decidir pela troca imediata; nesse caso o orquestrador emenda o contrato antes do código.

## 4. ADRs

- ADR nova: caminho da decodificação na placa de vídeo, a partir do spike da §1.6, com os números e o fallback.
- ADR nova: troca de formato com o app aberto, com a tabela por app da §1.4.

## Textos

Chaves novas antes do código: o rótulo e os dois valores do decodificador nos detalhes, a etapa nova do `/dev`, e o aviso da troca imediata de formato se a ADR decidir por ela.

## Testes

- Agent: igualdade de bytes entre placa de vídeo e software (só no Windows com placa, marcado para pular sem ela); fallback ao abrir e no meio do fluxo (decodificador falso que falha) sem derrubar a sessão e com PLI enviado; `WCAM_HW_DECODE=off`; igualdade de bytes da tradução de cor contra a v0.9.0; o vídeo da biblioteca trocando de caminho sem preto.
- Web: Vitest no rótulo do decodificador e no limite novo do indicador.
- e2e: segue em software no CI (sem placa de vídeo), com `decoder` `software` no status e o SSIM do CA-2.

## Fora do escopo

- Trocar o codec do celular (ADR 0014 continua).
- Codificação na placa de vídeo para a prévia do console (fica com o app Windows, 1.0.0).
- Linux e macOS.

## Critérios de aceitação

1. Celular em 2160p30, reunião de 30 min no Meet (medida em 15 min por decisão do usuário em 2026-11-18): p95 do processamento por quadro abaixo de 33,3 ms e nenhuma queda do fps entregue abaixo de 25 por mais de 1 s causada pelo PC (as do celular ou da rede ficam explicadas no relatório).
2. CPU do WCam com o celular em 2160p30 e com o `IMG_0641.MOV` em 4K pelo menos 50% menor que a da v0.9.0, medida no mesmo PC e com o mesmo procedimento.
3. Com `WCAM_HW_DECODE=off`, ou com a placa de vídeo falhando, tudo continua funcionando em software, sem queda da sessão.
4. CA-2: quadro da placa de vídeo igual ao de software, byte a byte, no vídeo de referência; SSIM de pelo menos 0,98 no e2e.
5. Causa das quedas de fps da v0.8.0 explicada com números; as do PC corrigidas.
6. Troca de formato com o app aberto imediata, ou ADR com a medição por app justificando por que não.
7. Detalhes e `/dev` mostram o decodificador em uso; indicador de processamento com o limite revisto.
8. Verificação completa do CLAUDE.md e `npm run test:e2e`; `version` 0.10.0 em `agent/pyproject.toml` e `web/package.json`.
