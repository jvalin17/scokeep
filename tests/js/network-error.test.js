/**
 * network-error.test.js — Tests for the NetworkError class.
 *
 * Run with: npx vitest run tests/js/network-error.test.js
 */

import { describe, it, expect } from 'vitest';
import { NetworkError } from '../../app/static/js/components/network-error.js';

describe('test_network_error_is_error', () => {
  it('extends Error', () => {
    const err = new NetworkError('offline');
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(NetworkError);
  });
});

describe('test_network_error_message', () => {
  it('stores the message', () => {
    const err = new NetworkError('exhausted');
    expect(err.message).toBe('exhausted');
  });
});

describe('test_network_error_name', () => {
  it('has name NetworkError', () => {
    const err = new NetworkError('offline');
    expect(err.name).toBe('NetworkError');
  });
});

describe('test_network_error_reason', () => {
  it('stores the reason for programmatic checks', () => {
    const err = new NetworkError('offline');
    expect(err.reason).toBe('offline');
  });

  it('defaults reason to message if not provided', () => {
    const err = new NetworkError('test');
    expect(err.reason).toBe('test');
  });
});
