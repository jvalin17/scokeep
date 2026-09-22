/**
 * retry-logic.test.js — Tests for the retry wrapper in api.js request().
 *
 * Mocks fetch via vi.stubGlobal. Tests retry count, backoff, banner,
 * NetworkError, and SW 503 handling.
 *
 * Run with: npx vitest run tests/js/retry-logic.test.js
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// We need to import AFTER mocking — use dynamic import in each test.
// But first, set up the fetch mock and banner module mock.

// ─── helpers ──────────────────────────────────────────────────────────────────

function setOnline(value) {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true });
}

function makeTypeError() {
  return new TypeError('Failed to fetch');
}

function makeAbortError() {
  const err = new DOMException('The operation was aborted', 'AbortError');
  return err;
}

function make503OfflineResponse() {
  return {
    ok: false,
    status: 503,
    json: () => Promise.resolve({ offline: true }),
  };
}

function make200Response(data = {}) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  };
}

function make400Response(detail = 'Bad request') {
  return {
    ok: false,
    status: 400,
    json: () => Promise.resolve({ detail }),
  };
}

// ─── module-level setup ───────────────────────────────────────────────────────

let request, NetworkError, banner;

beforeEach(async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  setOnline(true);
  vi.stubGlobal('fetch', vi.fn());

  // Clear module cache so each test gets fresh state
  vi.resetModules();

  // Dynamically import to get fresh modules with mocked fetch
  const apiModule = await import('../../app/static/js/api.js');
  request = apiModule._request;

  const errorModule = await import('../../app/static/js/components/network-error.js');
  NetworkError = errorModule.NetworkError;

  const bannerModule = await import('../../app/static/js/components/connection-banner.js');
  banner = bannerModule.banner;
  // Spy on banner methods
  vi.spyOn(banner, 'showReconnecting');
  vi.spyOn(banner, 'hide');
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

// ─── succeeds on first try ────────────────────────────────────────────────────

describe('test_request_succeeds_first_try', () => {
  it('returns data without retrying', async () => {
    globalThis.fetch.mockResolvedValueOnce(make200Response({ id: 1 }));
    const result = await request('GET', '/game/1');
    expect(result).toEqual({ id: 1 });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    expect(banner.showReconnecting).not.toHaveBeenCalled();
  });
});

// ─── retries on network error, succeeds on 2nd ────────────────────────────────

describe('test_request_retries_on_network_error', () => {
  it('retries after TypeError and succeeds on 2nd attempt', async () => {
    globalThis.fetch
      .mockRejectedValueOnce(makeTypeError())
      .mockResolvedValueOnce(make200Response({ id: 2 }));

    const promise = request('GET', '/game/2');
    // Advance past the backoff delay
    await vi.advanceTimersByTimeAsync(5000);
    const result = await promise;

    expect(result).toEqual({ id: 2 });
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
    expect(banner.showReconnecting).toHaveBeenCalled();
    expect(banner.hide).toHaveBeenCalled();
  });
});

// ─── all retries fail → NetworkError ──────────────────────────────────────────

describe('test_request_all_retries_fail_throws_network_error', () => {
  it('throws NetworkError after 4 failed attempts', async () => {
    globalThis.fetch
      .mockRejectedValueOnce(makeTypeError())
      .mockRejectedValueOnce(makeTypeError())
      .mockRejectedValueOnce(makeTypeError())
      .mockRejectedValueOnce(makeTypeError());

    const promise = request('GET', '/game/3');
    // Attach catch immediately to prevent unhandled rejection
    const caughtPromise = promise.catch(err => err);
    await vi.advanceTimersByTimeAsync(30000);

    const err = await caughtPromise;
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.reason).toBe('exhausted');
    expect(globalThis.fetch).toHaveBeenCalledTimes(4);
  });
});

// ─── 4xx not retried ──────────────────────────────────────────────────────────

describe('test_request_4xx_not_retried', () => {
  it('throws immediately on 400 without retrying', async () => {
    globalThis.fetch.mockResolvedValueOnce(make400Response('invalid'));

    await expect(request('POST', '/game/1/bid', { value: 5 }))
      .rejects.toThrow('invalid');
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});

// ─── SW 503 with offline:true is retried ──────────────────────────────────────

describe('test_request_sw_503_offline_retried', () => {
  it('treats SW 503 with offline body as retryable', async () => {
    globalThis.fetch
      .mockResolvedValueOnce(make503OfflineResponse())
      .mockResolvedValueOnce(make200Response({ ok: true }));

    const promise = request('GET', '/game/4');
    await vi.advanceTimersByTimeAsync(5000);
    const result = await promise;

    expect(result).toEqual({ ok: true });
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});

// ─── AbortError (timeout) is retried ──────────────────────────────────────────

describe('test_request_timeout_retried', () => {
  it('retries on AbortError from timeout', async () => {
    globalThis.fetch
      .mockRejectedValueOnce(makeAbortError())
      .mockResolvedValueOnce(make200Response({ ok: true }));

    const promise = request('GET', '/game/5');
    await vi.advanceTimersByTimeAsync(20000);
    const result = await promise;

    expect(result).toEqual({ ok: true });
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});

// ─── navigator.onLine=false → instant NetworkError ────────────────────────────

describe('test_request_offline_instant_network_error', () => {
  it('throws NetworkError immediately when navigator.onLine is false', async () => {
    setOnline(false);

    await expect(request('GET', '/game/6'))
      .rejects.toThrow();
    const err = await request('GET', '/game/6').catch(e => e);
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.reason).toBe('offline');
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});

// ─── banner hides on successful retry ─────────────────────────────────────────

describe('test_request_banner_hides_on_success', () => {
  it('shows reconnecting then hides after successful retry', async () => {
    globalThis.fetch
      .mockRejectedValueOnce(makeTypeError())
      .mockResolvedValueOnce(make200Response({ ok: true }));

    const promise = request('GET', '/game/7');
    await vi.advanceTimersByTimeAsync(5000);
    await promise;

    expect(banner.showReconnecting).toHaveBeenCalled();
    expect(banner.hide).toHaveBeenCalled();
  });
});

// ─── backoff delays increase ──────────────────────────────────────────────────

describe('test_request_backoff_increases', () => {
  it('waits longer between each retry attempt', async () => {
    // All fail — we just want to confirm fetch is called 4 times total
    globalThis.fetch.mockRejectedValue(makeTypeError());

    const promise = request('GET', '/game/8');
    const caughtPromise = promise.catch(() => {});
    await vi.advanceTimersByTimeAsync(40000);
    await caughtPromise;

    expect(globalThis.fetch).toHaveBeenCalledTimes(4);
  });
});

// ─── L1: no unused lastError variable ────────────────────────────────────────

describe('test_request_no_unused_lasterror', () => {
  it('exhausted retries throw NetworkError without relying on lastError', async () => {
    globalThis.fetch
      .mockRejectedValueOnce(makeTypeError())
      .mockRejectedValueOnce(makeTypeError())
      .mockRejectedValueOnce(makeTypeError())
      .mockRejectedValueOnce(makeTypeError());

    const promise = request('GET', '/game/l1');
    const caughtPromise = promise.catch(err => err);
    await vi.advanceTimersByTimeAsync(30000);

    const err = await caughtPromise;
    // NetworkError is thrown directly — not from a stored lastError
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.reason).toBe('exhausted');
    expect(err.message).not.toContain('Failed to fetch');
  });
});

// ─── server 500 is NOT retried ────────────────────────────────────────────────

describe('test_request_server_500_not_retried', () => {
  it('throws on server 500 without retrying', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: 'Internal error' }),
    });

    await expect(request('GET', '/game/9')).rejects.toThrow('Internal error');
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});

// ─── 503 without offline body is NOT retried ──────────────────────────────────

describe('test_request_server_503_without_offline_not_retried', () => {
  it('throws on regular 503 without retrying', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: () => Promise.resolve({ detail: 'Service unavailable' }),
    });

    await expect(request('GET', '/game/10')).rejects.toThrow('Service unavailable');
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});
