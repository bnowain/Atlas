/**
 * Build a URL to a spoke application using the current browser hostname.
 * When accessed via Tailscale (100.x.x.x or *.ts.net), links to spoke UIs
 * will automatically use the same hostname instead of hardcoded localhost.
 */
export function spokeUrl(port: number, path = ''): string {
  return `http://${window.location.hostname}:${port}${path}`
}
