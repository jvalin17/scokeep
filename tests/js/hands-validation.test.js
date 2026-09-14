import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { validateHands } from "../../app/static/js/engine/hands.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const vectors = JSON.parse(
  readFileSync(join(__dirname, "../vectors/hands_vectors.json"), "utf-8")
);

describe("validateHands", () => {
  it("returns null for all valid vectors", () => {
    for (const v of vectors.validate_hands) {
      if (!v.valid) continue;
      const result = validateHands(v.existing_hands, v.player_index, v.value, v.cards_dealt);
      expect(result, `[${v.description}] expected null but got: ${result}`).toBeNull();
    }
  });

  it("returns an error string for all invalid vectors", () => {
    for (const v of vectors.validate_hands) {
      if (v.valid) continue;
      const result = validateHands(v.existing_hands, v.player_index, v.value, v.cards_dealt);
      expect(result, `[${v.description}] expected error string but got: ${result}`).toBeTypeOf("string");
    }
  });

  it("exceeds remaining — returns error string", () => {
    // existing: {0:2, 1:3} = 5 others, remaining = 8-5 = 3; value 4 > 3
    const result = validateHands({ "0": 2, "1": 3 }, 2, 4, 8);
    expect(result).toBeTypeOf("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("equals remaining — returns null", () => {
    // existing: {0:2, 1:3} = 5 others, remaining = 8-5 = 3; value 3 == 3
    const result = validateHands({ "0": 2, "1": 3 }, 2, 3, 8);
    expect(result).toBeNull();
  });

  it("zero always valid", () => {
    // even if others filled 7 of 8 cards, value 0 is fine
    const result = validateHands({ "0": 5, "1": 2 }, 2, 0, 8);
    expect(result).toBeNull();
  });

  it("first entry with no existing hands — within deck", () => {
    const result = validateHands({}, 0, 5, 8);
    expect(result).toBeNull();
  });

  it("first entry exceeds full deck — rejected", () => {
    const result = validateHands({}, 0, 9, 8);
    expect(result).toBeTypeOf("string");
  });

  it("1-card round — value 1 ok", () => {
    expect(validateHands({}, 0, 1, 1)).toBeNull();
  });

  it("1-card round — value 2 rejected", () => {
    const result = validateHands({}, 0, 2, 1);
    expect(result).toBeTypeOf("string");
  });

  it("1-card round — others took card, player claims 0 — ok", () => {
    expect(validateHands({ "0": 1 }, 1, 0, 1)).toBeNull();
  });

  it("1-card round — others took card, player claims 1 — rejected", () => {
    const result = validateHands({ "0": 1 }, 1, 1, 1);
    expect(result).toBeTypeOf("string");
  });

  it("negative value — rejected", () => {
    const result = validateHands({ "0": 2 }, 1, -1, 8);
    expect(result).toBeTypeOf("string");
  });

  it("player's own existing entry is excluded from others sum", () => {
    // player 0 already has 3; others sum uses only player 1's 2; remaining = 8-2 = 6
    // player 0 submitting 6 should be valid
    const result = validateHands({ "0": 3, "1": 2 }, 0, 6, 8);
    expect(result).toBeNull();
  });

  it("error message contains value and remaining", () => {
    // existing: {0:2, 1:3} others=5, remaining=3; value=4
    const result = validateHands({ "0": 2, "1": 3 }, 2, 4, 8);
    expect(result).toContain("4");
    expect(result).toContain("3");
  });
});
