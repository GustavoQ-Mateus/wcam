# 0013. Formato escolhido pelo usuário no canal de quadros

Status: Aceita (2026-11-10, com o resultado do spike `vcam-format`)
Data: 2026-11-10
Refina: ADR 0012 (o formato fixo 1920x1080 do canal; o resto da 0012 continua valendo)

## Contexto
A câmera WCam anuncia um formato só, 1920x1080 a 30 fps, fixo no canal `WCamFrames`, na API C e na media source. A spec v0.7.0 deixa o usuário escolher resolução e fps (de 1280x720 a 3840x2160, 30 ou 60 fps), e o CA-2 proíbe redimensionar em paisagem. O usuário decidiu em 2026-11-10 que a escolha é dele, no seletor, e que a câmera anuncia só o formato escolhido, em vez de anunciar vários e deixar o app escolher.

## Decisão
- O cabeçalho do canal ganha largura, altura e fps do formato atual. As três posições NV12 têm tamanho para o maior formato (3840x2160).
- A API C ganha `WcamFormatSet(width, height, fps)`, chamada pelo agente quando o usuário escolhe um formato. `WcamFramePublish` aceita só quadros do formato atual.
- A media source anuncia um tipo de mídia só. O Frame Server cria a media source quando a câmera virtual inicia, não quando o app abre, e guarda os tipos dessa criação. Por isso o formato anunciado é o do último início da câmera virtual, e mudar de formato exige parar e iniciar a câmera virtual (`IMFVirtualCamera`) no formato novo. Os quadros de espera e de preto saem nesse formato.
- O formato novo vale na próxima abertura. Com `WcamFormatSet`, a DLL grava o formato e, se nenhum processo estiver recebendo vídeo da WCam (monitor de atividade de sensores do Media Foundation, `streaming` verdadeiro), para e inicia a câmera virtual no formato novo, o que leva cerca de 5 s. Se algum app estiver recebendo vídeo, a troca fica pendente (`videoFormat.pending`) até o último parar, e o agente mantém o celular no formato antigo nesse intervalo.
- A troca imediata pelo evento `MEStreamFormatChanged` foi descartada: o Chrome encerra a faixa cerca de 0,3 s depois da troca, e o app Câmera entra num laço de parar e reiniciar o stream.

## Consequências
- O canal passa de cerca de 9 MB para cerca de 37 MB de memória compartilhada.
- A media source continua só leitura no canal (ADR 0012); nenhum caminho de escrita do Frame Server para o agente é criado.
- Um app aberto num formato nunca recebe quadro de outro tamanho.
- Evidência do spike (2026-11-10, DLL `A9812F81...5494`): com a câmera virtual reiniciada em cada formato, o Chrome recebeu 1280x720 a 30 e 60 fps, 1920x1080, 2560x1440 e 3840x2160 a 30 fps, sem quadro de tamanho errado; a DLL entregou 30,0 e 60,0 quadros/s. Mudar o canal sem reiniciar a câmera deu preto no tamanho antigo. O monitor de sensores listou a WCam com o pid de cada app e o estado de `streaming`.
- Pendente de verificação com o usuário: Teams e OBS, inclusive app que segura a câmera sem receber vídeo (Teams) durante o reinício da câmera virtual.
