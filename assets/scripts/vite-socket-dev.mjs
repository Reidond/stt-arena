import { createServer as createHttpServer } from "node:http";
import { lstatSync, mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { createServer as createViteServer } from "vite";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const assetsRoot = resolve(scriptDir, "..");
const socketPath = process.env.VITE_SOCKET_PATH ?? resolve(tmpdir(), "stt-arena", "vite.sock");
const hmrHost = process.env.VITE_HMR_HOST ?? "localhost";
const hmrClientPort = Number(process.env.VITE_HMR_CLIENT_PORT ?? "8000");
const hmrPath = process.env.VITE_HMR_PATH ?? "/@vite/ws";

mkdirSync(dirname(socketPath), { recursive: true });
rmSync(socketPath, { force: true });

const httpServer = createHttpServer();
let ownedSocketIdentity;
let shuttingDown = false;

function socketIdentity() {
  try {
    const stats = lstatSync(socketPath);
    return `${stats.dev}:${stats.ino}`;
  } catch {
    return undefined;
  }
}

function removeOwnedSocket() {
  if (ownedSocketIdentity !== undefined && socketIdentity() === ownedSocketIdentity) {
    rmSync(socketPath, { force: true });
  }
}

const vite = await createViteServer({
  root: assetsRoot,
  configFile: resolve(assetsRoot, "vite.config.ts"),
  appType: "custom",
  server: {
    middlewareMode: { server: httpServer },
    hmr: {
      server: httpServer,
      protocol: "ws",
      host: hmrHost,
      clientPort: hmrClientPort,
      path: hmrPath,
    },
  },
});

httpServer.on("request", vite.middlewares);

function shutdown() {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  void vite.close().finally(() => {
    httpServer.close(() => {
      removeOwnedSocket();
      process.exit(0);
    });
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

httpServer.listen(socketPath, () => {
  ownedSocketIdentity = socketIdentity();
  console.log(`Vite dev server listening on ${socketPath}`);
});
