import pyautogui
import time

print("请将鼠标准确移动到闲管家中「灰色背景的用户行」上...")
print("5 秒后自动获取坐标...")
time.sleep(5)
x, y = pyautogui.position()
print(f"\n请将下面两行复制到 XianGuanjia.top_user 方法中：")
print(f"click_x = {x}")
print(f"click_y = {y}")