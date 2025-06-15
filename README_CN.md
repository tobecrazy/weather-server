# Weather Server MCP

![天气预报示例](https://private-us-east-1.manuscdn.com/sessionFile/RPohfjjIxIuy6mRgt40m4T/sandbox/Jtrwv0tQTbSbLsx6QI9EX5-images_1749976315104_na1fn_L2hvbWUvdWJ1bnR1L3JlYWRtZV9pbWFnZXMvd2VhdGhlcl9mb3JlY2FzdF9leGFtcGxl.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvUlBvaGZqakl4SXV5Nm1SZ3Q0MG00VC9zYW5kYm94L0p0cnd2MHRRVGJTYkxzeDZRSTlFWDUtaW1hZ2VzXzE3NDk5NzYzMTUxMDRfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwzSmxZV1J0WlY5cGJXRm5aWE12ZDJWaGRHaGxjbDltYjNKbFkyRnpkRjlsZUdGdGNHeGwucG5nIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzY3MjI1NjAwfX19XX0_&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=IdT10SKpKBzDGZ~qs-5OEwyS7nkNfExTaLaTEZ2u77C62bgz8ieLjDl9YpiYa6fkkcjDT9XYvX-p72102hKh94YRXXErCxPvC4gN~V~aSEPStGWzSwd5RF6-PjEhvy8Szs~aNE0-PAu2iLZoV~uEJSxhL1NZSBnttx40TcCj~IuwQ1abJaS09cb72SneM~E9be4~EK2GXcxmZXDB0-7tnc6WOiiO8noo6Zv4sG3w70hJ1o7OMurQLsDEWtxfYhoSILyjE10aeMXxR~pdm3pcpt4QXoAhuXPxhfJHuEj8not2S78pHB52tsZYNCyxX6Pjym8YRes19jjgSFPg3ks3RQ__)

一个模型上下文协议（MCP）服务器，通过OpenWeatherMap API提供天气信息。本项目旨在演示如何创建和使用MCP服务器，以通过实时天气数据扩展AI助手的能力。

## 项目概述

本项目实现了一个本地MCP服务器，使用FastMCP框架，允许AI助手访问全球任何城市的当前天气状况和天气预报。该服务器连接到OpenWeatherMap API，并通过标准化的MCP接口提供这些数据。

![MCP架构](https://private-us-east-1.manuscdn.com/sessionFile/RPohfjjIxIuy6mRgt40m4T/sandbox/Jtrwv0tQTbSbLsx6QI9EX5-images_1749976315105_na1fn_L2hvbWUvdWJ1bnR1L3JlYWRtZV9pbWFnZXMvbWNwX2FyY2hpdGVjdHVyZQ.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvUlBvaGZqakl4SXV5Nm1SZ3Q0MG00VC9zYW5kYm94L0p0cnd2MHRRVGJTYkxzeDZRSTlFWDUtaW1hZ2VzXzE3NDk5NzYzMTUxMDVfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwzSmxZV1J0WlY5cGJXRm5aWE12YldOd1gyRnlZMmhwZEdWamRIVnlaUS5wbmciLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjcyMjU2MDB9fX1dfQ__&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=o-IfmPbtYHTnlHlN2SL7Nx6ORD8cQUfHJJevezSO9RAhlRpkNT-bBLIDd8AMsVbsUdSEH6OYZ9Rm4tAHniOz2luw6TY8oVDBNBlW0Hpoe6ul8zEI6Flt5yi0jB7Tbl0j2IHhMCTZoE13XFvhk0erasgW42d7~jQLyBFO6l88xmbASthsOl~vTT44X8Q1kL-kmv5-Z-lOtXuJOutqyxuwuB6avDkcWP8V-QUK~ojrF9EbgStF7RjLE1-T5CUrslsmLObLTX59h2XyiPDgEF76EHivcQ-oc5osmZ2AhbwgWzr7nZdKUmhCrttwasvdiQK7ov16qIsFA0WtLHhlivU4tw__)

### 主要特性

*   **当前天气**：获取任何城市的实时天气数据
*   **天气预报**：获取长达15天的天气预报
*   **温度数据**：包括当前、最低和最高温度
*   **多种传输模式**：支持stdio和HTTP流模式
*   **OAuth 2.0 认证**：HTTP模式下支持安全的Bearer Token认证
*   **Docker支持**：通过Docker和Docker Compose轻松部署
*   **全面的错误处理**：健壮的错误处理和日志记录

## 项目结构

```
weather-server/
├── .dockerignore              # Docker构建排除文件
├── .env.example               # 环境变量示例文件
├── .gitignore                 # Git排除文件
├── README.md                  # 本文件（根文档）
│
└── weather_mcp/               # 主MCP服务器实现
    ├── main.py                # 使用FastMCP的服务器入口点
    ├── plugins/               # MCP插件目录
    │   └── weather.py         # 天气工具实现
    ├── config.yaml.example    # 配置文件示例
    ├── .env.example           # 环境变量示例
    ├── requirements.txt       # Python依赖
    ├── Dockerfile             # Docker容器定义
    ├── docker-compose.yml     # Docker Compose配置
    ├── run_server.sh          # 运行服务器的脚本
    └── README.md              # MCP服务器的详细文档
```

## 环境要求

*   Python 3.8 或更高版本
*   OpenWeatherMap API 密钥（在[OpenWeatherMap](https://openweathermap.org/)注册获取）

## 快速开始

1.  **克隆仓库**:
    
    ```bash
git clone https://github.com/yourusername/weather-server.git
cd weather-server/weather_mcp
    ```
    
2.  **安装依赖**:
    
    ```bash
pip install -r requirements.txt
    ```
    
3.  **配置服务器**:
    
    复制 `config.yaml.example` 为 `config.yaml` 并编辑，添加您的OpenWeatherMap API密钥：
    
    ```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml 并添加您的 OpenWeatherMap API 密钥
    ```
    
    或者使用环境变量：
    
    ```bash
cp .env.example .env
# 编辑 .env 并添加您的 OpenWeatherMap API 密钥
    ```

### 使用提供的脚本运行

```bash
# 使脚本可执行
chmod +x run_server.sh

# 在stdio模式下运行（默认）
./run_server.sh

# 在HTTP流模式下运行
./run_server.sh -m sse

# 启用认证运行
./run_server.sh -m sse -a -g
```

### 使用Docker部署

**使用Docker Compose**:

```bash
docker-compose up -d
```

**或者直接构建并运行Docker镜像**:

```bash
docker build -t weather-mcp-server .
docker run -d -p 3399:3399 -e OPENWEATHERMAP_API_KEY=your_api_key_here weather-mcp-server
```

## 认证

服务器支持OAuth 2.0 Bearer Token认证，适用于HTTP流模式（SSE和streamable-http）。这为您的MCP服务器提供了安全的访问控制。

认证可以通过以下几种方式启用：

1.  **使用环境变量**:
    
    ```bash
export AUTH_ENABLED=true
export AUTH_SECRET_KEY=your_secret_key_here
    ```
    
2.  **使用.env文件**:
    
    ```
AUTH_ENABLED=true
AUTH_SECRET_KEY=your_secret_key_here
    ```
    
3.  **使用config.yaml**:
    
    ```yaml
auth:
  enabled: true
  secret_key: your_secret_key_here
    ```
    
4.  **使用命令行选项**（通过`run_server.sh`）:
    
    ```bash
./run_server.sh -m sse -a -s your_secret_key_here
    ```

### 生成Token

项目包含一个Token生成工具：

```bash
# 使用密钥生成Token
python weather_mcp/utils/generate_token.py --secret your_secret_key_here

# 生成带有特定过期时间（秒）的Token
python weather_mcp/utils/generate_token.py --secret your_secret_key_here --expiry 3600

# 为特定用户生成Token
python weather_mcp/utils/generate_token.py --secret your_secret_key_here --user "user123"
```

您也可以在启动服务器时生成Token：

```bash
./run_server.sh -m sse -a -g
```

### 客户端使用Token

客户端必须在`Authorization`头中包含Bearer Token：

```
Authorization: Bearer your_token_here
```

## 与AI助手集成

该MCP服务器可以与支持模型上下文协议的AI助手集成。连接后，助手可以使用天气工具获取天气信息。

**示例请求**:

```json
{
  "tool": "weather.get_weather",
  "args": {
    "city": "London,uk",
    "days": 0
  }
}
```

**示例响应**:

```json
{
  "city": "London,uk",
  "date": "2025-05-12",
  "temperature_C": 15.8,
  "min_temperature_C": 12.3,
  "max_temperature_C": 18.2,
  "weather": "scattered clouds"
}
```

## 传输模式

服务器支持以下传输模式：

1.  **stdio**：标准输入/输出模式（适用于CLI使用）
2.  **streamable-http**：支持流的HTTP服务器模式（默认且推荐用于Web客户端）
3.  **sse**：旧版HTTP流模式（用于向后兼容）

## Docker支持

项目包含Docker支持，便于部署：

*   **Dockerfile**：定义容器镜像
*   **docker-compose.yml**：通过环境变量简化部署
*   **.dockerignore**：优化Docker构建

## 更多信息

有关MCP服务器实现、API详细信息和高级用法的更多信息，请参阅[weather_mcp/README.md](weather_mcp/README.md)文件。

## 许可证

本项目采用MIT许可证 - 详情请参阅LICENSE文件。

## 致谢

*   [FastMCP](https://github.com/google/fastmcp) - 用于构建MCP服务器的Python框架
*   [OpenWeatherMap](https://openweathermap.org/) - 天气数据提供商


