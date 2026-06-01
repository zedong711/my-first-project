import time
import os
import re
import sys
import random
import requests
from loguru import logger
from utils.xianyu_utils import generate_sign


class XianyuApis:
    def __init__(self):
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'origin': 'https://www.goofish.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.goofish.com/',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        })
        
    def clear_duplicate_cookies(self):
        """清理重复的cookies"""
        new_jar = requests.cookies.RequestsCookieJar()
        added_cookies = set()
        cookie_list = list(self.session.cookies)
        cookie_list.reverse()
        
        for cookie in cookie_list:
            if cookie.name not in added_cookies:
                new_jar.set_cookie(cookie)
                added_cookies.add(cookie.name)
                
        self.session.cookies = new_jar
        self.update_env_cookies()
        
    def update_env_cookies(self):
        """更新.env文件中的COOKIES_STR"""
        try:
            cookie_str = '; '.join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])
            
            env_path = os.path.join(os.getcwd(), '.env')
            if not os.path.exists(env_path):
                logger.warning(".env文件不存在，无法更新COOKIES_STR")
                return
                
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
                
            if 'COOKIES_STR=' in env_content:
                new_env_content = re.sub(
                    r'COOKIES_STR=.*', 
                    f'COOKIES_STR={cookie_str}',
                    env_content
                )
                
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write(new_env_content)
                    
                logger.debug("已更新.env文件中的COOKIES_STR")
        except Exception as e:
            logger.warning(f"更新.env文件失败: {str(e)}")
        
    def hasLogin(self, retry_count=0):
        """调用hasLogin.do接口进行登录状态检查"""
        if retry_count >= 3:
            logger.error("Login检查失败，重试次数过多")
            return False
            
        try:
            # 添加随机延迟，避免被检测
            time.sleep(random.uniform(0.5, 1.5))
            
            url = 'https://passport.goofish.com/newlogin/hasLogin.do'
            params = {
                'appName': 'xianyu',
                'fromSite': '77'
            }
            data = {
                'hid': self.session.cookies.get('unb', ''),
                'ltl': 'true',
                'appName': 'xianyu',
                'appEntrance': 'web',
                '_csrf_token': self.session.cookies.get('XSRF-TOKEN', ''),
                'umidToken': '',
                'hsiz': self.session.cookies.get('cookie2', ''),
                'bizParams': 'taobaoBizLoginFrom=web',
                'mainPage': 'false',
                'isMobile': 'false',
                'lang': 'zh_CN',
                'returnUrl': '',
                'fromSite': '77',
                'isIframe': 'true',
                'documentReferer': 'https://www.goofish.com/',
                'defaultView': 'hasLogin',
                'umidTag': 'SERVER',
                'deviceId': self.session.cookies.get('cna', '')
            }
            
            response = self.session.post(url, params=params, data=data, timeout=15)
            res_json = response.json()
            
            if res_json.get('content', {}).get('success'):
                logger.debug("Login成功")
                self.clear_duplicate_cookies()
                return True
            else:
                logger.warning(f"Login失败: {res_json}")
                time.sleep(random.uniform(1, 2))
                return self.hasLogin(retry_count + 1)
                
        except Exception as e:
            logger.error(f"Login请求异常: {str(e)}")
            time.sleep(random.uniform(1, 2))
            return self.hasLogin(retry_count + 1)

    def get_token(self, device_id, retry_count=0):
        if retry_count >= 3:
            logger.warning("获取token失败，尝试重新登陆")
            if self.hasLogin():
                logger.info("重新登录成功，重新尝试获取token")
                return self.get_token(device_id, 0)
            else:
                logger.error("重新登录失败，Cookie已失效")
                self._handle_cookie_expired()
                sys.exit(1)

        # 添加随机延迟，避免请求过快
        time.sleep(random.uniform(0.8, 1.5))

        # 获取token值 - 注意这里要用完整的 _m_h5_tk
        cookie_token = self.session.cookies.get('_m_h5_tk', '')
        if not cookie_token:
            logger.error("Cookie中缺少 _m_h5_tk")
            self._handle_cookie_expired()
            sys.exit(1)
        
        token = cookie_token.split('_')[0]
        
        # 生成时间戳
        timestamp = str(int(time.time() * 1000))
        
        # 数据体
        data_val = '{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"' + device_id + '"}'
        
        # 生成签名
        sign = generate_sign(timestamp, token, data_val)
        
        params = {
            'jsv': '2.7.2',
            'appKey': '34839810',  # 使用与 init 一致的 appKey
            't': timestamp,
            'sign': sign,
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idlemessage.pc.login.token',
            'sessionOption': 'AutoLoginOnly',
        }
        
        data = {
            'data': data_val,
        }
        
        headers = {
            "Host": "h5api.m.goofish.com",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "accept": "application/json",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua-mobile": "?0",
            "origin": "https://www.goofish.com",
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://www.goofish.com/",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "priority": "u=1, i"
        }
        
        try:
            response = self.session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', 
                headers=headers, 
                params=params, 
                data=data,
                timeout=15
            )
            
            # 处理响应中的Set-Cookie
            if 'Set-Cookie' in response.headers:
                logger.debug("检测到Set-Cookie，更新cookie")
                self.clear_duplicate_cookies()
            
            res_json = response.json()
            
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                ret_str = str(ret_value)
                
                # 检查是否成功
                if 'SUCCESS::调用成功' in ret_str:
                    logger.info("Token获取成功")
                    return res_json
                
                # 检测风控/限流错误
                if 'RGV587_ERROR' in ret_str or '被挤爆啦' in ret_str or 'FAIL_SYS_USER_VALIDATE' in ret_str:
                    logger.error(f"❌ 触发风控: {ret_value}")
                    self._handle_cookie_expired()
                    sys.exit(1)
                
                # 其他错误
                logger.warning(f"Token API调用失败，错误信息: {ret_value}")
                time.sleep(random.uniform(1, 2))
                return self.get_token(device_id, retry_count + 1)
            else:
                logger.error(f"Token API返回格式异常: {res_json}")
                return self.get_token(device_id, retry_count + 1)
                
        except requests.exceptions.Timeout:
            logger.error("Token API请求超时")
            return self.get_token(device_id, retry_count + 1)
        except Exception as e:
            logger.error(f"Token API请求异常: {str(e)}")
            time.sleep(random.uniform(1, 2))
            return self.get_token(device_id, retry_count + 1)

    def _handle_cookie_expired(self):
        """处理Cookie过期的情况"""
        logger.error("🔴 Cookie已失效，请按以下步骤更新：")
        print("\n" + "="*60)
        print("⚠️  Cookie 失效处理")
        print("="*60)
        print("\n请按以下步骤获取新的Cookie：")
        print("1. 打开浏览器，访问: https://www.goofish.com")
        print("2. 登录你的闲鱼账号（如需滑块验证，请手动完成）")
        print("3. 点击页面上的「消息」按钮")
        print("4. 按 F12 打开开发者工具")
        print("5. 切换到 Network（网络）标签")
        print("6. 刷新页面（F5）")
        print("7. 找到任意请求，在 Request Headers 中找到 Cookie")
        print("8. 复制完整的 Cookie 值")
        print("\n" + "-"*60)
        
        new_cookie_str = input("\n请输入新的Cookie字符串 (直接回车则退出程序): ").strip()
        
        if new_cookie_str:
            try:
                from http.cookies import SimpleCookie
                cookie = SimpleCookie()
                cookie.load(new_cookie_str)
                
                self.session.cookies.clear()
                for key, morsel in cookie.items():
                    self.session.cookies.set(key, morsel.value, domain='.goofish.com')
                
                logger.success("✅ Cookie已更新")
                self.update_env_cookies()
                
                print("\n✅ Cookie已保存，请重新启动程序")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Cookie解析失败: {e}")
                sys.exit(1)
        else:
            logger.info("用户取消输入，程序退出")
            sys.exit(1)

    def get_item_info(self, item_id, retry_count=0):
        """获取商品信息"""
        if retry_count >= 3:
            logger.error("获取商品信息失败，重试次数过多")
            return {"error": "获取商品信息失败，重试次数过多"}
        
        time.sleep(random.uniform(0.3, 0.8))
        
        cookie_token = self.session.cookies.get('_m_h5_tk', '')
        token = cookie_token.split('_')[0] if cookie_token else ''
        
        timestamp = str(int(time.time() * 1000))
        data_val = '{"itemId":"' + item_id + '"}'
        sign = generate_sign(timestamp, token, data_val)
        
        params = {
            'jsv': '2.7.2',
            'appKey': '444e9908a51d1cb236a27862abc769c9',
            't': timestamp,
            'sign': sign,
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idle.pc.detail',
            'sessionOption': 'AutoLoginOnly',
        }
        
        data = {
            'data': data_val,
        }
        
        try:
            response = self.session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/', 
                params=params, 
                data=data,
                timeout=15
            )
            
            if 'Set-Cookie' in response.headers:
                self.clear_duplicate_cookies()
            
            res_json = response.json()
            
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if 'SUCCESS::调用成功' in str(ret_value):
                    logger.debug(f"商品信息获取成功: {item_id}")
                    return res_json
                else:
                    logger.warning(f"商品信息API调用失败: {ret_value}")
                    time.sleep(random.uniform(0.5, 1))
                    return self.get_item_info(item_id, retry_count + 1)
            else:
                return self.get_item_info(item_id, retry_count + 1)
                
        except Exception as e:
            logger.error(f"商品信息API请求异常: {str(e)}")
            time.sleep(random.uniform(0.5, 1))
            return self.get_item_info(item_id, retry_count + 1)