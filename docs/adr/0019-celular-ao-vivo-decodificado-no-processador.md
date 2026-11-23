# 0019. Celular ao vivo decodificado no processador

Status: Aceita
Data: 2026-11-18
Substitui em parte: ADR 0018 (a parte em que o celular ao vivo usa a placa de vídeo com `WCAM_HW_DECODE=auto`)

## Contexto
O spike da ADR 0018 mediu a decodificação com arquivos e com loopback, sem outro app usando a placa de vídeo. Na medição com o celular real (2026-11-18, i5-8500 e UHD 630, iPhone em 2160p30, app Câmera do Windows recebendo a WCam), o resultado mudou:

| 2160p30 ao vivo | v0.9.0 | v0.10.0 com a placa | v0.10.0 no processador |
|---|---|---|---|
| decode por quadro | cerca de 19 ms | cerca de 22 ms, mais cerca de 15 de transfer | mediana 13,3 ms, p95 17,8 ms |
| total p95 | 39 a 67 ms | 19 a 55 ms | cerca de 19 ms |
| fps recebido | cerca de 30 | oscilando de 12 a 40 | mediana 29,9 |
| CPU da máquina | não comparada | cerca de 38% (principal mais filho) | 26,7% |
| atraso visto pelo usuário | maior em 4K | quase 2 s, com quedas | menor |

Com a placa, decode e transfer em série passam de 33,3 ms por quadro, porque a placa integrada é dividida com o app que mostra a câmera. A fila sem limite do receptor do aiortc cresce, e o atraso sobe até segundos. Para o vídeo da biblioteca, que não é tempo real, a placa continua muito melhor: a CPU caiu de 199% para 52% de um núcleo.

Opções consideradas:
- **Celular no processador, placa só para o vídeo da biblioteca.**
- **Medir ao vivo e voltar ao processador quando a placa não couber no tempo do quadro**: melhor em placas fortes, mas com mais código, um motivo novo no contrato e uma decisão difícil de testar.
- **Placa no celular só até 1080p**: regra fixa calibrada num PC só.
- **Sobrepor decode e transfer no processo filho**: soma um quadro de atraso, a cópia ainda segura o GIL do filho e disputa memória com o app; ganho incerto.

Escolha do usuário em 2026-11-18: celular no processador.

## Decisão
- Com `WCAM_HW_DECODE=auto`, o celular ao vivo é decodificado no processador, no processo do agente, e o vídeo da biblioteca na placa de vídeo pelo processo filho da ADR 0018.
- `WCAM_HW_DECODE=on` força a placa também para o celular, para medição e para PCs com placa dedicada. `off` força o processador nos dois.
- Limite de atraso em qualquer caminho: se o quadro do celular ficar mais de 200 ms atrás do relógio, o decodificador descarta até o próximo quadro-chave e pede um ao celular.
- Continua da ADR 0018: processo filho, fallback, encaixe pela troca de `get_decoder`, CPU somando os filhos, Main 10 em software.

## Consequências
- O atraso do celular ao vivo fica no tempo de processamento, e a fila não cresce.
- O ganho de CPU com o celular vem da tradução de cor (§1.2 da spec v0.10.0), não da decodificação.
- O caminho da placa para o celular continua no código e nos testes, ligado só por `on`. Uma versão futura (app Windows em C#, ou a imagem na placa de ponta a ponta) pode reavaliar.
