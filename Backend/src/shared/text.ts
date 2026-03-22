const WORD_REGEX = /[a-zA-Z0-9]+/g;

export const tokenize = (text: string): string[] => {
  const matches = text.toLowerCase().match(WORD_REGEX);
  return matches ?? [];
};

export const unique = (items: string[]): string[] => Array.from(new Set(items));

export const overlapScore = (query: string, candidate: string): number => {
  const queryTerms = unique(tokenize(query));
  const candidateSet = new Set(tokenize(candidate));

  if (queryTerms.length === 0) {
    return 0;
  }

  const overlap = queryTerms.filter((term) => candidateSet.has(term)).length;
  return overlap / queryTerms.length;
};

export const createSnippet = (text: string, maxLength = 320): string => {
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength).trim()}...`;
};
