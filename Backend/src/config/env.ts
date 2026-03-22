import { config } from 'dotenv';
import { z } from 'zod';

config();

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(1).max(65535).default(8080),
  API_BASE_PATH: z.string().default('/api/v1'),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent']).default('info'),

  POSTGRES_HOST: z.string().default('localhost'),
  POSTGRES_PORT: z.coerce.number().int().default(5432),
  POSTGRES_DB: z.string().default('lattice'),
  POSTGRES_USER: z.string().default('lattice'),
  POSTGRES_PASSWORD: z.string().default('lattice'),
  POSTGRES_SSL: z.enum(['true', 'false']).default('false').transform((value) => value === 'true'),

  EMBEDDING_DIMENSION: z.coerce.number().int().positive().default(1536),
  EMBEDDING_PROVIDER: z.enum(['openai', 'gemini', 'ollama', 'mock']).default('ollama'),
  EMBEDDING_MODEL: z.string().default('text-embedding-3-small'),
  OPENAI_API_KEY: z.string().optional().default(''),
  GEMINI_API_KEY: z.string().optional().default(''),
  OLLAMA_BASE_URL: z.string().default('http://localhost:11434'),
  OLLAMA_EMBEDDING_MODEL: z.string().default('nomic-embed-text'),

  LLM_PROVIDER: z.enum(['openai', 'gemini', 'ollama', 'mock']).default('ollama'),
  LLM_MODEL: z.string().default('llama3.2:1b'),
  LLM_TEMPERATURE: z.coerce.number().min(0).max(2).default(0),

  RERANK_PROVIDER: z.enum(['heuristic', 'cohere']).default('heuristic'),
  COHERE_API_KEY: z.string().optional().default(''),

  TOP_K_DENSE: z.coerce.number().int().positive().default(15),
  TOP_K_SPARSE: z.coerce.number().int().positive().default(15),
  TOP_K_RERANK: z.coerce.number().int().positive().default(8),

  CORS_ORIGIN: z.string().default('http://localhost:3000'),
  UPLOAD_DIR: z.string().default('storage/uploads'),
  MAX_FILE_SIZE_MB: z.coerce.number().positive().default(20),
});

const parsed = envSchema.parse(process.env);

export const env = {
  ...parsed,
  POSTGRES_SSL: parsed.POSTGRES_SSL,
};

export type Env = typeof env;
