# 0020. Troca de formato continua pendente até o app reabrir a câmera

Status: Aceita
Data: 2026-11-22
Mantém: spec v0.7.0 §1.3 (formato pendente até o app reabrir a câmera)

## Contexto
A spec v0.10.0 §1.4 pediu um spike: reiniciar a câmera virtual no formato novo com o app aberto, e trocar na hora se a maioria dos apps voltasse sozinha em até 3 s. Medido em 2026-11-22 no PC do usuário, com a câmera instalada (DLL nativa), um padrão de teste e uma troca a cada 5 s, alternando 1080p30 e 2160p30, duas idas e duas voltas por app. "Voltou" é o tempo até a contagem de apps da DLL ficar acima de 0; "0 s" quer dizer que o app nunca soltou a câmera.

| App | Para 2160p30 | Para 1080p30 | O que o usuário viu |
|---|---|---|---|
| Meet (Chrome) | 0 s e 0 s | não voltou em 20 s; 5,6 s | câmera indisponível depois de alguns segundos |
| Teams | 0 s e 0 s | não voltou em 20 s; 6,0 s | não pareceu cair (provavelmente mantém o último quadro na tela) |
| App Câmera | 0 s e 0 s | 5,7 s; 0 s | câmera indisponível |

- O reinício da câmera leva de 0,1 a 0,6 s; uma vez em cada app passou de 5 s, esperando o app soltar a câmera.
- Ir para um formato maior não derruba o app, mas a contagem não prova que ele passou a mostrar o formato novo.
- Voltar para um formato menor faz os três apps perderem a câmera. Meet e app Câmera mostram "indisponível"; o Teams esconde a perda, mas fica sem quadros novos.
- Discord, Zoom e OBS ficaram fora da medição por decisão do usuário (sessão reduzida).

## Decisão
- A troca com o app aberto não passa a ser imediata. O formato escolhido continua pendente até o app fechar e reabrir a câmera, como na spec v0.7.0 §1.3, e o console continua avisando isso.
- O `vcam` não muda.

## Consequências
- Nenhum app perde a câmera no meio de uma reunião por causa de uma troca de formato.
- O usuário continua precisando reabrir a câmera no app para o formato novo valer.
- Uma versão futura pode reavaliar com Discord, Zoom e OBS, ou com uma mudança na câmera nativa que anuncie vários formatos ao mesmo tempo.
