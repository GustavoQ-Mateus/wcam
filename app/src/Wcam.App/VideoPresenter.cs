using System.Runtime.InteropServices;
using Windows.Win32;
using Windows.Win32.Foundation;
using Windows.Win32.Graphics.Direct3D;
using Windows.Win32.Graphics.Direct3D11;
using Windows.Win32.Graphics.Dxgi;
using Windows.Win32.Graphics.Dxgi.Common;
using Windows.Win32.System.Com;

namespace Wcam.App;

internal sealed unsafe class VideoPresenter : IDisposable
{
    private const uint BufferCount = 2;
    private const uint FramesPerSecond = 30;

    private readonly ID3D11Device* _device;
    private readonly ID3D11DeviceContext* _context;
    private readonly ID3D11VideoDevice* _videoDevice;
    private readonly ID3D11VideoContext1* _videoContext;
    private readonly IDXGISwapChain1* _swapChain;
    private ID3D11VideoProcessorEnumerator* _enumerator;
    private ID3D11VideoProcessor* _processor;
    private ID3D11Texture2D* _texture;
    private ID3D11VideoProcessorInputView* _inputView;
    private ID3D11VideoProcessorOutputView* _outputView;
    private int _frameWidth;
    private int _frameHeight;
    private int _outputWidth;
    private int _outputHeight;

    public VideoPresenter(HWND window, int outputWidth, int outputHeight)
    {
        ID3D11Device* device;
        ID3D11DeviceContext* context;
        HRESULT created = PInvoke.D3D11CreateDevice(
            null,
            D3D_DRIVER_TYPE.D3D_DRIVER_TYPE_HARDWARE,
            HMODULE.Null,
            D3D11_CREATE_DEVICE_FLAG.D3D11_CREATE_DEVICE_BGRA_SUPPORT | D3D11_CREATE_DEVICE_FLAG.D3D11_CREATE_DEVICE_VIDEO_SUPPORT,
            null,
            0,
            PInvoke.D3D11_SDK_VERSION,
            &device,
            null,
            &context);
        Marshal.ThrowExceptionForHR(created.Value);
        _device = device;
        _context = context;
        _videoDevice = Query<ID3D11VideoDevice>((IUnknown*)device, ID3D11VideoDevice.IID_Guid);
        _videoContext = Query<ID3D11VideoContext1>((IUnknown*)context, ID3D11VideoContext1.IID_Guid);
        _swapChain = CreateSwapChain(device, window, outputWidth, outputHeight);
        _outputWidth = outputWidth;
        _outputHeight = outputHeight;
    }

    public void Resize(int width, int height)
    {
        if (width <= 0 || height <= 0 || (width == _outputWidth && height == _outputHeight))
        {
            return;
        }
        Release(ref _outputView);
        _swapChain->ResizeBuffers(BufferCount, (uint)width, (uint)height, DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_UNORM, 0);
        _outputWidth = width;
        _outputHeight = height;
        ReleaseProcessor();
    }

    public void Present(ReadOnlySpan<byte> nv12, int width, int height)
    {
        EnsureProcessor(width, height);
        fixed (byte* frame = nv12)
        {
            _context->UpdateSubresource((ID3D11Resource*)_texture, 0, null, frame, (uint)width, 0);
        }
        Blit(true);
    }

    public void PresentBlack()
    {
        if (_processor == null)
        {
            EnsureProcessor(_outputWidth & ~1, _outputHeight & ~1);
        }
        Blit(false);
    }

    public void Dispose()
    {
        ReleaseProcessor();
        Release(ref _outputView);
        _swapChain->Release();
        _videoContext->Release();
        _videoDevice->Release();
        _context->Release();
        _device->Release();
    }

    private void Blit(bool withFrame)
    {
        ID3D11VideoProcessorOutputView* output = OutputView();
        var stream = new D3D11_VIDEO_PROCESSOR_STREAM { Enable = withFrame, pInputSurface = _inputView };
        _videoContext->VideoProcessorSetOutputBackgroundColor(_processor, false, new D3D11_VIDEO_COLOR());
        _videoContext->VideoProcessorBlt(_processor, output, 0, 1, &stream);
        _swapChain->Present(1, 0);
    }

    private void EnsureProcessor(int width, int height)
    {
        if (_processor != null && width == _frameWidth && height == _frameHeight)
        {
            return;
        }
        ReleaseProcessor();
        var content = new D3D11_VIDEO_PROCESSOR_CONTENT_DESC
        {
            InputFrameFormat = D3D11_VIDEO_FRAME_FORMAT.D3D11_VIDEO_FRAME_FORMAT_PROGRESSIVE,
            InputWidth = (uint)width,
            InputHeight = (uint)height,
            OutputWidth = (uint)_outputWidth,
            OutputHeight = (uint)_outputHeight,
            InputFrameRate = new DXGI_RATIONAL { Numerator = FramesPerSecond, Denominator = 1 },
            OutputFrameRate = new DXGI_RATIONAL { Numerator = FramesPerSecond, Denominator = 1 },
            Usage = D3D11_VIDEO_USAGE.D3D11_VIDEO_USAGE_PLAYBACK_NORMAL,
        };
        ID3D11VideoProcessorEnumerator* enumerator;
        _videoDevice->CreateVideoProcessorEnumerator(&content, &enumerator);
        _enumerator = enumerator;
        ID3D11VideoProcessor* processor;
        _videoDevice->CreateVideoProcessor(enumerator, 0, &processor);
        _processor = processor;
        _texture = CreateTexture(width, height);
        var inputDescription = new D3D11_VIDEO_PROCESSOR_INPUT_VIEW_DESC
        {
            ViewDimension = D3D11_VPIV_DIMENSION.D3D11_VPIV_DIMENSION_TEXTURE2D,
        };
        ID3D11VideoProcessorInputView* inputView;
        _videoDevice->CreateVideoProcessorInputView((ID3D11Resource*)_texture, enumerator, &inputDescription, &inputView);
        _inputView = inputView;
        ConfigureColor(processor);
        RECT target = Letterbox(width, height);
        _videoContext->VideoProcessorSetStreamDestRect(processor, 0, true, &target);
        _frameWidth = width;
        _frameHeight = height;
    }

    private void ConfigureColor(ID3D11VideoProcessor* processor)
    {
        _videoContext->VideoProcessorSetStreamColorSpace1(
            processor, 0, DXGI_COLOR_SPACE_TYPE.DXGI_COLOR_SPACE_YCBCR_STUDIO_G22_LEFT_P709);
        _videoContext->VideoProcessorSetOutputColorSpace1(processor, DXGI_COLOR_SPACE_TYPE.DXGI_COLOR_SPACE_RGB_FULL_G22_NONE_P709);
        _videoContext->VideoProcessorSetStreamFrameFormat(processor, 0, D3D11_VIDEO_FRAME_FORMAT.D3D11_VIDEO_FRAME_FORMAT_PROGRESSIVE);
        _videoContext->VideoProcessorSetStreamAutoProcessingMode(processor, 0, false);
    }

    private RECT Letterbox(int width, int height)
    {
        double scale = Math.Min((double)_outputWidth / width, (double)_outputHeight / height);
        int scaledWidth = (int)Math.Round(width * scale);
        int scaledHeight = (int)Math.Round(height * scale);
        int left = (_outputWidth - scaledWidth) / 2;
        int top = (_outputHeight - scaledHeight) / 2;
        return new RECT { left = left, top = top, right = left + scaledWidth, bottom = top + scaledHeight };
    }

    private ID3D11Texture2D* CreateTexture(int width, int height)
    {
        var description = new D3D11_TEXTURE2D_DESC
        {
            Width = (uint)width,
            Height = (uint)height,
            MipLevels = 1,
            ArraySize = 1,
            Format = DXGI_FORMAT.DXGI_FORMAT_NV12,
            SampleDesc = new DXGI_SAMPLE_DESC { Count = 1 },
            Usage = D3D11_USAGE.D3D11_USAGE_DEFAULT,
        };
        ID3D11Texture2D* texture;
        _device->CreateTexture2D(&description, null, &texture);
        return texture;
    }

    private ID3D11VideoProcessorOutputView* OutputView()
    {
        if (_outputView != null)
        {
            return _outputView;
        }
        ID3D11Texture2D* buffer;
        Guid textureId = ID3D11Texture2D.IID_Guid;
        _swapChain->GetBuffer(0, &textureId, (void**)&buffer);
        var description = new D3D11_VIDEO_PROCESSOR_OUTPUT_VIEW_DESC
        {
            ViewDimension = D3D11_VPOV_DIMENSION.D3D11_VPOV_DIMENSION_TEXTURE2D,
        };
        ID3D11VideoProcessorOutputView* view;
        _videoDevice->CreateVideoProcessorOutputView((ID3D11Resource*)buffer, _enumerator, &description, &view);
        buffer->Release();
        _outputView = view;
        return view;
    }

    private void ReleaseProcessor()
    {
        Release(ref _inputView);
        Release(ref _texture);
        Release(ref _processor);
        Release(ref _outputView);
        Release(ref _enumerator);
    }

    private static IDXGISwapChain1* CreateSwapChain(ID3D11Device* device, HWND window, int width, int height)
    {
        IDXGIDevice* dxgiDevice = Query<IDXGIDevice>((IUnknown*)device, IDXGIDevice.IID_Guid);
        IDXGIAdapter* adapter;
        dxgiDevice->GetAdapter(&adapter);
        IDXGIFactory2* factory;
        Guid factoryId = IDXGIFactory2.IID_Guid;
        adapter->GetParent(&factoryId, (void**)&factory);
        var description = new DXGI_SWAP_CHAIN_DESC1
        {
            Width = (uint)width,
            Height = (uint)height,
            Format = DXGI_FORMAT.DXGI_FORMAT_B8G8R8A8_UNORM,
            SampleDesc = new DXGI_SAMPLE_DESC { Count = 1 },
            BufferUsage = DXGI_USAGE.DXGI_USAGE_RENDER_TARGET_OUTPUT,
            BufferCount = BufferCount,
            SwapEffect = DXGI_SWAP_EFFECT.DXGI_SWAP_EFFECT_FLIP_DISCARD,
        };
        IDXGISwapChain1* swapChain;
        factory->CreateSwapChainForHwnd((IUnknown*)device, window, &description, null, null, &swapChain);
        factory->Release();
        adapter->Release();
        dxgiDevice->Release();
        return swapChain;
    }

    private static T* Query<T>(IUnknown* source, Guid iid) where T : unmanaged
    {
        void* result;
        source->QueryInterface(&iid, &result);
        return (T*)result;
    }

    private static void Release<T>(ref T* resource) where T : unmanaged
    {
        if (resource == null)
        {
            return;
        }
        ((IUnknown*)resource)->Release();
        resource = null;
    }
}
