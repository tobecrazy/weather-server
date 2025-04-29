/**
 * Simple test client for the Weather MCP Server
 * 
 * This script demonstrates how to send a request to the MCP server
 * and receive a response. It uses the stdio transport mode.
 * 
 * Usage:
 *   node test-client.js
 */

// Sample request to get weather forecast for Paris, France for 3 days
const request = {
  type: 'tool',
  tool: 'get_forecast',
  params: {
    city: 'Paris,fr',
    days: 3
  }
};

// Send the request to the server
console.log('Sending request to MCP server:');
console.log(JSON.stringify(request, null, 2));
console.log('\n---\n');

// Write the request to stdout
process.stdout.write(JSON.stringify(request) + '\n');

// Listen for response from the server
process.stdin.on('data', (data) => {
  try {
    // Parse the response
    const response = JSON.parse(data.toString().trim());
    
    console.log('Received response from MCP server:');
    console.log(JSON.stringify(response, null, 2));
    
    // Exit after receiving the response
    process.exit(0);
  } catch (error) {
    console.error('Error parsing response:', error);
    process.exit(1);
  }
});

// Handle errors
process.stdin.on('error', (error) => {
  console.error('Error reading from stdin:', error);
  process.exit(1);
});

console.log('Waiting for response...');
