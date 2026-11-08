# Relatório v0.6.0, sessão vcam

Status: pronto (código, medições, verify e CA 4 no Frame Server)
Branch: `feature/qualidade-vcam`
Spec: `docs/specs/spec-v0.6.0.md` §1; ADRs 0011 e 0012; handoff `docs/handoff-v0.6.0.md`

## O que foi feito

1. **Atributos de cor do tipo de mídia (CA 2).** `CaptureMediaType` concentra a criação do tipo de mídia que antes ficava em `MediaStream`. Além do que já existia (NV12, 1920x1080, 30 fps), ele passa a declarar:
   - `MF_MT_VIDEO_NOMINAL_RANGE` = `MFNominalRange_16_235`;
   - `MF_MT_YUV_MATRIX` = `MFVideoTransferMatrix_BT709` (escolhida pela medição abaixo);
   - `MF_MT_VIDEO_PRIMARIES` = `MFVideoPrimaries_BT709`;
   - `MF_MT_TRANSFER_FUNCTION` = `MFVideoTransFunc_709`.
   Constantes novas no `NativeMethods.txt` do CsWin32. A API C (`WcamCameraStart`, `WcamCameraStop`, `WcamFramePublish`) e o canal de quadros não mudaram.
2. **Testes:** 5 novos em `CaptureMediaTypeTests` (faixa, matriz, primárias, transferência e formato mantido), 32 no total.
3. **Versão:** 0.6.0 em `vcam/Directory.Build.props`.

## Medição da matriz (CA 2)

Método:
- O padrão do probe (`--pattern`) já tem 8 barras 100% de valores YUV conhecidos, codificadas em BT.709 de faixa limitada: branco (235,128,128), amarelo (219,16,138), ciano (188,154,16), verde (173,42,26), magenta (78,214,230), vermelho (63,102,240), azul (32,240,118), preto (16,128,128).
- Duas DLLs publicadas do mesmo código, uma declarando BT.709 (rodada A) e outra BT.601 (rodada B). A variante BT.601 foi só de medição e não está em nenhum commit. Cada uma foi registrada pelo usuário com `scripts/register-vcam.ps1`, e o SHA-256 instalado foi conferido antes de cada rodada.
- Navegador: página local com `getUserMedia` na WCam (1920x1080, 30 fps, `resizeMode` none), quadro desenhado num canvas sRGB e média RGB de 32x32 pixels no centro de cada barra.
- App Câmera do Windows: captura da tela com a janela maximizada e média RGB de 20x20 pixels no centro de cada barra.
- Esperado: decodificação de faixa limitada pela matriz exata, arredondada e limitada a 0 a 255.

RGB lido em cada barra (branco 255,255,255 e preto 0,0,0 em todos os casos):

| Barra | Esperado BT.709 | Esperado BT.601 | App Câmera, A (709) | App Câmera, B (601) | Chrome, A (709) | Chrome, B (601) |
|---|---|---|---|---|---|---|
| amarelo | 254,255,0 | 252,255,10 | 254,255,0 | 254,255,0 | 254,255,12 | 252,255,12 |
| ciano | 0,254,255 | 22,255,253 | 0,254,255 | 0,254,255 | 0,254,252 | 22,255,252 |
| verde | 0,255,1 | 20,255,9 | 0,255,1 | 0,255,1 | 0,255,11 | 20,255,11 |
| magenta | 255,0,254 | 235,0,246 | 255,0,254 | 255,0,254 | 255,0,244 | 235,0,244 |
| vermelho | 255,1,0 | 233,0,2 | 255,1,0 | 255,1,0 | 255,1,3 | 233,0,3 |
| azul | 1,0,255 | 3,0,245 | 1,0,255 | 1,0,255 | 1,0,243 | 3,0,243 |

Leitura:
- **App Câmera:** decodifica BT.709 exato (erro 0 nas 8 barras) nas duas rodadas. Ele ignora o `MF_MT_YUV_MATRIX` declarado e usa 709 em 1080p.
- **Chrome:** segue a matriz declarada. O vermelho do magenta e do ciano muda de 255 e 0 (709) para 235 e 22 (601).
- **Azul cerca de 11 abaixo no Chrome, nas duas rodadas:** o Chromium converte pelo libyuv, que no caminho SIMD x86 limita o coeficiente U→B a 2,0 (128/64). O exato é 2,112 no BT.709 e 2,018 no BT.601. A conta B = 1,164(Y−16) + 2,0(U−128) reproduz o medido nas seis barras coloridas (12, 252, 11, 244, 3, 243), e R e G casam com a matriz declarada. Não é corrigível do lado da câmera. Em imagem real, o erro no azul é de 0,112 × |U−128| níveis: cerca de 2 com U=150, e só 12 em croma saturado. A medição da tarde (abaixo) mostrou que esse desvio só aparece quando o Chrome não usa a GPU; com GPU, o Chrome decodifica BT.709 exato.
- A rodada A foi medida também no Opera (Chromium), com valores idênticos aos do Chrome.

**Decisão: BT.709.** É a única declaração em que o Chrome e o app Câmera decodificam igual, e igual ao esperado (exceto o arredondamento do libyuv acima). Com BT.601 declarado, os dois discordam. Primárias e transferência BT.709 acompanham a matriz e são as do sRGB que as webcams usam.

Consequência para a spec §1 (matriz declarada pelo celular): se um celular declarar BT.601, o app Câmera vai mostrar 709 de qualquer forma. Converter matriz continua fora desta versão, como a spec diz.

## Calibração de cor: modelo do Chrome (spec §1.1, CA 3.1, parte 1)

Ferramenta de desenvolvimento, fora do produto:
- `--patches` no probe publica uma grade 16x9 de patches 120x120 alinhados ao croma. A linha 0 é uma rampa neutra de Y 16 a 235; as linhas 1 a 8 têm 128 combinações de Y (80 e 150) com U e V entre 44 e 212.
- `vcam/tools/Wcam.ColorVerify chrome-model` serve em `localhost:8765` uma página que abre a WCam por `getUserMedia`, faz a média de 5 quadros no centro de cada patch, em canvas `srgb` e `display-p3`, e ajusta por mínimos quadrados um modelo afim YUV→RGB. Entram só os patches sem recorte em sRGB; o `display-p3` é convertido para sRGB antes do ajuste. A saída mostra os coeficientes contra o BT.709 exato e o do libyuv, o resíduo e o ΔE2000 contra o BT.709 exato, e grava o modelo em JSON para a parte 2.
- `vcam/tools/chrome-model-run.mjs` abre o Google Chrome instalado pelo Playwright de `web/node_modules`, com `--use-fake-ui-for-media-stream` (permissão sem clique, dispositivo real). `WCAM_CHROME_ARGS` acrescenta flags.

Medição de 2026-11-06, Google Chrome 156.0.8078.80, coeficientes [offset, Y−16, U−128, V−128], canvas `srgb`, 74 patches sem recorte:

| Canal | BT.709 exato | Chrome com GPU | Chrome sem GPU (`--disable-gpu`) |
|---|---|---|---|
| R | 0, 1,1644, 0, 1,7927 | −0,234, 1,1666, −0,0005, 1,7966 | −0,067, 1,1640, −0,0004, 1,7961 |
| G | 0, 1,1644, −0,2132, −0,5329 | −0,110, 1,1653, −0,2128, −0,5323 | −0,081, 1,1638, −0,2191, −0,5317 |
| B | 0, 1,1644, 2,1124, 0 | −0,014, 1,1643, 2,1130, 0,0004 | −0,482, 1,1669, 1,9981, −0,0012 |
| Resíduo (rms, máx, em códigos) | | 0,29, 0,58 | 0,26, 0,80 |
| ΔE2000 contra o BT.709 exato (média, máx) | | 0,03, 0,08 | 0,45, 1,35 |

- No canvas `display-p3`, os coeficientes são os mesmos com diferença de até 0,003 (U→B 2,110 com GPU e 1,998 sem). O resíduo máximo sobe para cerca de 4 códigos nos patches saturados, pelo arredondamento da conversão para P3.
- **Dois caminhos de decodificação.** Com GPU, o Chrome decodifica BT.709 exato. Sem GPU, ele converte pelo libyuv, com U→B 2,0 em vez de 2,112.
- **O Chrome do usuário estava sem GPU.** As barras de cor medidas no Chrome dele pela manhã (amarelo 254,255,12; azul 1,0,243) se repetem exatamente no Chrome do Playwright com `--disable-gpu`. Sem a flag, saem 709 exato, como no app Câmera. É o mesmo binário, então a diferença está no perfil (aceleração gráfica desligada ou GPU bloqueada); não confirmado no `chrome://gpu` dele.
- O número do CA 3.1 usa o caminho que o Chrome do usuário usa no teste final. Se as barras não puderem ser repetidas no Chrome dele, vale o caminho sem GPU, o pior caso e o que ele mostrou de manhã. O relatório registra os dois.

## Calibração de cor: verificação de ponta a ponta (CA 3.1, parte 2)

`Wcam.ColorVerify verify <pasta do trace> --model gpu=<arquivo> --model software=<arquivo>` lê o trace do agente gravado com `WCAM_COLOR_TRACE_DIR`:
- `color-sample-<n>.json`: a mensagem `color_sample` como chegou, mais `receivedAt`, `calibrationState`, `correlation`, `mirrored`, `colorRange` e `matchedFrame` (Y, U e V do quadro casado, do tamanho da amostra, antes de qualquer tabela).
- `color-calibration.json`: `state`, `deltaE`, `rangeTables` (só faixa) e `appliedTables` (faixa composta com a calibração).

Para cada amostra e cada modelo, o comando aplica as tabelas ao quadro casado (espelhado quando `mirrored`), passa o resultado pelo modelo do Chrome do `colorSpace` da amostra e calcula o ΔE2000 médio por pixel contra a amostra. Isso sai "antes" (`rangeTables`) e "depois" (`appliedTables`), por amostra e na média. Testes: amostra gerada do próprio quadro dá ΔE abaixo de 0,3; o espelho é respeitado; uma correção conhecida dá ΔE baixo depois e alto antes; display-p3 equivale a sRGB; e o JSON do agente é lido.

Trace do teste final de 2026-11-07 (duas sessões, separadas pelo `receivedAt`; o agente publicou ΔE 1,23). ΔE2000 médio, antes e depois da calibração:

| Sessão (amostras válidas) | Chrome com GPU | Chrome sem GPU |
|---|---|---|
| 22:32 (1 a 5) | 2,05 para 1,62 | 2,12 para 1,76 |
| 21:45 a 21:46 (10 a 15) | 2,13 para 1,80 | 2,16 para 1,89 |

- As amostras 6 a 9 ficaram fora: quadros pretos, três delas com correlação abaixo de 0,5. A média das 15 que o comando imprime (1,56 para 1,28) é puxada por elas.
- Cena escura (L* entre 3,5 e 34), onde o ΔE2000 subestima diferenças visíveis.
- Depois da calibração, o brilho casa, mas sobra um desvio de matiz (Δa* cerca de −0,7, Δb* cerca de +0,4), vindo do ganho de saturação de cerca de 1,04.
- Limites do trace, passados à sessão agent: as amostras 1 a 5 de 21:44 foram sobrescritas pela sessão de 22:32 (a numeração recomeça); só existe o `color-calibration.json` de 22:32, então a sessão de 21:45 foi avaliada com as tabelas da outra; o trace guarda amostras de correlação baixa.

## Quadro real do iPhone (item 3 do handoff)

Substituído, por decisão do orquestrador, pela comparação lado a lado feita pelo usuário (`wcam-65bdcb172a11f251`): ΔE2000 de 1,80 entre a WCam no PC e o celular.

## Congelar 3 s e depois preto no Frame Server (CA 4)

Medição de 2026-11-08, sem o usuário, com a câmera liberada pelo orquestrador:
- Agente da raiz (código da integração `feature/qualidade`, 8f72c2d), subido com `WCAM_VIRTUAL_CAMERA=media_foundation`, depois de conferir 8080 e 8443 livres. Câmera nativa ativa, 1920x1080 a 30 fps.
- Cliente aiortc de laboratório no lugar do celular, pelo caminho real: `POST /api/pairing`, `POST /api/sessions` com o token e a oferta, `POST /api/sessions/current/confirm`, sessão `live`. Envia um clipe H.264 1080p30 sintético (ruído que se desloca 4 px por quadro) e, 4 s depois de `live`, para de enviar sem fechar a conexão.
- Leitura da WCam no Google Chrome 156 pelo Playwright (`getUserMedia` 1920x1080 a 30 fps): a cada quadro, `requestVideoFrameCallback`, nível médio e diferença média para o quadro anterior numa redução de 192x108.
- Três sessões seguidas. Tempo medido no Chrome, do último quadro que mudou até o primeiro quadro preto:

| Sessão | Congelado até o preto | Quadros congelados | Diferença máxima entre quadros congelados | Nível no preto |
|---|---|---|---|---|
| 1 | 3,00 s | 89 | 0 | 0 |
| 2 | 3,03 s | 88 | 0 | 0 |
| 3 | 3,03 s | 89 | 0 | 0 |

- Dentro de 3 s com tolerância de 0,2 s nas três. Durante o congelamento, a WCam continua a cerca de 30 fps repetindo o mesmo quadro (diferença 0, nível 129,5 igual ao do vídeo); ao vivo, a diferença média entre quadros era 13. O preto lido é RGB 0,0,0, que é Y=16, UV=128 decodificado em faixa limitada.
- O `virtualCamera.source` do status, lido a cada 0,25 s, acompanha: `phone` até cerca de 0,5 s, `frozen` até cerca de 3 s e `placeholder` a partir de 3,2 s.
- Nenhuma mudança na vcam: o agente republica o último quadro durante os 3 s, como previsto nos achados abaixo.

## Achados para outras versões

- **Instalador da v1.0.0:** o `register-vcam.ps1` só trata a DLL presa pelo FrameServer (reinicia o serviço e copia de novo). Qualquer processo cliente da API C também carrega a DLL instalada e a prende: o probe na medição e, no produto, o agente WCam. Na rodada B, o primeiro registro falhou com `IOException` por causa do probe. O instalador precisa encerrar o WCam antes de copiar a DLL.
- **Build não reprodutível:** duas publicações AOT do mesmo código dão SHA-256 diferente (MVID e carimbo de tempo do PE). Para conferir a DLL instalada, compare com o hash do arquivo publicado, não do código.
- **Congelar 3 s (spec §2):** a media source continua mostrando preto quando não recebe quadro publicado há 1 s. Para congelar, o agente precisa continuar chamando `WcamFramePublish` com o último quadro durante os 3 s. Isso não muda a vcam.

## Verificação

- `dotnet build`: 0 avisos.
- `dotnet test`: 96 de 96 (32 da câmera e 64 da ferramenta de cor e da grade).
- `dotnet publish -r win-x64 -c Release` da DLL: 0 avisos (com o `vswhere` no PATH).
- No Frame Server, com cada DLL registrada pelo usuário e o probe publicando: Chrome e app Câmera a 1920x1080 e 30 fps, barras limpas e contador andando.
- DLL final do commit 903e779: SHA-256 `ab70df1dd112ba2209092bc4c53c55b65bcb5ce064d2c109043bb865ada8414f`. Re-registrada pelo usuário: o hash instalado em `C:\Program Files\WCam` confere, e o `InprocServer32` aponta para ela.
- CA 4 no Frame Server, visto no Chrome: congelado 3,00 s, 3,03 s e 3,03 s até o preto, em três sessões (seção acima).
