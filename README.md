# WCam

Transforma a câmera do celular em webcam do PC, sem fio. O PC roda um agente local; o celular abre uma página pelo QR code, na mesma rede Wi-Fi, e envia o vídeo por WebRTC para uma câmera virtual que Meet, Teams, Zoom e qualquer app enxergam como webcam comum.

## Estado

Em desenvolvimento. A versão atual sobe o agente com HTTPS na rede local e serve a página do celular; ainda não transmite vídeo. O planejamento está em [docs/planejamento.md](docs/planejamento.md).

## Desenvolvimento

Requisitos: Python 3.13 com [uv](https://docs.astral.sh/uv/), Node 24 e Docker.

Agente nativo (Windows), necessário para testar com o celular:

```
cd web && npm ci && npm run build
cd ../agent && uv sync && uv run wcam
```

O terminal mostra o endereço do console, o endereço da página do celular, a impressão digital do certificado e o QR code. O celular precisa estar na mesma rede Wi-Fi.

Ambiente Docker (agente headless, web em modo dev e testes e2e):

```
docker compose up
docker compose --profile e2e up --build --exit-code-from e2e
```

## Licença

[MIT](LICENSE)
