/**
 * connection-banner.test.js — Tests for the connection status banner.
 *
 * Run with: npx vitest run tests/js/connection-banner.test.js
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { banner } from '../../app/static/js/components/connection-banner.js';

beforeEach(() => {
  banner.hide();
});

afterEach(() => {
  banner.hide();
});

// ─── helper ───────────────────────────────────────────────────────────────────

function getBannerEl() {
  return document.getElementById('connection-banner');
}

// ─── showReconnecting ─────────────────────────────────────────────────────────

describe('test_banner_show_reconnecting', () => {
  it('inserts a yellow banner with "Reconnecting" text', () => {
    banner.showReconnecting();
    const el = getBannerEl();
    expect(el).not.toBeNull();
    expect(el.textContent).toContain('Reconnecting');
    expect(el.style.backgroundColor).toContain('f59e0b');
  });
});

// ─── showOffline ──────────────────────────────────────────────────────────────

describe('test_banner_show_offline', () => {
  it('shows orange banner with offline message', () => {
    banner.showOffline();
    const el = getBannerEl();
    expect(el).not.toBeNull();
    expect(el.textContent).toContain('Playing offline');
    expect(el.style.backgroundColor).toContain('ea580c');
  });
});

// ─── showSynced ───────────────────────────────────────────────────────────────

describe('test_banner_show_synced', () => {
  it('shows green banner with synced message', () => {
    banner.showSynced();
    const el = getBannerEl();
    expect(el).not.toBeNull();
    expect(el.textContent).toContain('Synced');
    expect(el.style.backgroundColor).toContain('16a34a');
  });

  it('auto-hides after 3 seconds', () => {
    vi.useFakeTimers();
    banner.showSynced();
    expect(getBannerEl()).not.toBeNull();
    vi.advanceTimersByTime(3000);
    expect(getBannerEl()).toBeNull();
    vi.useRealTimers();
  });
});

// ─── showSyncFailed ───────────────────────────────────────────────────────────

describe('test_banner_show_sync_failed', () => {
  it('shows red banner with failure message', () => {
    banner.showSyncFailed();
    const el = getBannerEl();
    expect(el).not.toBeNull();
    expect(el.textContent).toContain('Sync failed');
    expect(el.style.backgroundColor).toContain('dc2626');
  });

  it('accepts an onRetry callback that fires on click', () => {
    const spy = vi.fn();
    banner.showSyncFailed(spy);
    const el = getBannerEl();
    el.click();
    expect(spy).toHaveBeenCalledOnce();
  });
});

// ─── hide ─────────────────────────────────────────────────────────────────────

describe('test_banner_hide', () => {
  it('removes the banner element', () => {
    banner.showReconnecting();
    expect(getBannerEl()).not.toBeNull();
    banner.hide();
    expect(getBannerEl()).toBeNull();
  });

  it('does nothing if banner is already hidden', () => {
    expect(() => banner.hide()).not.toThrow();
  });
});

// ─── only one banner at a time ────────────────────────────────────────────────

describe('test_banner_singleton', () => {
  it('replaces existing banner when showing a different state', () => {
    banner.showReconnecting();
    banner.showOffline();
    const banners = document.querySelectorAll('#connection-banner');
    expect(banners.length).toBe(1);
    expect(banners[0].textContent).toContain('Playing offline');
  });
});
