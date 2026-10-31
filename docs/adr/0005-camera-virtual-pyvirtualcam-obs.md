# 0005. Câmera virtual via pyvirtualcam sobre OBS Virtual Camera na v1

Status: Aceita
Data: 2026-10-31

## Contexto
Meet, Teams e Zoom só leem câmeras do sistema. Criar um driver de câmera próprio no Windows exige uma media source Media Foundation em C++ (`MFCreateVirtualCamera`, Windows 11). O pyvirtualcam escreve no driver do OBS Virtual Camera, que é DirectShow.

## Decisão
Na v1, a câmera virtual é o driver do OBS Virtual Camera, acessado pelo pyvirtualcam, atrás do `Protocol` `VirtualCameraSink`. O OBS precisa estar instalado; não precisa estar aberto. O agente verifica o driver ao iniciar e explica o que falta.

## Consequências
- O MVP não depende de código nativo próprio.
- Apps que só leem Media Foundation podem não enxergar a câmera. A tabela do CA-1 é verificada na v0.4.0; se algum app dela falhar, a câmera nativa Media Foundation entra antes da v1.0.0, em ADR nova que substitui esta.
- O pipeline é testável sem driver, com um sink falso.
