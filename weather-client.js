/**
 * 通用天气预报客户端 - 使用 MCP 天气服务器
 * 
 * 此脚本可以获取任意城市的天气预报数据
 * 用法: node weather-client.js <城市名称> <国家代码> <天数>
 * 例如: node weather-client.js Beijing cn 3
 */

import fetch from 'node-fetch';
import config from './config.js';

/**
 * 模拟 MCP 工具函数
 * 在实际的 MCP 客户端中，此函数由 MCP 框架提供
 */
async function use_mcp_tool(params) {
  const { server_name, tool_name, arguments: args } = params;
  
  // 从配置中获取主机和端口
  const host = config.host || 'localhost';
  const port = config.port || 3031;
  
  // 对于 SSE 模式，我们需要向服务器发送 HTTP 请求
  const response = await fetch(`http://${host}:${port}/mcp`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      type: 'tool',
      tool: tool_name,
      params: args
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP 错误! 状态码: ${response.status}`);
  }
  
  return await response.json();
}

/**
 * 获取天气预报的主函数
 */
async function getWeatherForecast(city, country, days) {
  try {
    console.log(`正在获取 ${city}, ${country} 未来 ${days} 天的天气预报...\n`);
    
    // 调用 MCP 工具获取天气预报
    const result = await use_mcp_tool({
      server_name: "weather-server",
      tool_name: "get_forecast",
      arguments: {
        city: `${city},${country}`,
        days: parseInt(days)
      }
    });
    
    // 检查结果状态
    if (result.status !== 'success' || !result.data) {
      console.error('获取天气数据失败:', result.error || '未知错误');
      return;
    }
    
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
    console.log('通过 MCP 天气服务器获取');
    
  } catch (error) {
    console.error('获取天气数据时出错:', error.message);
  }
}

// 从命令行参数获取城市、国家和天数
const args = process.argv.slice(2);
if (args.length < 2) {
  console.log('用法: node weather-client.js <城市名称> <国家代码> <天数>');
  console.log('例如: node weather-client.js Beijing cn 3');
  process.exit(1);
}

const city = args[0];
const country = args[1];
const days = args[2] || 3; // 默认3天

// 运行函数
getWeatherForecast(city, country, days);
