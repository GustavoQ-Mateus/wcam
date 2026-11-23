export interface Nv12Renderer {
  draw: (frame: ArrayBuffer, width: number, height: number) => void;
  dispose: () => void;
}

const CHROMA_SUBSAMPLING = 2;
const TRIANGLE_VERTICES = 3;
const LUMA_UNIT = 0;
const CHROMA_UNIT = 1;
const BYTE_ALIGNMENT = 1;

const VERTEX_SHADER = `#version 300 es
out vec2 position;
void main() {
  vec2 corner = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  position = vec2(corner.x, 1.0 - corner.y);
  gl_Position = vec4(corner * 2.0 - 1.0, 0.0, 1.0);
}`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;
const float LUMA_FLOOR = 16.0 / 255.0;
const float LUMA_SPAN = 219.0 / 255.0;
const float CHROMA_CENTER = 128.0 / 255.0;
const float CHROMA_SPAN = 224.0 / 255.0;
const mat3 BT709_TO_RGB = mat3(1.0, 1.0, 1.0, 0.0, -0.1873, 1.8556, 1.5748, -0.4681, 0.0);
uniform sampler2D luma;
uniform sampler2D chroma;
in vec2 position;
out vec4 color;
void main() {
  float y = (texture(luma, position).r - LUMA_FLOOR) / LUMA_SPAN;
  vec2 uv = (texture(chroma, position).rg - CHROMA_CENTER) / CHROMA_SPAN;
  color = vec4(clamp(BT709_TO_RGB * vec3(y, uv), 0.0, 1.0), 1.0);
}`;

export function createNv12Renderer(canvas: HTMLCanvasElement): Nv12Renderer | null {
  const gl = canvas.getContext("webgl2", { alpha: false, antialias: false, depth: false });
  if (!gl) {
    return null;
  }
  const program = linkProgram(gl);
  if (!program) {
    return null;
  }
  gl.useProgram(program);
  gl.uniform1i(gl.getUniformLocation(program, "luma"), LUMA_UNIT);
  gl.uniform1i(gl.getUniformLocation(program, "chroma"), CHROMA_UNIT);
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, BYTE_ALIGNMENT);
  const luma = createPlaneTexture(gl, LUMA_UNIT);
  const chroma = createPlaneTexture(gl, CHROMA_UNIT);
  let size = { width: 0, height: 0 };

  const resize = (width: number, height: number) => {
    canvas.width = width;
    canvas.height = height;
    gl.viewport(0, 0, width, height);
    size = { width, height };
  };

  return {
    draw: (frame, width, height) => {
      if (size.width !== width || size.height !== height) {
        resize(width, height);
      }
      const lumaBytes = width * height;
      const chromaWidth = width / CHROMA_SUBSAMPLING;
      const chromaHeight = height / CHROMA_SUBSAMPLING;
      gl.activeTexture(gl.TEXTURE0 + LUMA_UNIT);
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.R8,
        width,
        height,
        0,
        gl.RED,
        gl.UNSIGNED_BYTE,
        new Uint8Array(frame, 0, lumaBytes),
      );
      gl.activeTexture(gl.TEXTURE0 + CHROMA_UNIT);
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RG8,
        chromaWidth,
        chromaHeight,
        0,
        gl.RG,
        gl.UNSIGNED_BYTE,
        new Uint8Array(frame, lumaBytes, lumaBytes / CHROMA_SUBSAMPLING),
      );
      gl.drawArrays(gl.TRIANGLES, 0, TRIANGLE_VERTICES);
    },
    dispose: () => {
      gl.deleteTexture(luma);
      gl.deleteTexture(chroma);
      gl.deleteProgram(program);
    },
  };
}

function createPlaneTexture(gl: WebGL2RenderingContext, unit: number): WebGLTexture {
  const texture = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0 + unit);
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return texture;
}

function linkProgram(gl: WebGL2RenderingContext): WebGLProgram | null {
  const program = gl.createProgram();
  gl.attachShader(program, compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER));
  gl.attachShader(program, compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
  gl.linkProgram(program);
  return gl.getProgramParameter(program, gl.LINK_STATUS) ? program : null;
}

function compileShader(gl: WebGL2RenderingContext, type: GLenum, source: string): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) {
    throw new Error("WebGL2 could not create a shader");
  }
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  return shader;
}
