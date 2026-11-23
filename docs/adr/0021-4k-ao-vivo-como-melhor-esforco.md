# 0021. 4K ao vivo como melhor esforço; reunião garantida em 1080p30

Status: Aceita
Data: 2026-11-23
Complementa: ADR 0019 (celular ao vivo no processador)

## Contexto
O CA 1 da spec v0.10.0 pedia, com o celular em 2160p30 numa reunião do Meet, p95 do processamento por quadro abaixo de 33,3 ms e nenhuma queda abaixo de 25 fps por mais de 1 s causada pelo PC. Medido no PC do usuário (i5-8500, 6 núcleos, UHD 630), com o iPhone e o Meet no Chrome, em reuniões de 15 min, duração reduzida por decisão do usuário:

| Reunião | p95 por quadro | fps entregue | segundos abaixo de 25 | quedas do PC |
|---|---|---|---|---|
| 2160p30, 2026-11-22 (I420) | 53,4 ms | 27,5 | 149 | 16 |
| 2160p30, 2026-11-23 (NV12) | 30,5 ms | 28,9 | 82 | 3 |
| 1080p30, 2026-11-23 (NV12) | 11,5 ms | 29,7 | 7 | 0 |

- As quedas que sobram em 4K acontecem com os quadros chegando e a CPU do WCam caindo para 17 a 20%: o Chrome do Meet, recebendo e recodificando 4K, disputa os 6 núcleos, e a decodificação em software do WCam trava por até 0,7 s.
- A decodificação na placa de vídeo para o celular ao vivo foi descartada na ADR 0019, porque a placa integrada é dividida com o app e criava fila.
- O que tiraria esse custo é a imagem na placa de vídeo de ponta a ponta (proposta 2.0.0 do planejamento), fora do escopo desta versão.

Escolha do usuário em 2026-11-22: se o 4K falhasse depois do NV12, o CA 1 passaria a ser medido em 1080p30 e a versão fecharia.

## Decisão
- O CA 1 da v0.10.0 vale em 1080p30: é o formato garantido para reunião neste tipo de PC.
- 2160p30 ao vivo continua oferecido e funciona, como melhor esforço: p95 dentro do orçamento, com travadas curtas e raras quando o app da reunião disputa o processador.
- Sem mudança no padrão do formato: o padrão já é 1080p30 (spec v0.7.0).

## Consequências
- Quem escolhe 4K numa reunião num PC de 6 núcleos pode ver travadas de menos de 1 s algumas vezes em 15 min.
- Garantir o 4K fica para a imagem na placa de vídeo de ponta a ponta (2.0.0) ou para PCs mais fortes, com uma medição nova.
