# 0011. Câmera virtual nativa Media Foundation em C# Native AOT

Status: Aceita
Data: 2026-11-02
Substitui: ADR 0005

## Contexto
Na v0.4.0, o driver do OBS Virtual Camera (DirectShow) funcionou em apps de navegador, mas não apareceu no novo Microsoft Teams (app empacotado) nem funcionou no Opera, como a ADR 0005 previa. O Teams é o app mais usado pelo usuário. A fase 1 da v0.5.0 provou, na máquina do usuário, uma câmera virtual própria criada com `MFCreateVirtualCamera`.

## Decisão
- A câmera virtual do produto é uma media source Media Foundation própria, numa DLL nativa escrita em C# e publicada com .NET 10 Native AOT (pasta `vcam/`). COM só por `[GeneratedComInterface]`/`[GeneratedComClass]`; Win32 e Media Foundation pelo CsWin32.
- A câmera é criada com tipo `SoftwareCameraSource`, nome "WCam", tempo de vida `Session` e acesso `CurrentUser`: ela existe só enquanto o WCam está aberto. Os apps a mostram como "WCam (Câmera Virtual do Windows)".
- Transporte de quadros entre o agente (sessão do usuário) e a media source (Frame Server, `LOCAL SERVICE`, sessão 0): seção de memória nomeada em `Global\`, criada pela media source, com DACL que dá escrita só ao SID do usuário que iniciou o WCam. Formato: cabeçalho e três posições NV12 1920x1080 rotativas com seqlock.
- O SID do dono chega à media source por um caminho confiável definido no início da fase 2 (proposta: entrada de registro ou propriedade do dispositivo gravada pelo agente antes do `Start`). Sem SID, a media source não cria a seção e entrega preto.
- O agente controla a câmera e publica quadros por uma API C exportada pela mesma DLL (`WcamCameraStart`, `WcamCameraStop`, `WcamFramePublish`), chamada por `ctypes`.
- O driver do OBS continua como fallback quando a DLL não está registrada ou o Windows é anterior ao build 22000.

## Evidência (fase 1, 2026-11-02)
- "WCam" com padrão de teste no app Câmera, no novo Teams, no Meet e no Opera; Chrome mediu 1920x1080 a 29,9 fps, sem redimensionar.
- Seção `Global\` e arquivo mapeado funcionaram; a seção foi escolhida por segurança (escrita só do dono, nome que usuário comum não consegue ocupar antes), por existir desde o `Start` e por não escrever no disco (o arquivo mapeado gravava cerca de 5 GB por hora e deixava o último quadro em disco).
- Vários apps ao mesmo tempo funcionam com a opção do Windows "Permitir que vários aplicativos usem a câmera ao mesmo tempo", sem código.

## Consequências
- O OBS deixa de ser necessário quando a DLL está registrada.
- Registrar a DLL exige administrador: em desenvolvimento por `scripts/register-vcam.ps1`, no produto pelo instalador da v1.0.0.
- A DLL não descarrega do Frame Server: atualizar exige reiniciar o serviço `FrameServer`.
- O CI compila e testa a DLL, mas não consegue testar a câmera; a verificação real é sempre na máquina do usuário.
- Build Native AOT exige o MSVC do Visual Studio Build Tools e o `vswhere` acessível.
