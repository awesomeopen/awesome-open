// Calls one chrome-devtools-mcp tool on a Chrome started with --remote-debugging-port
// and prints its text result. V2's agent uses it to call the page's WebMCP tools.
//   node scripts/devtools-mcp.mjs <port> list_webmcp_tools
//   node scripts/devtools-mcp.mjs <port> execute_webmcp_tool '{"toolName":"list_find","input":"{\"query\":\"video editor\"}"}'
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { ROOT } from './lib.mjs';

const [port, tool, json = '{}'] = process.argv.slice(2);
const server = spawn('node', [join(ROOT, 'node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js'),
  `--browser-url=http://127.0.0.1:${port}`, '--categoryExperimentalWebmcp=true', '--no-usage-statistics', '--no-performance-crux'],
  { stdio: ['pipe', 'pipe', 'ignore'] });
let buffer = '', next = 0;
const waiting = new Map();
server.stdout.on('data', chunk => {
  buffer += chunk;
  for (let i; (i = buffer.indexOf('\n')) >= 0; buffer = buffer.slice(i + 1)) {
    const message = JSON.parse(buffer.slice(0, i));
    waiting.get(message.id)?.(message);
  }
});
const call = (method, params) => new Promise(resolve => {
  const id = ++next; waiting.set(id, resolve);
  server.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
});
const text = reply => (reply.result?.content || []).map(c => c.text).join('\n') || JSON.stringify(reply.error);

await call('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'launch-video', version: '1' } });
server.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
// WebMCP tools act on a page; use the one showing the local preview.
const pages = text(await call('tools/call', { name: 'list_pages', arguments: {} }));
const pageId = Number((pages.match(/^(\d+):.*127\.0\.0\.1/m) || [])[1]);
console.log(text(await call('tools/call', { name: tool, arguments: { pageId, ...JSON.parse(json) } })));
server.kill();
