import { createStdioTransport } from './transport/stdio.js';
import { createSseTransport } from './transport/sse.js';
import { getWeather } from './weather.js';
import config from './config.js';

/**
 * Simple MCP Server implementation
 */
class SimpleMcpServer {
  constructor(options) {
    this.name = options.name;
    this.description = options.description;
    this.transport = options.transport;
    this.tools = new Map();
    
    // Set up message handler
    this.transport.on('message', this.handleMessage.bind(this));
  }
  
  /**
   * Register a tool with the server
   */
  registerTool(toolDef) {
    this.tools.set(toolDef.name, toolDef);
    console.log(`Registered tool: ${toolDef.name}`);
  }
  
  /**
   * Start the server
   */
  async start() {
    console.log(`Starting ${this.name}...`);
    if (this.transport.start) {
      await this.transport.start();
    }
    return true;
  }
  
  /**
   * Stop the server
   */
  async stop() {
    console.log(`Stopping ${this.name}...`);
    if (this.transport.stop) {
      await this.transport.stop();
    }
    return true;
  }
  
  /**
   * Handle incoming messages
   */
  async handleMessage(message, respond) {
    try {
      // Parse the message
      const { type, tool, params } = message;
      
      // Handle tool execution
      if (type === 'tool' && tool) {
        const toolDef = this.tools.get(tool);
        
        if (!toolDef) {
          return respond({
            status: 'error',
            error: `Tool not found: ${tool}`
          });
        }
        
        try {
          const result = await toolDef.handler(params || {});
          return respond(result);
        } catch (error) {
          return respond({
            status: 'error',
            error: error.message
          });
        }
      }
      
      // Handle unknown message types
      return respond({
        status: 'error',
        error: `Unknown message type: ${type}`
      });
    } catch (error) {
      console.error('Error handling message:', error);
      return respond({
        status: 'error',
        error: 'Internal server error'
      });
    }
  }
}

/**
 * Initialize and start the MCP server
 */
async function startServer() {
  try {
    let transport;
    
    // Select transport based on configuration
    if (config.mode === 'sse') {
      try {
        transport = createSseTransport();
      } catch (error) {
        console.error('Failed to create SSE transport:', error);
        console.log('Falling back to stdio transport...');
        transport = createStdioTransport();
      }
    } else {
      transport = createStdioTransport();
    }
    
    // Create MCP server with the selected transport
    const server = new SimpleMcpServer({
      transport,
      name: 'weather-server',
      description: 'OpenWeatherMap API MCP Server'
    });
    
    // Register the getWeather tool
    server.registerTool({
      name: 'get_forecast',
      description: 'Get weather forecast for a city for a specified number of days',
      parameters: {
        type: 'object',
        properties: {
          city: {
            type: 'string',
            description: 'City name with optional country code (e.g., "Paris,fr" or "Tokyo,jp")'
          },
          days: {
            type: 'integer',
            description: 'Number of days to forecast (default: 1, max: 5)',
            default: 1,
            minimum: 1,
            maximum: 5
          }
        },
        required: ['city']
      },
      handler: async ({ city, days = 1 }) => {
        try {
          console.log(`Fetching weather for ${city} for ${days} day(s)`);
          
          // Validate API key
          if (!config.apiKey) {
            throw new Error('OpenWeatherMap API key is not configured');
          }
          
          // Get weather data
          const weatherData = await getWeather(city, days);
          
          return {
            status: 'success',
            data: weatherData
          };
        } catch (error) {
          console.error('Error in get_forecast handler:', error);
          
          return {
            status: 'error',
            error: error.message
          };
        }
      }
    });
    
    // Log server information
    console.log(`Starting weather-server in ${config.mode} mode`);
    
    if (!config.apiKey) {
      console.warn('WARNING: OpenWeatherMap API key is not set. API requests will fail.');
      console.warn('Set the OPENWEATHERMAP_API_KEY environment variable or add it to config.json');
    }
    
    // Start the server
    await server.start();
    
    console.log('Weather MCP server started successfully');
    
    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      console.log('Shutting down weather MCP server...');
      await server.stop();
      process.exit(0);
    });
    
    process.on('SIGTERM', async () => {
      console.log('Shutting down weather MCP server...');
      await server.stop();
      process.exit(0);
    });
  } catch (error) {
    console.error('Failed to start weather MCP server:', error);
    process.exit(1);
  }
}

// Start the server
startServer();
