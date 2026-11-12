import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";

const SPIKE_ROOT = fileURLToPath(new URL(".", import.meta.url));
const RESULTS_DIRECTORY = join(SPIKE_ROOT, "results");
const TLS_DIRECTORY = join(process.env.LOCALAPPDATA ?? "", "wcam", "tls");
const SPIKE_PORT = 5174;

function saveResults(): Plugin {
  return {
    name: "spike-save-results",
    configureServer(server) {
      server.middlewares.use("/spike-result", (request, response) => {
        let body = "";
        request.on("data", (chunk: Buffer) => (body += chunk.toString()));
        request.on("end", () => {
          mkdirSync(RESULTS_DIRECTORY, { recursive: true });
          const file = join(RESULTS_DIRECTORY, `zoom-${Date.now()}.json`);
          writeFileSync(file, body);
          server.config.logger.info(`spike result saved: ${file}`);
          response.statusCode = 204;
          response.end();
        });
      });
    },
  };
}

export default defineConfig({
  root: SPIKE_ROOT,
  plugins: [saveResults()],
  server: {
    host: "0.0.0.0",
    port: SPIKE_PORT,
    strictPort: true,
    https: {
      cert: readFileSync(join(TLS_DIRECTORY, "cert.pem")),
      key: readFileSync(join(TLS_DIRECTORY, "key.pem")),
    },
  },
});
