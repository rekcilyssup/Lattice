import type { ErrorRequestHandler } from 'express';
import multer from 'multer';
import { ZodError } from 'zod';
import { isAppError } from '../shared/errors.js';
import { logger } from '../shared/logger.js';

export const errorMiddleware: ErrorRequestHandler = (error, _req, res, _next) => {
  if (error instanceof ZodError) {
    res.status(400).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid request payload',
        details: error.flatten(),
      },
    });
    return;
  }

  if (error instanceof multer.MulterError) {
    res.status(400).json({
      error: {
        code: 'UPLOAD_ERROR',
        message: error.message,
      },
    });
    return;
  }

  if (isAppError(error)) {
    res.status(error.statusCode).json({
      error: {
        code: error.code,
        message: error.message,
        details: error.details,
      },
    });
    return;
  }

  logger.error({ error }, 'Unhandled server error');

  res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'Unexpected server error',
    },
  });
};
