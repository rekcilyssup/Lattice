import type { RouteStrategy } from './retrieval.types.js';

const METADATA_HINTS = ['author', 'uploaded', 'upload date', 'document type', 'access level', 'which document', 'list documents'];

export class SemanticRouterService {
  route(query: string): RouteStrategy {
    const normalized = query.toLowerCase();

    if (METADATA_HINTS.some((hint) => normalized.includes(hint))) {
      return 'metadata';
    }

    const hasQuotedTerm = /"[^"]+"/.test(query);
    const hasAcronym = /\b[A-Z]{2,}\b/.test(query);
    const hasIdentifierPattern = /\b[a-zA-Z]*\d+[a-zA-Z-]*\b/.test(query);

    if (hasQuotedTerm || hasAcronym || hasIdentifierPattern) {
      return 'keyword';
    }

    if (normalized.split(' ').length <= 3) {
      return 'hybrid';
    }

    return 'vector';
  }
}
