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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

mac_client_map: Dict[str, Dict] = {}
mac_user_map: Dict[str, Dict] = {}
# 核心配置常量
WS_HOST = "0.0.0.0"
WS_PORT = 9527
WS_PING_INTERVAL = 30  # 心跳间隔（秒）
WS_PING_TIMEOUT = 10   # 心跳超时（秒）
MAX_MSG_SIZE = 1 * 1024 * 1024  # 最大消息大小（1MB）

# HTTP服务配置
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 9528

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


@mcp.tool()
async def queryUserInfo(device_id:str) -> dict:
    """ 在想要用户信息时，请始终使用此工具来获取用户信息
    :param device_id: 设备ID"""
    if device_id in mac_user_map:
        user_info = mac_user_map[device_id].get('userInfo', {})
        return {"success": 0, "result": user_info}
    else:
        return {"success": -1, "result": {}, "message": "设备未连接或无用户信息"}

@mcp.tool()
async def queryDeviceState(device_id:str) -> dict:
    """ 在想要设备状态信息时，请始终使用此工具来获取设备状态信息
    :param device_id: 设备ID"""
    if device_id in mac_user_map:
        device_state = mac_user_map[device_id].get('deviceState', {})
        return {"success": 0, "result": device_state}
    else:
        return {"success": -1, "result": {}, "message": "设备未连接或无设备状态信息"}

@mcp.tool()
async def queryUseHistory(device_id:str) -> dict:
    """ 在想要使用历史时，请始终使用此工具来获取使用历史
    :param device_id: 设备ID"""
    if device_id in mac_user_map:
        use_history = mac_user_map[device_id].get('useHistory', [])
        return {"success": 0, "result": use_history}
    else:
        return {"success": -1, "result": [], "message": "设备未连接或无使用历史信息"}

# Add an addition tool
@mcp.tool()
def queryProducts(device_id:str) -> dict:
    """ 在咨询有哪些产品时，请始终使用此工具来查询产品的相关信息。
        :param device_id: 设备ID"""
    # logger.info(f"rrrrr{device_id}")
    logger.info(f"queryProducts device_id: {device_id}")
    result = [
      {
        "产品名称": "糖果TENS 2S",
        "模式数量": "12个",
        "控制方式": "选择部位",
        "产品特点": "1. 两套独立无线TENS单元，支持多设备同时连接，可同时对不同身体部位进行按摩\n2. 电极片：4片常规电极+2片小尺寸电极，自粘性好且易清洁\n3. 基于传统按摩+现代生物电技术，提供12种预设按摩模式\n4. 支持个性化定制按摩程序，满足不同用户需求\n5. 操作简便，一键启动，适合中老年用户使用\n6. FSA/HSA认证合格，适用于医疗报销范畴",
        "模式介绍": "模式1膝盖模式,缓解膝关节酸痛与僵硬，适合久走或运动后放松。模式2脚踝模式,放松脚踝疲劳，改善久站久走带来的不适。模式3腹部模式,舒缓腹部紧张，带来放松与舒适感。模式4腰部模式,缓解腰部酸痛与劳损，适合久坐人群。 模式5颈部模式,放松颈部肌肉，减轻低头导致的疲劳。 模式6肩部模式,缓解肩部僵硬与酸痛，提升活动舒适度。模式7腿部模式,缓解高强度训练后腿部疲劳，帮助肌肉放松恢复。 模式8全身模式,缓解高负荷运动后的全身疲劳，促进整体放松恢复。 模式9跑步恢复模式,缓解跑步后腿部紧绷与酸痛，帮助快速恢复状态。 模式10腹部恢复模式,放松腹部肌群，缓解训练后的紧张与疲劳。 模式11手臂模式,缓解手臂训练后酸胀感，帮助肌肉放松恢复。 模式12骑行腿部模式,缓解骑行后腿部疲劳，促进下肢放松与恢复。",
        "APP最大连接数量": "7个",
        "款式（推荐）": "1. 双主机款(推荐)\n2. 单主机款"
      },
      {
        "产品名称": "糖果TENS 2S Pro",
        "模式数量": "36个",
        "控制方式": "选择部位",
        "产品特点": "1. 两套独立无线TENS单元，支持多设备同时连接，可同时对不同身体部位进行按摩\n2. 极片：4片常规电极+2片小尺寸电极，自粘性好且易清洁\n3. 基于传统按摩+现代生物电技术，提供36种预设按摩模式\n4. 支持个性化定制按摩程序，满足不同用户需求\n5. 操作简便，一键启动\n6. FSA/HSA认证合格，适用于医疗报销范畴",
        "APP最大连接数量": "7个",
        "款式（推荐）": "1. 双主机款(推荐)\n2. 单主机款"
      },
      {
        "产品名称": "蝴蝶TENS 1S",
        "模式数量": "26个",
        "控制方式": "按摩方式选择",
        "产品特点": "1. FSA/HSA认证合格，适用于医疗报销范畴\n2. 标配两套独立TENS单元，可同时对不同身体部位进行按摩\n3. 26种按摩模式，模拟真人按摩手法\n4. 特别添加女性专用按摩模式\n5. 电极片：4片常规电极+2片小尺寸电极，自粘性好且易清洁\n6. 支持个性化定制按摩程序，满足不同用户需求",
        "APP最大连接数量": "2个",
        "款式（推荐）": "1. 双主机款(推荐)\n2. 单主机款"
      },
      {
        "产品名称": "腰带系列",
        "模式数量": "12个",
        "控制方式": "选择需训练的肌肉",
        "产品特点": "1. 无需更换导电硅胶垫：采用升级版无需更换的硅胶垫设计。\n2. 使用友好：亲肤材质硅胶垫，安全舒适。\n3. 多场景使用：可随时随地使用，如在放松、做家务或工作时使用，有效锻炼目标肌群。\n4. 强度可调：提供多级强度调节。\n5. 适用广泛：适用于男性和女性。\n6. 主打EMS模式，适用于肌肉健身人群，主要用于腰部和背部辅助训练。",
        "APP最大连接数量": "1个",
        "款式（推荐）": "1. 鲨鱼腰带\n2. 旋风腰带\n3. 拳王腰带"
      }
    ]
    return {"success": 0, "result": result}

@mcp.tool()
async def controlProductStrength(device_id:str,strength:int) -> dict:
    """ 在想要控制产品按摩强度时，请始终使用此工具来控制产品的强度
    :param device_id: 设备ID
    :param strength: 强度（增加为正数，减少为负数）"""
    logger.info(f"controlProductStrength 设备ID: {device_id}")
    if device_id not in mac_user_map or not mac_user_map[device_id].get('deviceState'):
        return {"success": -1, "result": {}, "message": "请先连接设备"}
    device_state = mac_user_map[device_id].get('deviceState', {})
    current_strength = device_state.get('strength', 0)
    max_strength = device_state.get('maxStrength', 100)  # 默认最大值为100
    new_strength = current_strength + strength
    # 确保新强度不超过maxStrength
    new_strength = min(new_strength, max_strength)
    # 同时确保新强度不低于0
    new_strength = max(new_strength, 0)
    return await sendto_client(device_id,{"type":"strength","strength": new_strength})

@mcp.tool()
async def controlProductMode(device_id:str,mode:int) -> dict:
    """ 在想要控制产品按摩模式时，请始终使用此工具来控制产品的模式
    :param device_id: 设备ID
    :param mode: 模式（取值为设备可用模式中的modeId）"""
    logger.info(f"controlProductMode 设备ID: {device_id}")
    if device_id not in mac_user_map or not mac_user_map[device_id].get('deviceState'):
        return {"success": -1, "result": {}, "message": "请先连接设备"}
    return await sendto_client(device_id,{"type":"mode","mode": mode})

@mcp.tool()
async def controlProductTime(device_id:str,time:int) -> dict:
    """ 在想要控制产品按摩时长时，请始终使用此工具来控制产品的按摩时长
    :param device_id: 设备ID
    :param time: 时长（根据设备状态中的useTime增加或减少，单位为分钟）"""
    logger.info(f"controlProductTime 设备ID: {device_id}")
    current_use_time = mac_user_map[device_id].get('deviceState', {}).get('useTime', 0)
    if device_id not in mac_user_map or not mac_user_map[device_id].get('deviceState'):
        return {"success": -1, "result": {}, "message": "请先连接设备"}
    return await sendto_client(device_id,{"type":"time","time": current_use_time + time})

@mcp.tool()
async def controlProductStartOrPause(device_id:str,startOrPause:int) -> dict:
    """ 在想要控制产品时暂停或者继续时，请始终使用此工具来控制产品的状态
    :param device_id: 设备ID
    :param startOrPause: 1 开始 0 暂停"""
    logger.info(f"controlProduct 设备ID: {device_id}")
    return await sendto_client(device_id,{"type":"status","status": startOrPause})

@mcp.tool()
async def setLastUsedSettings(device_id:str) -> dict:
    """ 在想要设置上一次的强度、模式、时长等时，请使用此工具
    :param device_id: 设备ID"""
    logger.info(f"setLastUsedSettings 设备ID: {device_id}")
    if device_id not in mac_user_map or not mac_user_map[device_id].get('deviceState'):
        return {"success": -1, "result": {}, "message": "请先连接设备"}
    use_history = mac_user_map[device_id].get('useHistory', [])
    if not use_history:
        return {"success": -1, "result": {}, "message": "无使用历史记录"}
    # 获取最新的一条历史记录
    last_record = use_history[-1]
    # 合并成一次发送，type定义为last_record
    await sendto_client(device_id,{"type":"last_record","data": last_record})
    return {"success": 0, "result": last_record, "message": "已设置为上一次的使用设置"}

@mcp.tool()
async def jumpPage(device_id:str,pageName:str) -> dict:
    """ 用户想要跳转页面或连接设备时，请始终使用此工具来控制app的页面跳转
    :param device_id: 设备ID
    :param pageName: 页面名"""
    pages = [
              {"name":"首页","path" :"home"},
              {"name":"回到首页","path" :"back_home"},
              {"name":"退出到桌面","path" :"exit_home"},
              {"name": "历史记录", "path": "history"},
              {"name": "购物", "path": "shop"},
              {"name": "个人中心", "path": "personalCenter"},
              {"name": "控制页面", "path": "control"},
              {"name": "连接设备", "path": "connect"},
              {"name": "设备连接", "path": "connect"},
            ]
    logger.error(f"pageName {pageName} ")
    if 'connect' in pageName.lower():
        pageName = '连接设备'
    path = None
    for page in pages:
        if page["name"] == pageName:
            path = page["path"]
    if path == None:
        return {"success": -1, "message": "页面不存在"}
    return await sendto_client(device_id,{"type":"jump","path": path})
@mcp.tool()
async def openConversation(device_id:str) -> dict:
    """ 在用户想要保持对话模式,开启聊天模式,切换聊天模式,开启语音模式时，请始终使用此工具来打开对话
    :param device_id: 设备ID"""
    logger.info(f"openConversation 设备ID: {device_id}")
    return await sendto_client(device_id,{"type":"open"})

@mcp.tool()
async def closeConversation(device_id:str) -> dict:
    """ 在用户想要关闭聊天、关闭本次对话或关闭语音聊天时，请始终使用此工具来关闭对话
    :param device_id: 设备ID"""
    logger.info(f"closeConversation 设备ID: {device_id}")
    return await sendto_client(device_id,{"type":"close"})
  
async def sendto_client(device_id: str,result: dict) -> dict:
    if device_id not in mac_client_map:
        logger.error(f"设备 {device_id} 未连接或不存在")
        return {"success": -1, "result": "设备未连接"}
    obj = mac_client_map[device_id]
    websocket = obj['websocket']
    if websocket:
        try:
          result = {"success": 0, "result": result,"message": f"操作成功"}
          logger.info(f"向设备 {device_id} 发送消息: {json.dumps(result)}")
          await websocket.send(json.dumps(result))
          return result
        except Exception as e:
          logger.error(f"向设备 {device_id} 发送消息失败: {str(e)}")
          return {"success": -5, "result": "发送消息失败"}
    else:
        return {"success": -1, "result": "设备连接已断开"}


async def register_client(mac: str, websocket: Any):
    """注册客户端连接到mac地址映射"""
    if mac not in mac_client_map:
      obj = {"websocket":websocket}
      mac_client_map[mac] = obj
    logger.info(f"客户端 [{mac}] 已连接，当前连接数: {len(mac_client_map)}")

async def unregister_client(mac: str, websocket: Any):
    """注销客户端连接"""
    if mac in mac_client_map:
        # 直接删除该mac的连接
        del mac_client_map[mac]
        logger.info(f"客户端 [{mac}] 已断开，剩余连接数: {len(mac_client_map)}")
    
    # 清理mac_user_map中的数据
    if mac in mac_user_map:
        del mac_user_map[mac]
        logger.info(f"已清理 [{mac}] 的用户信息")

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
            
            try:
                # 解析消息
                msg_data = json.loads(message)
                
                # 检查消息类型
                if msg_data.get('type') == 'userInfo':
                    # 存储数据到mac_user_map
                    mac_user_map[mac] = msg_data.get('data', {})
                    logger.info(f"已存储 [{mac}] 的用户信息")
            except json.JSONDecodeError as e:
                logger.error(f"消息解析失败: {str(e)}")
            
            # 示例1: 回复当前客户端
            # await websocket.send(f"服务端已收到 [{mac}] 的消息: {message}")

    except ConnectionClosedError:
        logger.info(f"客户端 [{mac}] 异常断开连接")
    except ConnectionClosedOK:
        logger.info(f"客户端 [{mac}] 正常断开连接")
    finally:
        # 4. 注销客户端
        await unregister_client(mac, websocket)
class UserInfoHTTPHandler(BaseHTTPRequestHandler):
    """处理HTTP请求的处理器类"""
    def do_GET(self):
        # 解析请求路径和参数
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # 处理 /userInfo 路径
        if path == '/userInfo':
            # 从请求头中获取 device-id
            device_id = self.headers.get('Device-Id')
            if not device_id:
                self.send_error(400, "Missing Device-Id header")
                return
            
            # 从 mac_user_map 中获取用户信息
            if device_id in mac_user_map:
                user_data = mac_user_map[device_id]
                user_info = user_data.get('userInfo', {})
                device_state = user_data.get('deviceState', {})
                use_history = user_data.get('useHistory', [])
                
                # 格式化用户信息
                user_info_str = f"姓名：{user_info.get('name', '')}，性别：{user_info.get('sex', '')}，年龄：{user_info.get('age', '')}，身高：{user_info.get('height', '')}，体重：{user_info.get('weight', '')}"
                
                # 格式化设备状态
                device_state_str = f"强度{device_state.get('strength', 0)}，模式{device_state.get('mode', 0)}，当前状态{device_state.get('status', '')}，设备名称{device_state.get('deviceName', '')}，最小强度{device_state.get('minStrength', 0)}，最大强度{device_state.get('maxStrength', 0)}，最长使用时间{device_state.get('maxTime', 0)}分钟，当前使用时间{device_state.get('useTime', 0)}分钟，约束{device_state.get('constraints', '')}"
                
                #设备可用模式 modeList
                mode_list = user_data.get('modeList', [])
                mode_list_str = "全部按摩模式有："
                if mode_list:
                    modes = []
                    for item in mode_list:
                        mode_id = item.get('modeId', '')
                        tips = item.get('tips', '')
                        position = item.get('position', '')
                        introduce = item.get('introduce', '')
                        modes.append(f"模式ID:{mode_id},适用部位:{position},提示:{tips},模式类型:{introduce}")
                    mode_list_str += "；".join(modes)
                else:
                    mode_list_str = "无"
                
                # 格式化历史记录
                history_count = len(use_history)
                history_str = f"当前历史记录数量为{history_count}条"
                for idx, record in enumerate(use_history, 1):
                    history_str += f",第{idx}条数据，模式:{record.get('mode', 0)},强度:{record.get('strength', 0)}, 开始时间:{record.get('startTime', '')},结束时间:{record.get('endTime', '')}"
                history_str += "."
                
                formatted_data = {
                    "用户信息": user_info_str,
                    "当前设备状态": device_state_str,
                    "设备可用模式": mode_list_str,
                    "历史记录": history_str
                }
                
                response = {
                    "code": 0,
                    "data": formatted_data
                }
            else:
                response = {
                    "code": -1,
                    "data": {},
                    "message": "Device not found or no user info"
                }
            
            # 发送响应
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            # 其他路径返回404
            self.send_error(404, "Not Found")

async def start_http_server():
    """启动HTTP服务"""
    server = HTTPServer((HTTP_HOST, HTTP_PORT), UserInfoHTTPHandler)
    logger.info(f"HTTP服务已启动 → http://{HTTP_HOST}:{HTTP_PORT}")
    
    # 使用 asyncio 来运行 HTTP 服务器
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, server.serve_forever)

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
        for mac, client_obj in list(mac_client_map.items()):
            try:
                websocket = client_obj['websocket']
                await websocket.close(code=1001, reason=b"Server shutdown")
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
    try:
        # 使用asyncio.to_thread来运行阻塞的mcp.run函数
        await asyncio.to_thread(mcp.run, transport="stdio")
    except KeyboardInterrupt:
        pass

# Start the server
if __name__ == "__main__":
    # 创建事件循环
    loop = asyncio.get_event_loop()
    
    # 运行服务端
    try:
        # 在事件循环中运行所有服务器
        loop.run_until_complete(asyncio.gather(
            run_mcp_server(),  # 运行MCP服务器
            startWsServer(),    # 运行WebSocket服务器
            start_http_server()  # 运行HTTP服务器
        ))
    except KeyboardInterrupt:
        logger.info("\n服务端已停止")
    finally:
        # 确保事件循环被正确关闭
        loop.close()
