import { EventEmitter } from 'events';
import readline from 'readline';

/**
 * Simple stdio transport for MCP server
 * Implements a basic transport that reads from stdin and writes to stdout
 */
class StdioTransport extends EventEmitter {
  constructor() {
    super();
    
    // Create readline interface
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false
    });
    
    // Set up line handler
    this.rl.on('line', this._handleLine.bind(this));
    
    console.log('Stdio transport initialized');
  }
  
  /**
   * Handle incoming line from stdin
   * @param {string} line - Line from stdin
   */
  _handleLine(line) {
    try {
      // Parse the line as JSON
      const message = JSON.parse(line);
      
      // Emit message event
      this.emit('message', message, (response) => {
        // Write response to stdout
        console.log(JSON.stringify(response));
      });
    } catch (error) {
      console.error('Error parsing message:', error);
      
      // Send error response
      console.log(JSON.stringify({
        status: 'error',
        error: 'Invalid JSON message'
      }));
    }
  }
  
  /**
   * Send a message to stdout
   * @param {Object} message - Message to send
   */
  send(message) {
    console.log(JSON.stringify(message));
  }
}

/**
 * Create and configure a stdio transport for MCP server
 * @returns {StdioTransport} Configured stdio transport
 */
export function createStdioTransport() {
  console.log('Initializing MCP server with stdio transport');
  
  // Create stdio transport
  const transport = new StdioTransport();
  
  return transport;
}

export default {
  StdioTransport,
  createStdioTransport
};
