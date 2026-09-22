/**
 * NetworkError — custom error class for network/timeout failures.
 * Screens use `instanceof NetworkError` to trigger offline failover.
 */

export class NetworkError extends Error {
  constructor(reason) {
    super(reason);
    this.name = 'NetworkError';
    this.reason = reason;
  }
}
