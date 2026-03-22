import type { ChunkDraft, ParsedBlock } from '../../shared/types.js';
import { createSnippet } from '../../shared/text.js';

interface ChunkerOptions {
  maxChars: number;
  overlapChars: number;
}

const defaultOptions: ChunkerOptions = {
  maxChars: 1200,
  overlapChars: 180,
};

export class RecursiveChunker {
  private readonly options: ChunkerOptions;

  constructor(options?: Partial<ChunkerOptions>) {
    this.options = { ...defaultOptions, ...options };
  }

  chunk(blocks: ParsedBlock[], baseMetadata: Record<string, unknown>): ChunkDraft[] {
    const chunks: ChunkDraft[] = [];

    let currentText = '';
    let currentPage = 1;
    let currentMetadata: Record<string, unknown> = {};
    let chunkIndex = 0;

    const flush = () => {
      const content = currentText.trim();
      if (!content) {
        return;
      }

      chunks.push({
        chunkIndex,
        pageNumber: currentPage,
        content,
        contextSnippet: createSnippet(content, 360),
        exactQuote: createSnippet(content, 180),
        metadata: {
          ...baseMetadata,
          ...currentMetadata,
        },
      });

      chunkIndex += 1;
      const overlap = content.slice(Math.max(0, content.length - this.options.overlapChars));
      currentText = overlap;
    };

    for (const block of blocks) {
      const normalized = block.text.replace(/\s+/g, ' ').trim();
      if (!normalized) {
        continue;
      }

      const candidate = currentText ? `${currentText} ${normalized}` : normalized;

      if (candidate.length > this.options.maxChars && currentText) {
        flush();
      }

      currentPage = block.pageNumber;
      currentMetadata = {
        bbox: block.bbox,
      };

      if (!currentText) {
        currentText = normalized;
      } else if (`${currentText} ${normalized}`.length <= this.options.maxChars) {
        currentText = `${currentText} ${normalized}`;
      } else {
        const segments = this.splitLongText(normalized);
        for (const segment of segments) {
          const merged = currentText ? `${currentText} ${segment}` : segment;
          if (merged.length > this.options.maxChars && currentText) {
            flush();
            currentText = segment;
          } else {
            currentText = merged;
          }
        }
      }
    }

    flush();
    return chunks;
  }

  private splitLongText(text: string): string[] {
    if (text.length <= this.options.maxChars) {
      return [text];
    }

    const sentences = text.split(/(?<=[.!?])\s+/g);
    const segments: string[] = [];
    let current = '';

    for (const sentence of sentences) {
      const trimmed = sentence.trim();
      if (!trimmed) {
        continue;
      }

      const merged = current ? `${current} ${trimmed}` : trimmed;
      if (merged.length > this.options.maxChars) {
        if (current) {
          segments.push(current);
          current = trimmed;
        } else {
          const chunks = this.sliceHard(trimmed);
          segments.push(...chunks);
          current = '';
        }
      } else {
        current = merged;
      }
    }

    if (current) {
      segments.push(current);
    }

    return segments;
  }

  private sliceHard(text: string): string[] {
    const segments: string[] = [];
    let pointer = 0;

    while (pointer < text.length) {
      const end = pointer + this.options.maxChars;
      segments.push(text.slice(pointer, end));
      pointer = end;
    }

    return segments;
  }
}
