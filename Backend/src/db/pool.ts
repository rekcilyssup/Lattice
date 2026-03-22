import { Pool, type QueryResultRow } from 'pg';
import { env } from '../config/env.js';

export const pool = new Pool({
  host: env.POSTGRES_HOST,
  port: env.POSTGRES_PORT,
  database: env.POSTGRES_DB,
  user: env.POSTGRES_USER,
  password: env.POSTGRES_PASSWORD,
  ssl: env.POSTGRES_SSL ? { rejectUnauthorized: false } : false,
});

export const query = <T extends QueryResultRow = QueryResultRow>(text: string, params?: unknown[]) => pool.query<T>(text, params);
