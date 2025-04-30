import http from 'http';
import { EventEmitter } from 'events';
import config from '../config.js';

/**
 * Custom SSE transport for MCP server
 * Implements the necessary interface to work with MCP Server
 */
export class SseServerTransport extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.port = options.port || config.port;
    this.host = options.host || config.host;
    this.server = null;
    this.clients = new Set();
    this.nextClientId = 1;
  }
  
  /**
   * Start the SSE server
   * @param {number[]} retryPorts - Optional array of ports to try if the initial port is in use
   */
  async start(retryPorts = []) {
    return new Promise((resolve, reject) => {
      try {
        this.server = http.createServer(this._handleRequest.bind(this));
        
        this.server.listen(this.port, this.host, () => {
          console.log(`SSE transport server listening on http://${this.host}:${this.port}`);
          resolve();
        });
        
        this.server.on('error', (err) => {
          if (err.code === 'EADDRINUSE' && retryPorts.length > 0) {
            // Try the next port in the retry list
            console.log(`Port ${this.port} is in use, trying port ${retryPorts[0]}...`);
            this.port = retryPorts[0];
            this.start(retryPorts.slice(1))
              .then(resolve)
              .catch(reject);
          } else {
            console.error('SSE server error:', err);
            reject(err);
          }
        });
      } catch (error) {
        console.error('Failed to start SSE server:', error);
        reject(error);
      }
    });
  }
  
  /**
   * Stop the SSE server
   */
  async stop() {
    if (this.server) {
      // Close all client connections
      for (const client of this.clients) {
        client.res.end();
      }
      this.clients.clear();
      
      // Close the server
      return new Promise((resolve) => {
        this.server.close(() => {
          console.log('SSE transport server stopped');
          this.server = null;
          resolve();
        });
      });
    }
    return Promise.resolve();
  }
  
  /**
   * Send a message to all connected clients
   * @param {Object} message - Message to send
   */
  send(message) {
    const data = JSON.stringify(message);
    
    for (const client of this.clients) {
      client.res.write(`data: ${data}\n\n`);
    }
  }
  
  /**
   * Handle incoming HTTP requests
   * @param {http.IncomingMessage} req - HTTP request
   * @param {http.ServerResponse} res - HTTP response
   */
  _handleRequest(req, res) {
    const { url, method } = req;
    
    // Handle SSE connections
    if (url === '/events' && method === 'GET') {
      this._handleSseConnection(req, res);
      return;
    }
    
    // Handle MCP requests
    if (url === '/mcp' && method === 'POST') {
      this._handleMcpRequest(req, res);
      return;
    }
    
    // Default response for other routes
    res.writeHead(404);
    res.end('Not Found');
  }
  
  /**
   * Handle SSE connection setup
   * @param {http.IncomingMessage} req - HTTP request
   * @param {http.ServerResponse} res - HTTP response
   */
  _handleSseConnection(req, res) {
    // Set headers for SSE
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });
    
    // Send initial connection message
    res.write('event: connected\ndata: {"status":"connected"}\n\n');
    
    // Create client object
    const clientId = this.nextClientId++;
    const client = { id: clientId, req, res };
    
    // Add to clients set
    this.clients.add(client);
    console.log(`SSE client connected: ${clientId}`);
    
    // Handle client disconnect
    req.on('close', () => {
      this.clients.delete(client);
      console.log(`SSE client disconnected: ${clientId}`);
    });
  }
  
  /**
   * Handle MCP request
   * @param {http.IncomingMessage} req - HTTP request
   * @param {http.ServerResponse} res - HTTP response
   */
  _handleMcpRequest(req, res) {
    let body = '';
    
    req.on('data', (chunk) => {
      body += chunk.toString();
    });
    
    req.on('end', () => {
      try {
        const message = JSON.parse(body);
        
        // Set CORS headers
        res.writeHead(200, {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        });
        
        // Emit the message event for the MCP server to handle
        this.emit('message', message, (response) => {
          // Send response to the HTTP client
          res.end(JSON.stringify(response));
          
          // Also broadcast the response to all SSE clients
          this.send(response);
        });
      } catch (error) {
        console.error('Error processing MCP request:', error);
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid request' }));
      }
    });
  }
}

/**
 * Create and configure an SSE transport for MCP server
 * @param {Object} options - Configuration options
 * @returns {SseServerTransport} Configured SSE transport
 */
export function createSseTransport(options = {}) {
  console.log('Initializing MCP server with SSE transport');
  
  const transport = new SseServerTransport(options);
  
  // Define retry ports - try a few ports above the configured one
  const basePort = transport.port;
  transport.retryPorts = [
    basePort + 1,
    basePort + 2,
    basePort + 3,
    basePort + 4
  ];
  
  // Add a custom start method that uses retry ports
  const originalStart = transport.start;
  transport.start = async function() {
    try {
      // Call the original start method with retry ports
      return await originalStart.call(this, this.retryPorts);
    } catch (error) {
      if (error.code === 'EADDRINUSE') {
        console.error(`All ports (${basePort}-${basePort + 4}) are already in use.`);
        console.error('Please try one of the following:');
        console.error(`1. Set a different port in .env or config.json`);
        console.error(`2. Run with a different port: PORT=${basePort + 10} MCP_MODE=sse node index.js`);
        console.error(`3. Use stdio mode instead: MCP_MODE=stdio node index.js`);
        console.error(`4. Stop the processes using these ports and try again`);
        console.error(`   You can find processes using these ports with: lsof -i :${basePort}`);
      }
      throw error;
    }
  };
  
  return transport;
}

export default {
  SseServerTransport,
  createSseTransport
};
