import { mkdirSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { Router } from 'express';
import multer from 'multer';
import { env } from '../../config/env.js';
import { asyncHandler } from '../../http/async-handler.js';
import { AppError } from '../../shared/errors.js';
import { DocumentController } from './document.controller.js';

const sanitizeFilename = (filename: string): string => filename.replace(/[^a-zA-Z0-9._-]/g, '_');

export const buildDocumentRoutes = (documentController: DocumentController): Router => {
  mkdirSync(env.UPLOAD_DIR, { recursive: true });

  const storage = multer.diskStorage({
    destination: (_req, _file, callback) => {
      callback(null, env.UPLOAD_DIR);
    },
    filename: (_req, file, callback) => {
      callback(null, `${Date.now()}-${randomUUID()}-${sanitizeFilename(file.originalname)}`);
    },
  });

  const upload = multer({
    storage,
    limits: {
      fileSize: env.MAX_FILE_SIZE_MB * 1024 * 1024,
    },
    fileFilter: (_req, file, callback) => {
      const isPdf = file.mimetype === 'application/pdf' || path.extname(file.originalname).toLowerCase() === '.pdf';
      if (!isPdf) {
        callback(new AppError('Only PDF files are supported', 400, 'UNSUPPORTED_FILE_TYPE'));
        return;
      }
      callback(null, true);
    },
  });

  const router = Router({ mergeParams: true });

  router.get('/', asyncHandler((req, res) => documentController.listDocuments(req, res)));
  router.post('/upload', upload.single('file'), asyncHandler((req, res) => documentController.uploadDocument(req, res)));

  return router;
};
