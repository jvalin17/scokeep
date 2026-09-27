/**
 * logger.test.js — Sensitive fields must not appear in apiCall logs.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logger } from '../../app/static/js/components/logger.js';

describe('test_api_call_redacts_pin', () => {
  let logSpy;

  beforeEach(() => {
    logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    logSpy.mockRestore();
  });

  it('redacts pin in auth body so console does not show the PIN', () => {
    logger.apiCall('POST', '/playground/auth', { name: 'Trial1', pin: '1234' });

    expect(logSpy).toHaveBeenCalled();
    const loggedData = logSpy.mock.calls[0][2];
    expect(loggedData.pin).toBe('[REDACTED]');
    expect(loggedData.name).toBe('Trial1');
    // Original object must not be mutated
    expect(loggedData).not.toBe({ name: 'Trial1', pin: '1234' });
  });

  it('redacts password and pin_hint fields', () => {
    logger.apiCall('POST', '/playground', {
      name: 'Room',
      pin: '9999',
      pin_hint: 'mom birthday',
      password: 'secret',
    });
    const loggedData = logSpy.mock.calls[0][2];
    expect(loggedData.pin).toBe('[REDACTED]');
    expect(loggedData.pin_hint).toBe('[REDACTED]');
    expect(loggedData.password).toBe('[REDACTED]');
  });
});
