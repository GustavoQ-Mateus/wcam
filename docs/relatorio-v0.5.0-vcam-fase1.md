# Relatório v0.5.0 fase 1, sessão vcam

Status: Concluída (validada pelo usuário em 2026-11-02)
Branch: `feature/camera-nativa-vcam`
Spec: `docs/specs/spec-v0.5.0.md`

## O que foi feito

- Solução `vcam/Wcam.VirtualCamera.sln` com a DLL (`PublishAot`), o probe (Native AOT) e os testes xUnit.
- Interfaces de Media Foundation e funções Win32 pelo CsWin32 0.3.367 com `useComSourceGenerators` (`CsWin32RunAsBuildTask`): todas saem como `[GeneratedComInterface]`, e as classes da DLL usam `[GeneratedComClass]`. `PreserveSig` só em `IClassFactory`, `IMFActivate.ActivateObject`, `IMFGetService` e `IKsControl`.
- Media source:
  - `IMFActivate`, que delega `IMFAttributes` a um armazenamento criado por `MFCreateAttributes`;
  - `IMFMediaSourceEx` + `IMFGetService` + `IKsControl`;
  - `IMFMediaStream2` + `IKsControl`.
- Padrão de teste: NV12 1920x1080 a 30 fps, com barras BT.709, um bloco em movimento e um contador de quadros.
- Ritmo: `RequestSample` só enfileira o pedido. Uma thread com timer de alta resolução entrega uma amostra a cada 1/30 s, com o tempo da amostra dado por `MFGetSystemTime`. Um contador loga, a cada 10 s, os quadros entregues, os pedidos recebidos, os ticks ociosos e o tempo por amostra.
- Exports:
  - `DllGetClassObject`;
  - `DllCanUnloadNow`, que responde sempre `S_FALSE`, porque o runtime Native AOT não descarrega;
  - `DllRegisterServer` e `DllUnregisterServer`;
  - `WcamCameraStart` e `WcamCameraStop`.
- Registro COM: CLSID `{F2F06D1E-FA8A-4930-83F6-D85D4E2190C3}`, `ThreadingModel` `Both`.
- Log em `OutputDebugString` e em `%ProgramData%\WCam\logs\vcam.log`.
- Scripts `scripts/register-vcam.ps1` e `scripts/unregister-vcam.ps1`. A DLL é copiada para `%ProgramFiles%\WCam`, e as ACLs para `LOCAL SERVICE` usam o SID, porque o nome da conta muda conforme o idioma do Windows.
- Probe: inicia a câmera e espera Enter. Com `--write file|section`, publica um degradê colorido em movimento no canal escolhido.

## Verificação

- `dotnet build`: 0 avisos.
- `dotnet test`: 14 de 14. Cobrem o padrão de teste, o seqlock do canal (leitura durante a escrita, cabeçalho inválido, bytes 0, 16, 128, 235 e 255 intactos) e a leitura do arquivo mapeado por outro handle.
- `dotnet publish -r win-x64 -c Release` da DLL e do probe: 0 avisos de AOT e de trimming. A DLL publicada tem 2,4 MB, é nativa, sem cabeçalho CLR, e exporta as seis funções (conferido com `dumpbin /exports`).
- Teste no próprio processo, sem registro: a DLL publicada é carregada, e `DllGetClassObject` + `IClassFactory` + `IMFActivate` ativam a media source. O `IMFSourceReader` leu 90 quadros NV12 1920x1080 de 3.110.400 bytes em 3,00 s.

## Resultado nos apps

Registro em 2026-11-02, pelo script de administrador, com o usuário autorizando pelo UAC. O probe rodou como usuário comum.

| Consumidor | Resultado | Evidência |
|---|---|---|
| Frame Server | A DLL carrega no serviço | Log no `svchost` do serviço `FrameServer` (`NT AUTHORITY\LocalService`). Contador do stream: 30,0 fps entregues, 30,0 pedidos/s, 0 ticks ociosos, 0,8 a 1,8 ms por amostra |
| Lista de câmeras do Media Foundation | Aparece | `MFEnumDeviceSources`: "WCam (Câmera Virtual do Windows)", link `\\?\swd#vcamdevapi#...` |
| Chrome (headless, teste da sessão) | Funciona | `getSettings` 1920x1080, 30 fps, `resizeMode` `none`; 29,9 fps medidos por `requestVideoFrameCallback` em 10 s; as 8 barras em RGB 255,255,255 / 254,255,0 / 0,254,255 / 0,255,1 / 255,0,254 / 255,1,0 / 1,0,255 / 0,0,0 |
| App Câmera do Windows (usuário) | Funciona | Aparece e mostra o padrão, com o contador rodando |
| Novo Teams, app (usuário) | Funciona | Aparece como "WCam (Câmera Virtual do Windows)" e mostra o padrão (contador 000223, espelhado pela opção do Teams). Foi o caso que motivou a v0.5.0 |
| Google Meet no navegador (usuário) | Funciona | Aparece e mostra o padrão |
| Opera (usuário) | Funciona | Aparece e mostra o padrão. Na v0.4.0, com o OBS, não funcionava |
| A câmera some ao encerrar | Verificado | Depois de `WcamCameraStop`, `MFEnumDeviceSources` não lista mais a câmera; o log mostra "media source shut down" e "virtual camera stopped" |

Observações:
- O Windows acrescenta " (Câmera Virtual do Windows)" ao nome "WCam". Os textos do console e do terminal precisam considerar isso.
- Quando `MFCreateVirtualCamera` valida a source no processo de quem chama, a DLL tenta criar `Global\WCamFrames` e recebe acesso negado. Fica logado como erro, sem efeito, porque só a instância do serviço precisa da seção. Na fase 2, a seção é criada só no processo do serviço, e essa tentativa sai do log de erro.
- Um cliente de teste em .NET lendo pelo Frame Server parou depois de cerca de 19 quadros, enquanto a DLL seguia entregando 30 fps. O problema é do cliente de teste (cache de wrappers COM com amostras recicladas), não da câmera: Chrome, Teams, Meet, Opera e o app Câmera funcionaram.

### Vários consumidores ao mesmo tempo

Achado do usuário: com o app Câmera aberto, a prévia do Teams ficou preta, e só funcionou depois de fechar o app Câmera.

Diagnóstico pelo `vcam.log` (serviço `FrameServer`, pid 26992):
- Uma única media source é criada e reaproveitada por todos os apps. Cada app novo provoca um `Start` na mesma source (14:07:21, 14:09:39, 14:11:17), às vezes dois seguidos, sem erro.
- Com o segundo app aberto, a source continua recebendo 30 pedidos/s e entregando 30,0 fps. Quem distribui os quadros entre os apps é o Frame Server.
- O stream declara `MF_DEVICESTREAM_FRAMESERVER_SHARED` = 1.

Resultado: com a opção do Windows 11 "Permitir que vários aplicativos usem a câmera ao mesmo tempo" ligada para a WCam (Configurações > Bluetooth e dispositivos > Câmeras), o Meet e o Teams mostraram a câmera juntos. Não precisa de código. Decisão do orquestrador: nada de código para vários consumidores. Fica para o instalador da v1.0.0 avaliar se a opção pode ser ligada por configuração.

Lacuna de log: há intervalos sem entrega sem chamada ao `Stop` da source (por exemplo, de 14:10:01 a 14:11:17), provavelmente via `IMFMediaStream2.SetStreamState`, que hoje não loga. A linha de log está aprovada para a fase 2.

## Transporte de quadros

### O que foi testado

As duas opções usam o mesmo formato: cabeçalho de 64 bytes (magic, versão, largura, altura, fourcc NV12, número de posições, índice do quadro, timestamp e sequência de cada posição) mais três posições NV12 rotativas, com seqlock por posição.
- (a) Arquivo mapeado `%ProgramData%\WCam\frames.bin`, criado pelo probe, lido pela media source.
- (b) Seção nomeada `Global\WCamFrames`, criada pela media source com SDDL `D:(A;;GA;;;SY)(A;;GA;;;LS)(A;;GA;;;BA)(A;;GRGW;;;IU)` e aberta pelo probe para escrita.

Evidência do `vcam.log` (media source no `FrameServer`, pid 26992; probe como usuário comum):

```
14:24:11.79 pid=25424 virtual camera started                         (probe --write file)
14:24:50.74 pid=26992 opened mapped file C:\ProgramData\WCam\frames.bin
14:24:50.75 pid=26992 frame source changed from test pattern to mapped file at frame 0
14:25:17.44 pid=25424 virtual camera stopped
14:25:19.15 pid=26992 created global section Global\WCamFrames      (probe --write section)
14:25:19.21 pid=24564 virtual camera started
14:25:24.59 pid=26992 frame source changed from test pattern to global section at frame 0
14:26:43.88 pid=24564 virtual camera stopped
```

Resultado do usuário: nos dois casos o probe publicou (mais de 900 quadros com `--write file`) e o Teams trocou do padrão para o degradê do probe. Conclusão: as duas opções atravessam processo, sessão e conta (usuário na sessão do console, `LOCAL SERVICE` na sessão 0).

Medição extra da sessão: escrita no disco C: em 25 s com o probe publicando por `--write file`. Média de 2,1 MB/s, contra 0,7 MB/s de base, com picos de 31 MB/s, porque o Windows grava no disco, periodicamente, as páginas modificadas do arquivo mapeado. A seção (b) vive no arquivo de paginação e não gera essa escrita.

### Comparação

| Critério | (a) Arquivo mapeado | (b) Seção `Global\` criada pela media source |
|---|---|---|
| Restringir a escrita ao SID do usuário do WCam | O agente cria o arquivo com DACL própria (o usuário escreve, `LOCAL SERVICE` só lê). Para outro usuário da máquina não ocupar o nome antes, o nome precisa ser por usuário, e a media source precisa saber qual ler. | A media source cria a seção com DACL que dá escrita só ao SID do dono da câmera, e não a `INTERACTIVE`. Nenhum outro usuário consegue criar o nome antes: criar em `Global\` exige `SeCreateGlobalPrivilege`, que usuário comum não tem (confirmado: o processo do probe recebeu acesso negado ao tentar). |
| Caminho confiável para o SID chegar à media source | Necessário também, para escolher o arquivo. | Necessário. Proposta para verificar na fase 2: o agente grava o próprio SID no dispositivo da câmera com `IMFVirtualCamera.AddRegistryEntry` (ou `AddProperty`) antes de `Start`, e a media source lê esse valor da chave do dispositivo. Só o processo que criou a câmera, com acesso `CurrentUser`, consegue escrever ali. Falta confirmar que a source acha a própria chave de dispositivo a partir dos atributos do activate. |
| Quem cria e quando | O agente, quando quiser, inclusive antes de qualquer app abrir a câmera. | A media source, na ativação. Pelo log, o Frame Server ativa a source dentro do `Start` da câmera: a seção existe às 14:25:19.15, antes do retorno de `WcamCameraStart` às 14:25:19.21. O agente abre a seção logo depois do `Start`, sem esperar um app. |
| Latência e cópias por quadro | Duas cópias: agente para a posição, e posição para o buffer de Media Foundation. Latência de até um intervalo de quadro (33 ms), pelo ritmo da source. | Igual: duas cópias e até 33 ms. A conversão I420 para NV12 do agente escreve direto na posição, então não há cópia extra. Montar a amostra mediu 0,8 a 1,8 ms. |
| Custo extra | Cerca de 1,4 MB/s de escrita no disco (medido), uns 5 GB por hora de uso. | Nenhum disco; 9,3 MB no arquivo de paginação. |
| Limpeza ao encerrar | O arquivo fica no disco e guarda o último quadro, ou seja, a última imagem da câmera do usuário, até ser apagado. Exige apagar e lidar com o leitor ainda aberto. | A seção some quando o último handle fecha (agente e source). Nada fica no disco. Se o Frame Server recriar a source enquanto o agente segura o handle, a nova source reabre a mesma seção pelo nome. |
| Instalador da v1.0.0 | Criar `%ProgramData%\WCam` com ACL que permita a cada usuário criar o próprio arquivo sem acessar o dos outros. | Nada para o transporte. Continua só o diretório de logs com escrita para `LOCAL SERVICE`, que é necessário de qualquer forma. |

### Recomendação

Opção (b), a seção `Global\` criada pela media source, com duas mudanças para o produto:
1. DACL da seção: `SY` e `LS` com acesso total, e leitura e escrita só para o SID do usuário que iniciou o WCam, no lugar de `INTERACTIVE`. Se a source não obtiver esse SID por um caminho confiável, ela não cria a seção e entrega preto. Nunca cai para `INTERACTIVE`.
2. Caminho do SID: verificar no começo da fase 2 a proposta de `AddRegistryEntry`/`AddProperty` descrita acima. Se não for viável, trago alternativas antes de implementar.

Motivos: mesma latência e mesmas cópias que (a), sem escrita contínua no disco, sem imagem do usuário deixada no disco, sem risco de outro usuário ocupar o nome antes, limpeza automática e nada novo no instalador. O canal existe assim que `WcamCameraStart` retorna, então o agente pode publicar antes de algum app abrir a câmera.

## Riscos do Native AOT encontrados

Nenhum bloqueio: COM gerado por código, exports `[UnmanagedCallersOnly]` e a DLL dentro do Frame Server funcionaram. Pontos encontrados:
- MSVC e `vswhere`: o `vcvarsall.bat` chama `vswhere.exe` pelo PATH, e a pasta `C:\Program Files (x86)\Microsoft Visual Studio\Installer` não está no PATH desta máquina. A mensagem de erro vai parar no caminho do linker que o ILCompiler monta, e o link falha com código 123. Primeiro pareceu culpa da instalação Insiders (o ILCompiler escolhe a instalação mais nova, inclusive prerelease), mas o erro continuou depois que o usuário a removeu. Contorno: chamar o `vcvarsall.bat amd64` da Community e publicar com `/p:IlcUseEnvironmentalTools=true`. Correção definitiva: pôr a pasta do Installer no PATH. No CI isso não deve acontecer.
- `SelfContained=false` no `Directory.Build.props` quebra o publish AOT (NETSDK1102). Foi removido.
- É preciso `[assembly: DisableRuntimeMarshalling]` para o código do CsWin32 com geradores de COM compilar.
- É preciso o TFM `net10.0-windows10.0.22000.0` para as APIs de câmera virtual (e `IMFMediaSourceEx`) passarem pelo analisador de plataforma (CA1416).
- Objetos nativos criados a cada quadro (amostra e buffer) são liberados com `ComObject.FinalRelease()`. Sem isso, 3 MB por quadro ficariam esperando o GC. `FinalRelease` só vale para objetos criados pela própria DLL: o cliente de teste mostrou que objetos reciclados pelo Frame Server não combinam com o cache de wrappers.
- `DllCanUnloadNow` responde sempre `S_FALSE`: o runtime Native AOT não pode ser descarregado do processo do serviço. Para trocar a DLL é preciso reiniciar o FrameServer (o script de registro faz isso quando a cópia falha).
- Depuração: não há console no Frame Server. O log em arquivo bastou para todos os diagnósticos desta fase. Exceções viram `HRESULT` nos stubs gerados, e a thread de quadros captura tudo, porque uma exceção ali derrubaria o serviço de câmera.
- Dois runtimes Native AOT no mesmo processo (o probe AOT carregando a DLL AOT) funcionaram.

## Perguntas

1. O caminho confiável do SID (`AddRegistryEntry`/`AddProperty`) entra como primeiro item da fase 2, com uma prova antes da implementação?
2. Os textos que mostram o nome da câmera devem usar "WCam" e explicar que os apps mostram "WCam (Câmera Virtual do Windows)"?
