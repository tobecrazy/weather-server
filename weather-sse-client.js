/**
 * 使用 MCP 直接获取天气数据
 * 
 * 此脚本直接使用 MCP 工具获取天气数据，无需通过 SSE 事件流
 * 用法: node weather-sse-client.js <城市名称> <国家代码> <天数>
 * 例如: node weather-sse-client.js Beijing cn 3
 */

import fetch from 'node-fetch';
import config from './config.js';

// 从命令行参数获取城市、国家和天数
const args = process.argv.slice(2);
if (args.length < 2) {
  console.log('用法: node weather-sse-client.js <城市名称> <国家代码> <天数>');
  console.log('例如: node weather-sse-client.js Beijing cn 3');
  process.exit(1);
}

const city = args[0];
const country = args[1];
const days = args[2] || 3; // 默认3天

/**
 * 使用 MCP 获取天气数据
 */
async function getWeatherWithMcp() {
  try {
    // 从配置中获取主机和端口
    const host = config.host || 'localhost';
    const port = config.port || 3031;
    
    console.log(`正在连接到 MCP 服务器: http://${host}:${port}/mcp`);
    console.log(`获取 ${city}, ${country} 未来 ${days} 天的天气预报...\n`);
    
    // 发送天气请求
    const result = await sendWeatherRequest(host, port);
    
    // 显示天气数据
    if (result && result.status === 'success' && result.data) {
      displayWeatherData(result);
    } else {
      console.error('获取天气数据失败:', result ? result.error : '未知错误');
    }
  } catch (error) {
    console.error('获取天气数据时出错:', error.message);
  }
}

/**
 * 发送天气请求到 MCP 服务器
 */
async function sendWeatherRequest(host, port) {
  // 发送 HTTP 请求到 MCP 端点
  const response = await fetch(`http://${host}:${port}/mcp`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      type: 'tool',
      tool: 'get_forecast',
      params: {
        city: `${city},${country}`,
        days: parseInt(days)
      }
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP 错误! 状态码: ${response.status}`);
  }
  
  console.log('已发送天气请求，等待响应...');
  
  // 解析响应
  return await response.json();
}

/**
 * 显示天气数据
 */
function displayWeatherData(result) {
  // 提取天气数据
  const { location, forecast } = result.data;
  
  // 打印城市信息
  console.log(`\n===== ${location.name}, ${location.country} 天气预报 =====`);
  console.log(`经纬度: ${location.coordinates.lat}, ${location.coordinates.lon}`);
  console.log('===========================\n');
  
  // 打印每天的天气预报
  forecast.forEach((day) => {
    console.log(`【${day.date}】`);
    console.log(`天气状况: ${day.summary.weather.description}`);
    console.log(`平均温度: ${day.summary.avg_temp.toFixed(1)}°C`);
    console.log(`平均湿度: ${day.summary.avg_humidity.toFixed(1)}%`);
    
    // 获取当天的最高温和最低温
    const temps = day.hourly.map(hour => hour.temp);
    const maxTemp = Math.max(...temps).toFixed(1);
    const minTemp = Math.min(...temps).toFixed(1);
    
    console.log(`最高温度: ${maxTemp}°C`);
    console.log(`最低温度: ${minTemp}°C`);
    
    // 获取风速范围
    const windSpeeds = day.hourly.map(hour => hour.wind_speed);
    const maxWind = Math.max(...windSpeeds).toFixed(1);
    
    console.log(`最大风速: ${maxWind} m/s`);
    console.log('---------------------------\n');
  });
  
  console.log('数据来源: OpenWeatherMap API');
  console.log('通过 MCP 天气服务器获取 (SSE 模式)');
}

// 运行函数
getWeatherWithMcp();
