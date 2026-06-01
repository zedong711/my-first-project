import json
from wzry_auto import WZRYQuoter  #新加
import re
from typing import List, Dict
import os
from openai import OpenAI
from loguru import logger
import pyautogui
import time
import pygetwindow as gw


class XianyuReplyBot:
    def __init__(self):
                # 记录每个会话最后一次报价完成的时间戳
        self.last_quote_time = {}  # {chat_id: timestamp}
        # 初始化OpenAI客户端
        # 会话状态管理：{chat_id: {"device": ..., "account": ..., "service": ..., "rank": ...}}
        self.session_state = {}
        self.client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        self._init_system_prompts()
        self._init_agents()
        self.router = IntentRouter(self.agents['classify'])
        self.last_intent = None  # 记录最后一次意图
        self.wzry_quoter = WZRYQuoter("wzry_coords.json")  #新加
        self.guanjia = XianGuanjia("消息")  # 闲管家窗口标题


    def _init_agents(self):
        """初始化各领域Agent"""
        self.agents = {
            'classify':ClassifyAgent(self.client, self.classify_prompt, self._safe_filter),
            'price': PriceAgent(self.client, self.price_prompt, self._safe_filter),
            'tech': TechAgent(self.client, self.tech_prompt, self._safe_filter),
            'default': DefaultAgent(self.client, self.default_prompt, self._safe_filter),
        }

    def _init_system_prompts(self):
        """初始化各Agent专用提示词，优先加载用户自定义文件，否则使用Example默认文件"""
        prompt_dir = "prompts"
        
        def load_prompt_content(name: str) -> str:
            """尝试加载提示词文件"""
            # 优先尝试加载 target.txt
            target_path = os.path.join(prompt_dir, f"{name}.txt")
            if os.path.exists(target_path):
                file_path = target_path
            else:
                # 尝试默认提示词 target_example.txt
                file_path = os.path.join(prompt_dir, f"{name}_example.txt")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.debug(f"已加载 {name} 提示词，路径: {file_path}, 长度: {len(content)} 字符")
                return content

        try:
            # 加载分类提示词
            self.classify_prompt = load_prompt_content("classify_prompt")
            # 加载价格提示词
            self.price_prompt = load_prompt_content("price_prompt")
            # 加载技术提示词
            self.tech_prompt = load_prompt_content("tech_prompt")
            # 加载默认提示词
            self.default_prompt = load_prompt_content("default_prompt")
                
            logger.info("成功加载所有提示词")
        except Exception as e:
            logger.error(f"加载提示词时出错: {e}")
            raise

    def _safe_filter(self, text: str) -> str:
        """安全过滤模块"""
        blocked_phrases = ["微信", "QQ", "支付宝", "银行卡", "线下"]
        return "[安全提醒]请通过平台沟通" if any(p in text for p in blocked_phrases) else text

    def format_history(self, context: List[Dict]) -> str:
        """格式化对话历史，返回完整的对话记录"""
        # 过滤掉系统消息，只保留用户和助手的对话
        user_assistant_msgs = [msg for msg in context if msg['role'] in ['user', 'assistant']]
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_assistant_msgs])

    def generate_reply(self, user_msg: str, item_desc: str, context: List[Dict], chat_id: str = None, user_name: str = None) -> str:
        
        import time
        
                # 静默模式：报价完成后2分钟内，用户说非报价内容，只回复客套话
                # 静默模式：报价完成后2分钟内，用户说非报价内容，只回复客套话
        if chat_id and chat_id in self.last_quote_time:
            if time.time() - self.last_quote_time[chat_id] < 120:  # 2分钟内
                game_keywords = [
                    "王者", "荣耀", "星耀", "青铜", "白银", "黄金", "铂金", "钻石",
                    "代练", "代打", "上分", "陪练", "巅峰", "战力", "段位", "多少钱"
                ]
                
                # 检查是否是新报价需求：包含报价关键词，或者包含数字+“到”/“星”
                has_game_keyword = any(k in user_msg for k in game_keywords)
                has_number_and_range = bool(re.search(r'\d+', user_msg)) and bool(re.search(r'[到至\-~]|星', user_msg))
                
                if has_game_keyword or has_number_and_range:
                    # 可能是新需求，清除静默状态，继续走报价流程
                    del self.last_quote_time[chat_id]
                else:
                    # 严格匹配结束语：只允许完全等于一个或两个字
                    strict_endings = {"好", "好的", "行", "嗯嗯", "谢谢", "感谢", "ok", "OK"}
                    if user_msg.strip().lower() in strict_endings:
                        polite_replies = ["好的", "有需要再找我", "嗯嗯", "没问题"]
                        import random
                        return random.choice(polite_replies)
                    else:
                        logger.info(f"会话 {chat_id} 需要人工处理，消息: {user_msg}")
                        if user_name:
                            self._top_user_in_guanjia(user_name)
                        else:
                            logger.warning(f"user_name 为空，无法置顶，chat_id={chat_id}")
                        return "请稍等"
        
        
        quote = self.handle_quote(user_msg, chat_id)
        if quote:
            return quote
        # ... 其余代码不变 ...
         # 拦截无意义短消息，主动引导用户说出需求
        game_keywords = [
            "王者", "荣耀", "星耀", "青铜", "白银", "黄金", "铂金", "钻石",
            "代练", "代打", "上分", "陪练", "巅峰", "战力", "段位", "多少钱"
        ]
        if not any(k in user_msg for k in game_keywords) and len(user_msg.strip()) <= 5:
            return "欢迎您，辛苦您具体描述需要代练什么内容，是什么系统呢？我们给您急速报价\n\n比如：苹果 星耀5 1星-王者1星"
                    # === 兜底：无法自动处理的消息 ===
        if not any(k in user_msg for k in game_keywords) and not re.search(r'\d+', user_msg):
            strict_endings = {"好", "好的", "行", "嗯嗯", "谢谢", "感谢", "ok", "OK"}
            if user_msg.strip().lower() in strict_endings:
                return "嗯嗯"
            else:
                logger.info(f"会话 {chat_id} 需要人工处理，消息: {user_msg}")
                if user_name:
                    self._top_user_in_guanjia(user_name)
                else:
                    logger.warning(f"user_name 为空，无法置顶，chat_id={chat_id}")
                return "请稍等"
        # 原有对话逻辑（报价未触发时执行）
        formatted_context = self.format_history(context)
        detected_intent = self.router.detect(user_msg, item_desc, formatted_context)
        
        internal_intents = {'classify'}
        if detected_intent == 'no_reply':
            logger.info(f'意图识别完成: no_reply - 无需回复')
            self.last_intent = 'no_reply'
            return "-"
        elif detected_intent in self.agents and detected_intent not in internal_intents:
            agent = self.agents[detected_intent]
            logger.info(f'意图识别完成: {detected_intent}')
            self.last_intent = detected_intent
        else:
            agent = self.agents['default']
            logger.info(f'意图识别完成: default')
            self.last_intent = 'default'
        
        bargain_count = self._extract_bargain_count(context)
        logger.info(f'议价次数: {bargain_count}')
        
        return agent.generate(
            user_msg=user_msg,
            item_desc=item_desc,
            context=formatted_context,
            bargain_count=bargain_count
        )
    
    def _extract_bargain_count(self, context: List[Dict]) -> int:
        """
        从上下文中提取议价次数信息
        
        Args:
            context: 对话历史
            
        Returns:
            int: 议价次数，如果没有找到则返回0
        """
        # 查找系统消息中的议价次数信息
        for msg in context:
            if msg['role'] == 'system' and '议价次数' in msg['content']:
                try:
                    # 提取议价次数
                    match = re.search(r'议价次数[:：]\s*(\d+)', msg['content'])
                    if match:
                        return int(match.group(1))
                except Exception:
                    pass
        return 0

    def reload_prompts(self):
        """重新加载所有提示词"""
        logger.info("正在重新加载提示词...")
        self._init_system_prompts()
        self._init_agents()
        logger.info("提示词重新加载完成")


    def _top_user_in_guanjia(self, chat_id):
        """在闲管家中置顶用户"""
        try:
            import threading
            def do_top():
                time.sleep(2)  # 等待界面稳定
                self.guanjia.top_user(chat_id)  # 用chat_id搜索
            t = threading.Thread(target=do_top)
            t.daemon = True
            t.start()
        except Exception as e:
            logger.error(f"置顶失败: {e}")




    
    def handle_quote(self, user_msg, chat_id):
        import time
        game_keywords = [
            "王者", "荣耀", "星耀", "青铜", "白银", "黄金", "铂金", "钻石",
            "代练", "代打", "上分", "陪练", "巅峰", "战力", "段位", "多少钱"
        ]
        
        clean_msg = user_msg.strip()
        
        # === 优先检测省略表达（如“那到50星呢”、“到50星”） ===
        # 匹配消息中包含“到/至”后跟数字和“星”的模式，且消息中没有段位关键词
        has_rank_keyword = any(k in clean_msg for k in ["王者", "星耀", "钻石", "铂金", "黄金", "白银", "青铜"])
        to_match = re.search(r'[到至]\s*(\d+)\s*星', clean_msg)
        if to_match and not has_rank_keyword:
            return "请提供完整的段位范围，例如：王者1星到50星"
        
        # 如果没有 chat_id，使用消息内容作为临时标识
        if not chat_id:
            chat_id = f"temp_{clean_msg[:30]}"
        
        # ... 后续原有代码保持不变 ...
        
        # 获取或初始化该会话的状态
        state = self.session_state.get(chat_id, {
            "device": None,
            "account": "QQ",
            "service": "段位代练",
            "rank": None
        })
        
        # === 从当前消息提取信息，覆盖已有字段 ===
        # 设备
                # 设备（支持“安卓的”、“安卓手机”、“苹果的”等）
        if any(k in clean_msg for k in ["安卓", "android", "Android"]):
            state["device"] = "安卓"
        elif any(k in clean_msg for k in ["苹果", "IOS", "ios", "iPhone", "iphone", "Iphone"]):
            state["device"] = "IOS"
        
        # 账号
                # 账号（支持多种写法）
        # 微信：微信、wx、WX、Wx、vx、VX、Vx
        if any(k in clean_msg for k in ["微信", "wx", "WX", "Wx", "vx", "VX", "Vx","v","V"]):
            state["account"] = "微信"
        # QQ：QQ、qq、Q、q、手Q、手q
        elif any(k in clean_msg for k in ["QQ", "qq", "Q", "q", "手Q", "手q"]):
            state["account"] = "QQ"
        
        # 服务类型
        if "巅峰" in clean_msg:
            state["service"] = "巅峰赛"
        elif "战力" in clean_msg:
            state["service"] = "战力"
        elif "陪练" in clean_msg or "陪玩" in clean_msg:
            state["service"] = "段位陪练"
        elif "代练" in clean_msg or "代打" in clean_msg or "上分" in clean_msg:
            state["service"] = "段位代练"
        
                # 段位/分数信息
        rank_keywords = ["王者", "星耀", "钻石", "铂金", "黄金", "白银", "青铜", "巅峰", "战力"]
        has_number = bool(re.search(r'\d', clean_msg))
        has_range = bool(re.search(r'[到至\-~]', clean_msg))
        has_rank_keyword = any(k in clean_msg for k in rank_keywords)
        
        # 特殊处理：检测到省略表达（如“到50星”），直接追问
        to_match = re.search(r'^[到至]\s*(\d+)\s*星?', clean_msg)
        if to_match and not has_rank_keyword:
            # 这是省略表达，需要追问起始段位
            return "请提供完整的段位范围，例如：王者1星到50星"
        
        # 判断是否为完整的段位描述
        is_complete_rank = False
        if has_range:
            parts = re.split(r'[到至\-~]', clean_msg)
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                is_complete_rank = True
        if len(re.findall(r'\d+', clean_msg)) >= 2 and has_range:
            is_complete_rank = True
        
        # 只有完整的段位描述才存储
        if has_rank_keyword and is_complete_rank:
            state["rank"] = clean_msg
        
        # 保存状态
        self.session_state[chat_id] = state
        
        # 检查是否触发了报价关键词
        if any(keyword in clean_msg for keyword in game_keywords):
            try:
                # 构建解析消息：只使用当前存储的状态，不拼接历史
                parse_parts = []
                if state["rank"]:
                    parse_parts.append(state["rank"])
                if state["device"]:
                    parse_parts.append(state["device"])
                if state["account"]:
                    parse_parts.append(state["account"])
                if state["service"]:
                    parse_parts.append(state["service"])
                
                parse_msg = " ".join(parse_parts)
                logger.info(f"会话 {chat_id} 状态: {state}")
                logger.info(f"解析消息: {parse_msg}")
                
                # 解析参数
                params = self.wzry_quoter.parse_message(parse_msg)

                
                
                # 覆盖明确提取的值
                params["device"] = state["device"]
                params["account_type"] = state["account"]
                params["service"] = state["service"]
                
                # 完整性检查
                missing = []
                if not params["device"]:
                    missing.append("设备类型（安卓/苹果）")
                #if not params["account_type"]:
                #    missing.append("账号类型（微信/QQ）")
                
                
                service_type = params["service"]
                if service_type in ["段位代练", "段位陪练"]:
                    if not params["start_rank"] or not params["end_rank"]:
                        missing.append("段位范围（例如：星耀3到王者1星）")
                elif service_type == "巅峰赛":
                    if not params["from_point"] or not params["to_point"]:
                        missing.append("巅峰分数范围（例如：1800到2000）")
                elif service_type == "战力":
                    if not params["from_point"] or not params["to_point"]:
                        missing.append("战力分数范围（例如：3000到4000）")
                
                if missing:
                    prompt = "请补充以下信息：\n" + "\n".join([f"• {item}" for item in missing])
                    prompt += "\n\n（例如：安卓 QQ 代练 星耀3到王者1星）"
                    return prompt
                
                                # 执行报价
                                # 执行报价
                result = self.wzry_quoter.get_quote_by_params(params)
                
                # === 提取价格并生成下单指引 ===
                price = None
                service_type = params.get("service", "段位代练")
                
                if service_type == "巅峰赛":
                    # 巅峰赛：不指定的价格是：XX元
                    match = re.search(r'不指定的价格是[：:]\s*(\d+)\s*元', result)
                    if match:
                        price = int(match.group(1))
                elif service_type == "战力":
                    # 战力：取正常英雄的价格
                    match = re.search(r'正常英雄[：:]\s*(\d+)\s*元', result)
                    if match:
                        price = int(match.group(1))
                else:
                    # 段位代练/陪练：正常上分是：XX元
                    match = re.search(r'正常上分是[：:]\s*(\d+)\s*元', result)
                    if match:
                        price = int(match.group(1))
                
                if price:
                    quantity = price // 2   # 整除，如42→21
                    guidance = f"\n\n下单页面商品拍{quantity}次即可"
                    result = result + guidance
                
                # 记录报价完成时间
                self.last_quote_time[chat_id] = time.time()
                # 报价成功后只清除段位信息，保留设备、账号、服务
                if chat_id in self.session_state:
                    self.session_state[chat_id]["rank"] = None
                return result
                
            except Exception as e:
                logger.error(f"报价失败: {e}")
                return "抱歉，报价系统暂时不可用，请稍后再试。"
        
        return None
    
       

class IntentRouter:
    """意图路由决策器"""

    def __init__(self, classify_agent):
        self.rules = {
            'tech': {  # 技术类优先判定
                'keywords': ['参数', '规格', '型号', '连接', '对比'],
                'patterns': [
                    r'和.+比'             
                ]
            },
            'price': {
                'keywords': ['便宜', '价', '砍价', '少点'],
                'patterns': [r'\d+元', r'能少\d+']
            }
        }
        self.classify_agent = classify_agent

    def detect(self, user_msg: str, item_desc, context) -> str:
        """三级路由策略（技术优先）"""
        text_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', user_msg)
        
        # 1. 技术类关键词优先检查
        if any(kw in text_clean for kw in self.rules['tech']['keywords']):
            # logger.debug(f"技术类关键词匹配: {[kw for kw in self.rules['tech']['keywords'] if kw in text_clean]}")
            return 'tech'
            
        # 2. 技术类正则优先检查
        for pattern in self.rules['tech']['patterns']:
            if re.search(pattern, text_clean):
                # logger.debug(f"技术类正则匹配: {pattern}")
                return 'tech'

        # 3. 价格类检查
        for intent in ['price']:
            if any(kw in text_clean for kw in self.rules[intent]['keywords']):
                # logger.debug(f"价格类关键词匹配: {[kw for kw in self.rules[intent]['keywords'] if kw in text_clean]}")
                return intent
            
            for pattern in self.rules[intent]['patterns']:
                if re.search(pattern, text_clean):
                    # logger.debug(f"价格类正则匹配: {pattern}")
                    return intent
        
        # 4. 大模型兜底
        # logger.debug("使用大模型进行意图分类")
        return self.classify_agent.generate(
            user_msg=user_msg,
            item_desc=item_desc,
            context=context
        )


class BaseAgent:
    """Agent基类"""

    def __init__(self, client, system_prompt, safety_filter):
        self.client = client
        self.system_prompt = system_prompt
        self.safety_filter = safety_filter

    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int = 0) -> str:
        """生成回复模板方法"""
        messages = self._build_messages(user_msg, item_desc, context)
        response = self._call_llm(messages)
        return self.safety_filter(response)

    def _build_messages(self, user_msg: str, item_desc: str, context: str) -> List[Dict]:
        """构建消息链"""
        return [
            {"role": "system", "content": f"【商品信息】{item_desc}\n【你与客户对话历史】{context}\n{self.system_prompt}"},
            {"role": "user", "content": user_msg}
        ]

    def _call_llm(self, messages: List[Dict], temperature: float = 0.4) -> str:
        """调用大模型"""
        response = self.client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "qwen-max"),
            messages=messages,
            temperature=temperature,
            max_tokens=500,
            top_p=0.8
        )
        return response.choices[0].message.content


class PriceAgent(BaseAgent):
    """议价处理Agent"""

    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int=0) -> str:
        """重写生成逻辑"""
        dynamic_temp = self._calc_temperature(bargain_count)
        messages = self._build_messages(user_msg, item_desc, context)
        messages[0]['content'] += f"\n▲当前议价轮次：{bargain_count}"

        response = self.client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "qwen-max"),
            messages=messages,
            temperature=dynamic_temp,
            max_tokens=500,
            top_p=0.8
        )
        return self.safety_filter(response.choices[0].message.content)

    def _calc_temperature(self, bargain_count: int) -> float:
        """动态温度策略"""
        return min(0.3 + bargain_count * 0.15, 0.9)


class TechAgent(BaseAgent):
    """技术咨询Agent"""
    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int=0) -> str:
        """重写生成逻辑"""
        messages = self._build_messages(user_msg, item_desc, context)
        # messages[0]['content'] += "\n▲知识库：\n" + self._fetch_tech_specs()

        response = self.client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "qwen-max"),
            messages=messages,
            temperature=0.4,
            max_tokens=500,
            top_p=0.8,
            extra_body={
                "enable_search": True,
            }
        )

        return self.safety_filter(response.choices[0].message.content)


    # def _fetch_tech_specs(self) -> str:
    #     """模拟获取技术参数（可连接数据库）"""
    #     return "功率：200W@8Ω\n接口：XLR+RCA\n频响：20Hz-20kHz"


class ClassifyAgent(BaseAgent):
    """意图识别Agent"""

    def generate(self, **args) -> str:
        response = super().generate(**args)
        return response


class DefaultAgent(BaseAgent):


    """默认处理Agent"""

    def _call_llm(self, messages: List[Dict], *args) -> str:
        """限制默认回复长度"""
        response = super()._call_llm(messages, temperature=0.7)
        return response
    


class XianGuanjia:
    """闲管家自动置顶操作 - 图像识别版"""
    
    def __init__(self, window_title="消息"):
        self.window_title = window_title
        self.window = None
        self.ref_x = 0
        self.ref_y = 0
        
    def find_window(self):
        windows = gw.getWindowsWithTitle(self.window_title)
        if windows:
            self.window = windows[0]
            self.ref_x = self.window.left
            self.ref_y = self.window.top
            return True
        return False
    
    def activate_window(self):
        if self.window:
            try:
                self.window.activate()
                time.sleep(0.5)
                return True
            except:
                pass
        return False
    
    def click_image(self, image_path, confidence=0.8):
        """通过图像识别左键点击"""
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                pyautogui.click(center.x, center.y)
                time.sleep(0.3)
                return True
        except Exception as e:
            print(f"图像识别失败: {e}")
        return False
    
    def right_click_image(self, image_path, confidence=0.8):
        """通过图像识别右键点击"""
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                pyautogui.rightClick(center.x, center.y)
                time.sleep(0.5)
                return True
        except Exception as e:
            print(f"右键图像识别失败: {e}")
        return False
    
    def top_user(self, user_name):
        """图像识别灰色行 → 右键 → 点击置顶"""
        if not self.find_window():
            print("❌ 未找到闲管家窗口")
            return False
        
        self.activate_window()
        time.sleep(0.5)
        
        # 1. 右键点击灰色行
        if not self.right_click_image("gray_row.png", confidence=0.7):
            print("❌ 未找到灰色背景行")
            return False
        
        time.sleep(0.8)  # 等待菜单弹出
        
        # 2. 点击“置顶”菜单项
        if self.click_image("top_menu.png", confidence=0.7):
            print(f"✅ 已置顶用户: {user_name}")
            return True
        else:
            # 备选：键盘模拟（假设“置顶”是菜单第2项）
            pyautogui.press("down", presses=2)
            time.sleep(0.2)
            pyautogui.press("enter")
            print(f"✅ 已通过键盘置顶用户: {user_name}")
            return True