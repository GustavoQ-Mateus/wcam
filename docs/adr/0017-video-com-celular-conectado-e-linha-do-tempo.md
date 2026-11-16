# 0017. Vídeo só com o celular conectado, tocando uma linha do tempo de trechos

Status: Aceita
Data: 2026-11-15
Substitui em parte: ADR 0016 (a parte em que ativar o vídeo encerra a sessão do celular)

## Contexto
Na bateria da spec v0.9.0 (revisão 1), o usuário pediu duas mudanças. Primeiro, por segurança, escolher e usar o vídeo só com o celular conectado: o vídeo substitui a câmera do celular, não a conexão. Segundo, uma linha do tempo de editor, com vários vídeos, cortes e ordem. A ADR 0016 encerrava a sessão ao ativar e tocava um arquivo só.

Opções consideradas para o celular:
- **Encerrar a sessão ao ativar** (ADR 0016): simples, mas voltar à câmera exige novo QR, e qualquer pessoa no PC usa o vídeo sem celular.
- **Manter a sessão com a câmera do celular desligada**: voltar à câmera é imediato e o vídeo só começa com um celular autorizado pelo QR.

Opções para a linha do tempo:
- **Renderizar a edição num arquivo novo** antes de tocar: reprodução igual à de um arquivo só, mas cada corte custa uma recodificação longa.
- **Tocar os trechos direto dos arquivos originais**, abrindo o próximo antes do fim do atual: a edição vale na hora, sem recodificar.

## Decisão
- Envio e ativação do vídeo exigem o celular em `live`. Ativar não encerra a sessão: o celular recebe `video_source` pelo DataChannel, para a faixa da câmera e mostra que o computador está mostrando um vídeo. Voltar à câmera (console, bandeja ou celular) religa a câmera do mesmo celular.
- Se o celular desconectar com o vídeo ativo, o vídeo continua; voltar à câmera do celular passa por um novo QR. O pareamento continua só pelo QR (CA-4).
- A origem de vídeo toca uma linha do tempo de uma faixa, com trechos `{videoId, inSeconds, outSeconds}` direto dos arquivos guardados, abrindo e decodificando o próximo trecho antes do fim do atual. Nada é recodificado em arquivo.
- Vídeos e linha do tempo persistem no SQLite (migration nova); o estado ativo não.
- Continua da ADR 0016: ajuste ao formato anunciado com faixas, ritmo pelo `pts`, CA-2 só para o celular, HDR sem mapeamento de tom, `vcam` sem mudança.

## Consequências
- Voltar à câmera não pede QR, e o vídeo nunca começa sem um celular autorizado.
- O agente precisa tratar a falta de quadros do celular com o vídeo ativo como normal, sem queda nem congelamento.
- Dois decodificadores abertos na troca de trecho aumentam memória e CPU por um instante; com 4K HEVC em software isso pesa até a decodificação na GPU (0.10.0).
- O contrato da revisão 1 (`/api/video-source/file`, `video_source` como motivo de encerramento) sai antes da entrega, sem versão publicada que dependa dele.
