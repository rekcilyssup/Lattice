import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pool } from './pool.js';
import { logger } from '../shared/logger.js';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const migrationsDir = path.resolve(currentDir, '../migrations');

const main = async () => {
  const client = await pool.connect();

  try {
    await client.query('BEGIN');
    await client.query(`
      CREATE TABLE IF NOT EXISTS schema_migrations (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
    `);

    const files = (await readdir(migrationsDir)).filter((file) => file.endsWith('.sql')).sort();

    for (const file of files) {
      const exists = await client.query<{ name: string }>('SELECT name FROM schema_migrations WHERE name = $1', [file]);

      if (exists.rowCount && exists.rowCount > 0) {
        continue;
      }

      const filePath = path.join(migrationsDir, file);
      const sql = await readFile(filePath, 'utf8');

      logger.info({ migration: file }, 'Applying migration');
      await client.query(sql);
      await client.query('INSERT INTO schema_migrations(name) VALUES($1)', [file]);
    }

    await client.query('COMMIT');
    logger.info('Migrations complete');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
};

main().catch((error) => {
  logger.error({ error }, 'Migration failed');
  process.exitCode = 1;
});
