import { readFile } from 'node:fs/promises';
import type { ParsedBlock } from '../../shared/types.js';

interface TextItem {
  str?: string;
  transform?: number[];
  width?: number;
  height?: number;
}

interface PositionedItem {
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export class PdfLayoutParser {
  async parse(filePath: string): Promise<ParsedBlock[]> {
    const buffer = await readFile(filePath);
    const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');

    const loadingTask = pdfjs.getDocument({ data: new Uint8Array(buffer) });
    const document = await loadingTask.promise;

    const blocks: ParsedBlock[] = [];

    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
      const page = await document.getPage(pageNumber);
      const content = await page.getTextContent();

      const items = (content.items as TextItem[])
        .map<PositionedItem | null>((item) => {
          const text = (item.str ?? '').trim();
          const transform = item.transform;

          if (!text || !transform || transform.length < 6) {
            return null;
          }

          return {
            text,
            x: transform[4],
            y: transform[5],
            width: item.width ?? text.length,
            height: item.height ?? 10,
          };
        })
        .filter((item): item is PositionedItem => item !== null)
        .sort((a, b) => {
          const yDiff = b.y - a.y;
          if (Math.abs(yDiff) > 2) {
            return yDiff;
          }
          return a.x - b.x;
        });

      const lines: Array<{ y: number; items: PositionedItem[] }> = [];

      for (const item of items) {
        const existingLine = lines.find((line) => Math.abs(line.y - item.y) <= 2.5);
        if (!existingLine) {
          lines.push({ y: item.y, items: [item] });
        } else {
          existingLine.items.push(item);
        }
      }

      lines
        .sort((a, b) => b.y - a.y)
        .forEach((line) => {
          const sortedItems = line.items.sort((a, b) => a.x - b.x);
          const text = sortedItems.map((item) => item.text).join(' ').replace(/\s+/g, ' ').trim();

          if (!text) {
            return;
          }

          const xMin = Math.min(...sortedItems.map((item) => item.x));
          const yMin = Math.min(...sortedItems.map((item) => item.y));
          const xMax = Math.max(...sortedItems.map((item) => item.x + item.width));
          const yMax = Math.max(...sortedItems.map((item) => item.y + item.height));

          blocks.push({
            pageNumber,
            text,
            bbox: {
              xMin,
              yMin,
              xMax,
              yMax,
            },
          });
        });
    }

    return blocks;
  }
}
