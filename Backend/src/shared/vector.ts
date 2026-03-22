export const toPgVectorLiteral = (values: number[]): string => `[${values.join(',')}]`;

export const normalizeL2 = (values: number[]): number[] => {
  const magnitude = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0));
  if (magnitude === 0) {
    return values;
  }
  return values.map((value) => value / magnitude);
};
