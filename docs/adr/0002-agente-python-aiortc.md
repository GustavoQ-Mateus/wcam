# 0002. Agente em Python com aiortc

Status: Aceita
Data: 2026-10-31

## Contexto
O agente precisa receber vídeo WebRTC, decodificar os quadros e escrevê-los numa câmera virtual do sistema. Foram avaliados Python, Go e .NET. Sinalização e HTTP são simples nos três. A parte difícil é o caminho do quadro decodificado até a câmera virtual.

## Decisão
Python 3.13 com uv. WebRTC com aiortc, decodificação com PyAV, câmera virtual com pyvirtualcam, HTTP com FastAPI e uvicorn.

## Consequências
- O caminho WebRTC, quadro, câmera virtual existe pronto e é multiplataforma (Windows, Linux, macOS).
- Go exigiria cgo com FFmpeg e DirectShow ou Media Foundation; .NET exigiria COM e wrapper de FFmpeg. Ficam descartados.
- Desempenho por quadro exige cuidado: trabalho pesado fora do event loop e nenhuma cópia ou conversão de cor desnecessária (CA-2).
- Tipagem estrita com pyright compensa a falta de compilador.
