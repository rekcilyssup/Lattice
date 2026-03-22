import { Router } from 'express';

export const buildHealthRoutes = (): Router => {
  const router = Router();

  router.get('/', (_req, res) => {
    res.status(200).json({
      status: 'ok',
      service: 'lattice-backend',
      timestamp: new Date().toISOString(),
    });
  });

  return router;
};
