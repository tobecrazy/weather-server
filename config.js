import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

// Load environment variables from .env file
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Default configuration
const defaultConfig = {
  apiKey: process.env.OPENWEATHERMAP_API_KEY || '',
  mode: process.env.MCP_MODE || 'stdio', // 'stdio' or 'sse'
  port: process.env.PORT || 3031, // Port for SSE server
  host: process.env.HOST || 'localhost' // Host for SSE server
};

// Try to load config from file if it exists
let fileConfig = {};
const configPath = join(__dirname, 'config.json');

try {
  if (fs.existsSync(configPath)) {
    const configFile = fs.readFileSync(configPath, 'utf8');
    fileConfig = JSON.parse(configFile);
    console.log('Loaded configuration from config.json');
  }
} catch (error) {
  console.error('Error loading config file:', error.message);
}

// Merge configurations with environment variables taking precedence
const config = {
  ...defaultConfig,
  ...fileConfig,
  // Override with environment variables if they exist
  apiKey: process.env.OPENWEATHERMAP_API_KEY || fileConfig.apiKey || defaultConfig.apiKey,
  mode: process.env.MCP_MODE || fileConfig.mode || defaultConfig.mode,
  port: process.env.PORT || fileConfig.port || defaultConfig.port,
  host: process.env.HOST || fileConfig.host || defaultConfig.host
};

// Validate required configuration
if (!config.apiKey) {
  console.warn('Warning: OpenWeatherMap API key is not set. Set OPENWEATHERMAP_API_KEY environment variable or add it to config.json');
}

export default config;
