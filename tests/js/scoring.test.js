import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import {
  kachufulStandard,
  kachufulZeros,
  calculateRoundScores,
} from '../../app/static/js/engine/scoring.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

const scoringVectors = JSON.parse(
  readFileSync(join(__dirname, '../vectors/scoring_vectors.json'), 'utf8')
);
const roundVectors = JSON.parse(
  readFileSync(join(__dirname, '../vectors/round_scoring_vectors.json'), 'utf8')
);

describe('kachufulStandard', () => {
  for (const { bid, actual, expected } of scoringVectors.kachuful_standard) {
    it(`bid=${bid}, actual=${actual} => ${expected}`, () => {
      expect(kachufulStandard(bid, actual)).toBe(expected);
    });
  }
});

describe('kachufulZeros', () => {
  for (const { bid, actual, expected } of scoringVectors.kachuful_zeros) {
    it(`bid=${bid}, actual=${actual} => ${expected}`, () => {
      expect(kachufulZeros(bid, actual)).toBe(expected);
    });
  }
});

describe('calculateRoundScores — kachuful_standard', () => {
  for (const { description, bids, hands_won, expected } of roundVectors.kachuful_standard) {
    it(description, () => {
      expect(calculateRoundScores(bids, hands_won, 'kachuful_standard')).toEqual(expected);
    });
  }
});

describe('calculateRoundScores — kachuful_zeros', () => {
  for (const { description, bids, hands_won, expected } of roundVectors.kachuful_zeros) {
    it(description, () => {
      expect(calculateRoundScores(bids, hands_won, 'kachuful_zeros')).toEqual(expected);
    });
  }
});

describe('calculateRoundScores — error handling', () => {
  it('throws on unknown formula', () => {
    expect(() => calculateRoundScores({ '0': 1 }, { '0': 1 }, 'nonexistent')).toThrow(
      'Unknown scoring formula: nonexistent'
    );
  });
});
