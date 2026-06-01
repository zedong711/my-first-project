"""
王者荣耀 - 全自动报价（快速稳定版）
支持代练、陪练、巅峰赛、战力
"""

import pyautogui
import pyperclip
import time
import json
import os
import re
import pygetwindow as gw

pyautogui.FAILSAFE = True


class WZRYQuoter:
    def __init__(self, config_file="wzry_coords.json"):
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        self.cfg = config["王者荣耀"]
        self.services = self.cfg["services"]
        self.ranks = self.cfg["ranks"]
        self.zone = self.cfg["zone"]
        self.buttons = self.cfg["buttons"]
        self.rank_names = list(self.ranks.keys())
        
        self.window_title = "小蜜蜂报价器"
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
                time.sleep(0.1)
                return True
            except:
                pass
        return False
    
    def click_relative(self, abs_x, abs_y):
        """直接点击绝对坐标"""
        target_x = self.window.left + (abs_x - self.ref_x)
        target_y = self.window.top + (abs_y - self.ref_y)
        pyautogui.click(target_x, target_y)
    
    def click(self, name, coords_dict):
        if name not in coords_dict:
            print(f"❌ 未找到: {name}")
            return False
        abs_x, abs_y = coords_dict[name]
        self.click_relative(abs_x, abs_y)
        return True
    

    def check_missing_info(self, user_msg):
        params = self.parse_message(user_msg)
        missing = []

        if not params["device"]:
            missing.append("设备类型（安卓/苹果）")
        if not params["account_type"]:
            missing.append("账号类型（微信/QQ）")
        

        service = params["service"]
        if service in ["段位代练", "段位陪练"]:
            if not params["start_rank"] or not params["end_rank"]:
                missing.append("段位范围（例如：星耀3到王者1星）")
        elif service == "巅峰赛":
            if not params["from_point"] or not params["to_point"]:
                missing.append("巅峰分数范围（例如：1800到2000）")
        elif service == "战力":
            if not params["from_point"] or not params["to_point"]:
                missing.append("战力分数范围（例如：3000到4000）")
 
        if missing:
            prompt = "请补充以下信息：\n" + "\n".join([f"• {item}" for item in missing])
            prompt += "\n\n（例如：安卓 QQ 代练 星耀3到王者1星）"
            return prompt
        return None
    
    

    def parse_message(self, user_msg):
        result = {
            "start_rank": None,
            "end_rank": None,
            "start_star": None,
            "end_star": None,
            "service": None,
            "device": None,
            "account_type": None,
            "from_point": None,
            "to_point": None
        }
        msg = user_msg

                # ========== 0. 预处理：拆分非王者段位的中文连写数字 ==========
        # 例如：“星耀三五” → “星耀三 五”，便于后续分别转换为等级和星数
        # 王者段位不拆分，直接整体转换（如“王者五十” → “王者50星”）
                # ========== 0. 预处理：拆分非王者段位的中文连写数字 ==========
        non_king_ranks = "星耀|钻石|铂金|黄金|白银|青铜"
        # 处理“星耀三五”类型
        msg = re.sub(rf'({non_king_ranks})([一二三四五])([一二三四五六七八九十百千万]+)', 
                     lambda m: f"{m.group(1)}{m.group(2)} {m.group(3)}", msg)
        # 处理“星耀十五”类型
        msg = re.sub(rf'({non_king_ranks})([一二三四五]?十[一二三四五六七八九]?)', 
                     lambda m: f"{m.group(1)} {m.group(2)}" if m.group(2) else m.group(0), msg)
        

        
                # ===== 极简补丁：直接识别“王者X-XX星”、“王者X到Y”等格式 =====
                
        #m = re.search(r'王者\s*(\d+)\s*[-~到至]\s*(\d+)\s*星?', user_msg)
        #if m:
            #result["start_rank"] = "王者1星"
           # result["end_rank"] = "王者1星"
          #  result["start_star"] = int(m.group(1))
            ##result["end_star"] = int(m.group(2))
            #result["service"] = "段位代练"
            # 设备
            #if "苹果" in user_msg or "IOS" in user_msg or "ios" in user_msg:
             #   result["device"] = "IOS"
           # elif "安卓" in user_msg:
            #    result["device"] = "安卓"
            # 账号
            #if "微信" in user_msg or "wx" in user_msg.lower():
            #    result["account_type"] = "微信"
           # else:
             #   result["account_type"] = "QQ"
            #return result
    
        # ========== 1. 中文数字转换 ==========
        chinese_digit_map = {
            "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "百": 100, "千": 1000, "万": 10000
        }

        def chinese_to_arabic(cn_str):
            if not cn_str:
                return None
            total = 0
            current = 0
            for char in cn_str:
                if char in chinese_digit_map:
                    val = chinese_digit_map[char]
                    if val >= 10:
                        if current == 0:
                            current = 1
                        total += current * val
                        current = 0
                    else:
                        current = val
                else:
                    return None
            total += current
            return total

        pattern_cn_num = re.compile(r'[零一二三四五六七八九十百千万]+')
        matches = pattern_cn_num.findall(msg)
        for cn_num in matches:
            arabic = chinese_to_arabic(cn_num)
            if arabic is not None:
                msg = msg.replace(cn_num, str(arabic))

        single_map = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
                      "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
        for cn, num in single_map.items():
            msg = msg.replace(cn, num)

        # 拆分合并的数字（如“星耀35星” → “星耀3 5星”）
        msg = re.sub(r'(星耀|钻石|铂金|黄金|白银|青铜)([1-5])([1-9])\s*星', r'\1\2 \3星', msg)
        # 处理“王者X到Y”、“王者X星到Y星”等格式，拆分为两个独立的段位词条
        msg = re.sub(r'王者\s*(\d+)\s*星?\s*[到至\-~]\s*(\d+)\s*星?', r'王者\1星 王者\2星', msg)
        # ========== 2. 段位简写统一 ==========
        msg = re.sub(r'钻\s*([0-9])', r'钻石\1', msg)
        msg = re.sub(r'星耀\s*([0-9])', r'星耀\1', msg)
        # ========== 2. 段位简写统一 ==========
        # 将“钻一”、“钻二”等映射为“钻石1”、“钻石2”
        msg = re.sub(r'钻\s*([0-9])', r'钻石\1', msg)
        # 星耀简写：星耀一 → 星耀1
        msg = re.sub(r'星耀\s*([0-9])', r'星耀\1', msg)
        # 其他常见简写可根据需要添加

        # ========== 3. 规范化段位表达 ==========
        msg = re.sub(r'(?<![0-9])青铜(?![0-9])', '青铜3', msg)
        msg = re.sub(r'(?<![0-9])白银(?![0-9])', '白银3', msg)
        msg = re.sub(r'(?<![0-9])黄金(?![0-9])', '黄金4', msg)
        msg = re.sub(r'(?<![0-9])铂金(?![0-9])', '铂金4', msg)
        msg = re.sub(r'(?<![0-9])钻石(?![0-9])', '钻石5', msg)
        msg = re.sub(r'(?<![0-9])星耀(?![0-9])', '星耀5', msg)
        msg = re.sub(r'王者[^\d]*(星)', r'王者1\1', msg)
        msg = re.sub(r'王者\s*(\d+)\s*星?', r'王者\1星', msg)

        # ========== 4. 设备、账号识别 ==========
        if "IOS" in msg or "ios" in msg or "苹果" in msg:
            result["device"] = "IOS"
        wx_keywords = ["微信", "wx", "WX", "Wx", "vx", "VX", "Vx", "v", "V"]
        if any(k in msg for k in wx_keywords):
            result["account_type"] = "微信"
        qq_keywords = ["QQ", "qq", "Q", "q", "手Q", "手q"]
        if any(k in msg for k in qq_keywords):
            result["account_type"] = "QQ"

                # ========== 5. 服务类型 ==========
        if "巅峰" in msg:
            result["service"] = "巅峰赛"
            result["start_rank"] = None
            result["end_rank"] = None
        elif "战力" in msg:
            result["service"] = "战力"
            result["start_rank"] = None
            result["end_rank"] = None
        elif "陪练" in msg or "陪玩" in msg:
            result["service"] = "段位陪练"
        elif "代练" in msg or "代打" in msg or "上分" in msg:
            result["service"] = "段位代练"
        else:
            # 默认服务类型为段位代练
            result["service"] = "段位代练"

        # ========== 6. 巅峰赛/战力分数解析 ==========
        if result["service"] in ["巅峰赛", "战力"]:
            score_pattern = r'(\d+)\s*[分到至\-~]+\s*(\d+)'
            score_match = re.search(score_pattern, msg)
            if score_match:
                result["from_point"] = int(score_match.group(1))
                result["to_point"] = int(score_match.group(2))
            else:
                single_score = re.search(r'巅峰\s*(\d+)', msg)
                if single_score:
                    score = int(single_score.group(1))
                    result["from_point"] = score
                    result["to_point"] = score + 200
        else:
            # 预处理：将“王者1—50星”统一为“王者1星到王者50星”
            msg = re.sub(r'王者\s*(\d+)\s*[—\-~到至]\s*(\d+)\s*星', r'王者\1星到王者\2星', msg)

            # ===== 专用补丁：直接匹配“王者X-XX星”格式 =====
            #king_direct = re.search(r'王者\s*(\d+)\s*[-~]\s*(\d+)', msg)
            #if king_direct:
             #  ranks = [("王者1星", start_star), ("王者1星", end_star)]
              #  print("DEBUG ranks (直接补丁):", ranks)
               # result["start_rank"] = ranks[0][0]
               # result["end_rank"] = ranks[-1][0]
                #result["start_star"] = ranks[0][1]
               # result["end_star"] = ranks[-1][1]
               # return result
            # ========== 7. 段位解析（支持带星数） ==========
                        # 改进的正则：匹配段位名 + 可选等级 + 可选星数（星数可能紧跟等级后或单独出现）
            # 例如：星耀3 5星 → 段位星耀，等级3，星数5
            pattern = r'(王者|星耀|钻石|铂金|黄金|白银|青铜)\s*(\d+)?\s*(?:(\d+)\s*星)?'
            matches = re.findall(pattern, msg)

            ranks = []
            for rank_name, rank_num, extra_star in matches:
                if rank_name == "王者":
                    # 王者段位：rank_num 就是星数
                    star = int(rank_num) if rank_num else 1
                    ranks.append(("王者1星", star))
                else:
                    if not rank_num:
                        rank_num = {"青铜":3,"白银":3,"黄金":4,"铂金":4,"钻石":5,"星耀":5}.get(rank_name, "1")
                    full_rank = rank_name + rank_num
                    if full_rank in self.rank_names:
                        # extra_star 可能为空
                        star = int(extra_star) if extra_star else None
                        ranks.append((full_rank, star))

            # 如果未匹配到，兜底
            if not ranks:
                fallback = re.findall(r'(王者|星耀|钻石|铂金|黄金|白银|青铜)\s*(\d+)', msg)
                for rank_name, num in fallback:
                    if rank_name == "王者":
                        ranks.append(("王者1星", int(num)))
                    else:
                        full = rank_name + num
                        if full in self.rank_names:
                            ranks.append((full, None))

            seen = set()
            unique_ranks = []
            for r, s in ranks:
                key = (r, s)
                if key not in seen:
                    seen.add(key)
                    unique_ranks.append((r, s))
            ranks = unique_ranks

            print("DEBUG ranks:", ranks)

            if len(ranks) >= 2:
                result["start_rank"] = ranks[0][0]
                result["end_rank"] = ranks[-1][0]
                result["start_star"] = ranks[0][1] if ranks[0][1] is not None else 1
                result["end_star"] = ranks[-1][1] if ranks[-1][1] is not None else 1
            elif len(ranks) == 1:
                result["start_rank"] = ranks[0][0]
                result["end_rank"] = "王者1星"
                result["start_star"] = ranks[0][1] if ranks[0][1] is not None else 1
                result["end_star"] = 1
            else:
                result["start_rank"] = None
                result["end_rank"] = None

        return result
    
    

    def get_quote_by_message(self, user_msg):
        params = self.parse_message(user_msg)
        if params["service"] in ["巅峰赛", "战力"]:
            if not params["from_point"]:
                params["from_point"] = 1200
                params["to_point"] = 1500
            print(f"   解析结果: {params['from_point']}分 → {params['to_point']}分 ({params['service']})")
        else:
            # 如果段位缺失，直接使用 None，不补全默认值（由调用方负责检查）
            print(f"   解析结果: {params['start_rank']} → {params['end_rank']} ({params['service']})")
            if params.get("start_star"):
                print(f"   起始星数: {params['start_star']}")
            if params.get("end_star"):
                print(f"   结束星数: {params['end_star']}")
        return self.get_quote(
            start_rank=params.get("start_rank"),
            end_rank=params.get("end_rank"),
            start_star=params.get("start_star"),
            end_star=params.get("end_star"),
            service=params["service"],
            device=params["device"],
            account_type=params["account_type"],
            from_point=params.get("from_point"),
            to_point=params.get("to_point")
        )
    
    def get_quote(self, start_rank=None, end_rank=None, 
                  start_star=None, end_star=None,
                  service="段位代练", 
                  device="安卓", 
                  account_type="QQ",
                  from_point=None,
                  to_point=None):
    
        if not self.find_window():
            print("❌ 未找到报价器窗口！")
            return "报价器未打开，请联系客服获取报价。"
    
        self.activate_window()
    
        print(f"\n🎮 王者荣耀报价")
        print(f"   区服: {device} / {account_type}")
        print(f"   服务: {service}")
    
        # 清空剪贴板
        pyperclip.copy("")
        time.sleep(0.05)
    
        # 1. 选择设备
        print("📱 选择设备...")
        self.click(device, self.zone)
        time.sleep(0.1)
    
        # 2. 选择账号类型
        print("🔐 选择账号类型...")
        self.click(account_type, self.zone)
        time.sleep(0.1)
    
        # 3. 选择服务类型
        print(f"⚙️ 选择服务: {service}...")
        self.click(service, self.services)
        time.sleep(0.2)
    
        # 4. 根据服务类型处理
        if service in ["巅峰赛", "战力"]:
            if from_point is None:
                from_point = 1200
            if to_point is None:
                to_point = 1500
    
            print(f"📍 起始分: {from_point} → 结束分: {to_point}")
            if service == "巅峰赛":
                start_key = "巅峰赛_起始分"
                end_key = "巅峰赛_结束分"
                generate_key = "巅峰赛_生成报价"
                content_key = "巅峰赛_报价内容框"
            else:
                start_key = "战力_起始分"
                end_key = "战力_结束分"
                generate_key = "战力_生成报价"
                content_key = "战力_报价内容框"
    
            # 输入起始分
            self.click(start_key, self.buttons)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.write(str(from_point))
            time.sleep(0.1)
    
            # 输入结束分
            self.click(end_key, self.buttons)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.write(str(to_point))
            time.sleep(0.1)
    
        else:
            if start_rank is None:
                start_rank = "青铜3"
            if end_rank is None:
                end_rank = "星耀1"
    
            print(f"   段位: {start_rank} → {end_rank}")
            
                        # 点击起始段位
            self.click(start_rank, self.ranks)
            time.sleep(0.2)
            if start_star is not None:
                self.click("王者_起始星数", self.buttons)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.05)
                pyautogui.write(str(start_star))
                time.sleep(0.1)
            
            # 点击结束段位
            self.click(end_rank, self.ranks)
            time.sleep(0.2)
            if end_star is not None:
                self.click("王者_结束星数", self.buttons)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.05)
                pyautogui.write(str(end_star))
                time.sleep(0.1)
    
            generate_key = "生成报价"
            content_key = "报价内容框"
    
        # 5. 生成报价
        print("💰 生成报价...")
        self.click(generate_key, self.buttons)
        time.sleep(1.0)  # 等待报价生成
    
        # 6. 复制报价
        print("📋 复制报价...")
        pyperclip.copy("")
        time.sleep(0.05)
    
        self.click(content_key, self.buttons)
        time.sleep(0.1)
    
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.1)
    
        result = pyperclip.paste()
    
        # 如果剪贴板为空，尝试按回车后再复制
        if not result or result.strip() == "":
            pyautogui.press("enter")
            time.sleep(0.1)
            self.click(content_key, self.buttons)
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.1)
            result = pyperclip.paste()
    
        # 降级方案
        if not result or result.strip() == "":
            if service in ["巅峰赛", "战力"]:
                result = f"【{service}】{from_point}分→{to_point}分，具体价格请咨询客服。"
            else:
                result = f"【{service}】{start_rank}→{end_rank}，具体价格请咨询客服。"
            print("⚠️ 使用降级方案生成报价文本")
        else:
            print(f"✅ 报价获取成功！")
                # 7. 重置报价器（按 C 键）
        print("🔄 重置报价器...")
        pyautogui.press('c')
        time.sleep(0.2)
        return result
    

    def get_quote_by_params(self, params):
        """直接根据大模型提取的参数字典进行报价"""
        return self.get_quote(
            start_rank=params.get("start_rank"),
            end_rank=params.get("end_rank"),
            start_star=params.get("start_star"),
            end_star=params.get("end_star"),
            service=params.get("service", "段位代练"),
            device=params.get("device", "安卓"),
            account_type=params.get("account_type", "QQ"),
            from_point=params.get("from_point"),
            to_point=params.get("to_point")
        )


# ============== 测试 ==============
if __name__ == "__main__":
    print("="*50)
    print("王者荣耀 - 全自动报价")
    print("="*50)
    print("\n1. 测试代练")
    print("2. 测试巅峰赛")
    print("3. 测试自定义消息")
    choice = input("\n选择 (1/2/3): ").strip()
    
    quoter = WZRYQuoter("wzry_coords.json")
    
    if choice == "1":
        result = quoter.get_quote("青铜3", "星耀1", "段位代练")
    elif choice == "2":
        result = quoter.get_quote(service="巅峰赛", from_point=1200, to_point=1500)
    else:
        msg = input("请输入测试消息: ").strip()
                # 测试时直接传入参数示例
        result = quoter.get_quote(start_rank="青铜3", end_rank="星耀1")
    
    print("\n" + "="*50)
    print("报价结果：")
    print(result)
    print("="*50)