# server.py
from fastmcp import FastMCP
import sys
import logging

import json
import re
import asyncio
import websockets
from websockets import ConnectionClosed
from typing import Dict, Set, Any

mac_client_map: Dict[str, Dict] = {}
# 核心配置常量
MAX_CONNECTIONS_PER_MAC = 5  # 单个MAC最大连接数
MAC_PATTERN = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')  # MAC地址校验
WS_HOST = "0.0.0.0"
WS_PORT = 9527
WS_PING_INTERVAL = 30  # 心跳间隔（秒）
WS_PING_TIMEOUT = 10   # 心跳超时（秒）
MAX_MSG_SIZE = 1 * 1024 * 1024  # 最大消息大小（1MB）

# 配置logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test')

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Create an MCP server
mcp = FastMCP("query_products")

# Add an addition tool
@mcp.tool()
def queryProducts(device_id:str) -> dict:
    """ 在咨询有哪些产品时，请始终使用此工具来查询产品的相关信息。
        :param device_id: 设备ID"""
    # logger.info(f"rrrrr{device_id}")
    logger.info(f"queryProducts device_id: {device_id}")
    result = [
              {"name":"糖果TENS 2S","special" :"可调节输出模式跟强度"},
              {"name": "蝴蝶TENS", "special": "有26个模式,他的不同在于他除了缓解疼痛跟肌肉训练还有MASSAGE按摩模式和女性痛经模式,更专业适合重度患者使用,设备有三个按钮,左右两个按键可以调节输出强度,中间按钮长按开关机,短按切换模式"},
              {"name": "腰带1", "special": "佩戴方便，使用效果显著"}
            ]
    return {"success": True, "result": result}


@mcp.tool()
def queryShop(local_address:str) -> dict:
    """ 在想要购买产品时，请始终使用此工具来查询该城市的门店信息"""
    logger.info(f"queryShop local_address: {local_address}")
    logger.info(f"queryShop local_address: {local_address}")
    # logger.info(f"rrrrr{parameter}")
    return {"success": True, "result": "重庆市渝北区xxx街xxx号"}
@mcp.tool()
async def controlProduct(device_id:str,strength:int) -> dict:
    """ 在想要控制产品时，请始终使用此工具来控制产品的状态
    :param device_id: 设备ID"""
    logger.info(f"controlProduct 设备ID: {device_id}")
    obj = mac_client_map[device_id]
    websocket = obj['websocket']
    if websocket:
        try:
          result = {"success": True, "result": {strength},"message": "操作成功,强度已经调整成:{strength}"}
          await websocket.send(json.dumps(result))
          return result
        except Exception as e:
          logger.error(f"向设备 {device_id} 发送消息失败: {str(e)}")
    else:
        return {"success": False, "result": "设备未连接"}

async def register_client(mac: str, websocket: Any):
    """注册客户端连接到mac地址映射"""
    if mac not in mac_client_map:
      obj = {"websocket":websocket}
      mac_client_map[mac] = obj
    logger.info(f"客户端 [{mac}] 已连接，当前连接数: {len(mac_client_map)}")

async def unregister_client(mac: str, websocket: Any):
    """注销客户端连接"""
    if mac in mac_client_map:
        # mac_client_map[mac].discard(websocket)
        # 如果该mac下无连接，清理键
        if not mac_client_map[mac]:
            del mac_client_map[mac]
        logger.info(f"客户端 [{mac}] 已断开，剩余连接数: {len(mac_client_map)}")

async def handle_client(websocket: Any):
    """处理单个客户端连接"""
    # 1. 从请求头获取mac地址
    mac = websocket.request.headers["Device-Id"]
    if not mac:
        # 无mac地址，拒绝连接
        await websocket.close(code=1008, reason="Missing MAC address in headers")
        logger.info("拒绝无MAC地址的客户端连接")
        return

    try:
        # 2. 注册客户端
        await register_client(mac, websocket)

        # 3. 循环接收客户端消息
        async for message in websocket:
            logger.info(f"收到 [{mac}] 消息: {message}")
            
            # 示例1: 回复当前客户端
            # await websocket.send(f"服务端已收到 [{mac}] 的消息: {message}")

    except ConnectionClosedError:
        logger.info(f"客户端 [{mac}] 异常断开连接")
    except ConnectionClosedOK:
        logger.info(f"客户端 [{mac}] 正常断开连接")
    finally:
        # 4. 注销客户端
        await unregister_client(mac, websocket)
async def startWsServer():
    """启动WebSocket服务端（适配v13.0+最新API）"""
    server = None
    try:
        # 新版核心变更：使用 websockets.serve 替代 websockets.server.serve
        server = await websockets.serve(
            handler=handle_client,
            host=WS_HOST,
            port=WS_PORT,
            ping_interval=WS_PING_INTERVAL,
            ping_timeout=WS_PING_TIMEOUT,
            max_size=MAX_MSG_SIZE
        )
        logger.info(f"WebSocket服务端已启动 → ws://{WS_HOST}:{WS_PORT}")
        
        # 保持服务运行（新版推荐方式）
        await server.wait_closed()

    except OSError as e:
        logger.error(f"服务启动失败: {str(e)} (端口 {WS_PORT} 可能被占用)")
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭服务...")
    finally:
        # 优雅关闭服务和所有连接
        if server:
            server.close()
            await server.wait_closed()
        
        # 清理所有客户端连接
        for mac, clients in list(mac_client_map.items()):
            for client in clients:
                try:
                    await client[''].close(code=1001, reason=b"Server shutdown")
                except Exception:
                    pass
            del mac_client_map[mac]
        
        logger.info("服务端已完全停止，所有资源已清理")
# @mcp.tool()
# def currentDevice() -> dict:
#     """ 
#     在想要控制产品时，传入{{device_id}}设备ID，获取当前连接的产品信息
#     """
#     # logger.info(f"currentDevice device_id: {device_id}")
#     # logger.info(f"rrrrrcurrentDevice: {device_id}")
#     logger.info(f"controlProduct device_id: {{device_id}}")
#     # logger.info(f"rrrrr2222currentDevice: {{device_id}}")
#     return {"success": True, "result": {
#       "sn": "123456",
#       "device_name": "TENS",
#     }}

# 定义一个异步函数来运行MCP服务器
async def run_mcp_server():
    """运行MCP服务器"""
    import threading
    
    # 创建一个线程来运行mcp.run，因为它是阻塞调用
    def mcp_thread():
        try:
            mcp.run(transport="stdio")
        except KeyboardInterrupt:
            pass
    
    # 启动MCP服务器线程
    thread = threading.Thread(target=mcp_thread, daemon=True)
    thread.start()
    
    # 返回线程对象，以便可以监控它
    return thread

# Start the server
if __name__ == "__main__":
    # 创建事件循环
    loop = asyncio.get_event_loop()
    
    # 运行服务端
    try:
        # 在事件循环中运行所有服务器
        loop.run_until_complete(asyncio.gather(
            run_mcp_server(),  # 运行MCP服务器
            startWsServer()     # 运行WebSocket服务器
        ))
    except KeyboardInterrupt:
        logger.info("\n服务端已停止")
    finally:
        # 确保事件循环被正确关闭
        loop.close()
