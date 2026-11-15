# 0015. Prévia do console por uma segunda conexão WebRTC local

Status: Aceita
Data: 2026-11-12

## Contexto
O console da v0.8.0 mostra uma prévia do que os apps recebem, com espelho, congelamento e o quadro de câmera desligada aplicados (spec v0.8.0 §2.3). O quadro final existe só no agente, em YUV, no formato anunciado, que vai até 3840x2160 a 30 fps. A prévia é para conferir de relance, não para medir qualidade, e não pode pesar na CPU a ponto de prejudicar a câmera virtual.

Opções consideradas:
- **Imagens JPEG periódicas** por HTTP ou SSE: simples, mas codificar JPEG em Python por quadro custa mais que o vídeo, e a taxa útil fica em poucos quadros por segundo.
- **Repassar a faixa do celular** com `MediaRelay`: não mostra o que os apps recebem (sem espelho, congelamento nem quadro de câmera desligada) e ficaria em 4K no console.
- **Segunda conexão WebRTC** entre o console e o agente, só em loopback, com uma faixa que lê o último quadro entregue à câmera e o reduz.

## Decisão
- A prévia é uma segunda `RTCPeerConnection` aiortc, aberta por `POST /api/preview` e fechada por `DELETE /api/preview` ou pela queda do ICE, com candidatos só de loopback (contrato, "Prévia do console").
- A faixa envia o quadro entregue à câmera, reduzido para 960x540 no executor, a no máximo 30 fps. Antes da redução por área, o agente pula um pixel a cada dois em cada plano nos quadros grandes (2160p), o que só afeta a prévia; a regra exata está no relatório do agent.
- Sem prévia aberta, nada é reduzido nem codificado para ela.
- A câmera virtual não muda: a redução vale só para a prévia (CA-2).

## Medição
CPU do processo do agente (`process.cpuPercent`), mediana de 2 min por fase, câmera falsa a 30 fps, Edge headless como console, prévia em 960x540, em 2026-11-12 (relatório `docs/relatorio-v0.8.0-agent.md`):

| Formato | Sem prévia | Com prévia | Custo da prévia |
|---|---|---|---|
| 1080p30 | 1,6% | 4,7% | +3,1 pontos |
| 2160p30, redução direta | 2,1% | 13,3% | +11,2 pontos |
| 2160p30, com pulo de pixels | 2,6% | 9,4% | +6,8 pontos |

- Com a redução direta, o 2160p30 passou do limite de 10 pontos da spec. Com o pulo de pixels ficou abaixo, e a prévia segue a 30 fps em todos os formatos; a queda para 15 fps não foi necessária.
- O processo de teste não decodifica vídeo do celular, então os valores "sem prévia" ficam abaixo do uso real; a diferença entre as fases é o custo da prévia. A CPU do sistema nas fases de 2160p ficou entre 34% e 60% por outros programas do PC.

## Consequências
- O console recebe vídeo comum de WebRTC, com o mesmo código de recepção do navegador e sem formato novo.
- A prévia custa de 3 a 7 pontos de CPU com o console aberto. Desligar a prévia devolve esse custo, e a câmera virtual não é afetada.
- Se um PC mais fraco mostrar a prévia acima de 10 pontos, o passo previsto na spec (15 fps) continua disponível sem mudar o contrato.
