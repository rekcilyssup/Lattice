import { env } from './config/env.js';
import { pool } from './db/pool.js';
import { createApp } from './app.js';
import { logger } from './shared/logger.js';

const app = createApp();

const server = app.listen(env.PORT, () => {
  logger.info({ port: env.PORT }, 'Lattice backend listening');
});

const shutdown = async (signal: NodeJS.Signals) => {
  logger.info({ signal }, 'Shutting down backend');
  server.close(async () => {
    await pool.end();
    process.exit(0);
  });
};

process.on('SIGINT', () => {
  void shutdown('SIGINT');
});

process.on('SIGTERM', () => {
  void shutdown('SIGTERM');
});
