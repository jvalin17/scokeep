import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import {
  getTrumpForRound,
  getCardsForRound,
  maxCardsForPlayers,
} from "../../app/static/js/engine/trump.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(
  readFileSync(join(__dirname, "../vectors/trump_vectors.json"), "utf-8")
);

describe("getTrumpForRound", () => {
  it("returns a string suit name for each vector", () => {
    for (const { round, trump } of vectors.trump_rotation) {
      expect(getTrumpForRound(round)).toBe(trump);
    }
  });

  it("round 1 is spades", () => {
    expect(getTrumpForRound(1)).toBe("spades");
  });

  it("round 4 is hearts", () => {
    expect(getTrumpForRound(4)).toBe("hearts");
  });

  it("round 5 wraps back to spades", () => {
    expect(getTrumpForRound(5)).toBe("spades");
  });

  it("returns a string (not an object)", () => {
    expect(typeof getTrumpForRound(1)).toBe("string");
  });
});

describe("getCardsForRound", () => {
  it("matches all cards_per_round vectors", () => {
    for (const { round, rounds_per_set, cards } of vectors.cards_per_round) {
      expect(getCardsForRound(round, rounds_per_set)).toBe(cards);
    }
  });

  it("set 1 descends 8 to 1", () => {
    const expected = [8, 7, 6, 5, 4, 3, 2, 1];
    const actual = Array.from({ length: 8 }, (_, i) => getCardsForRound(i + 1));
    expect(actual).toEqual(expected);
  });

  it("set 2 ascends 1 to 8", () => {
    const expected = [1, 2, 3, 4, 5, 6, 7, 8];
    const actual = Array.from({ length: 8 }, (_, i) => getCardsForRound(i + 9));
    expect(actual).toEqual(expected);
  });

  it("set 3 descends again 8 to 1", () => {
    const expected = [8, 7, 6, 5, 4, 3, 2, 1];
    const actual = Array.from({ length: 8 }, (_, i) => getCardsForRound(i + 17));
    expect(actual).toEqual(expected);
  });

  it("uses default rounds_per_set of 8", () => {
    expect(getCardsForRound(1)).toBe(8);
    expect(getCardsForRound(8)).toBe(1);
  });
});

describe("maxCardsForPlayers", () => {
  it("matches all max_cards vectors", () => {
    for (const { players, max_cards } of vectors.max_cards) {
      expect(maxCardsForPlayers(players)).toBe(max_cards);
    }
  });

  it("4 players => 13", () => {
    expect(maxCardsForPlayers(4)).toBe(13);
  });

  it("uses integer division (floor)", () => {
    expect(maxCardsForPlayers(3)).toBe(17); // 52 / 3 = 17.33 → 17
  });
});
