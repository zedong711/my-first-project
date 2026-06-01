import pyautogui
import time

print("="*50)
print("报价器坐标获取工具")
print("="*50)

# 1. 获取起始星数输入框坐标
print("\n📍 第一步：获取【起始星数】输入框坐标")
print("请打开报价器，点击「王者1星」按钮，确保输入框显示出来")
print("然后将鼠标移动到【起始星数】输入框的中心位置")
print("\n倒计时 5 秒后自动获取坐标...")
for i in range(5, 0, -1):
    print(f"  {i} 秒...")
    time.sleep(1)

start_x, start_y = pyautogui.position()
print(f"\n✅ 起始星数输入框坐标: [{start_x}, {start_y}]")

time.sleep(1)

# 2. 获取结束星数输入框坐标
print("\n📍 第二步：获取【结束星数】输入框坐标")
print("现在将鼠标移动到【结束星数】输入框的中心位置")
print("\n倒计时 5 秒后自动获取坐标...")
for i in range(5, 0, -1):
    print(f"  {i} 秒...")
    time.sleep(1)

end_x, end_y = pyautogui.position()
print(f"\n✅ 结束星数输入框坐标: [{end_x}, {end_y}]")

# 3. 输出配置代码
print("\n" + "="*50)
print("请将以下内容添加到 wzry_coords.json 的 buttons 部分：")
print("="*50)
print(f'''
    "王者_起始星数": [{start_x}, {start_y}],
    "王者_结束星数": [{end_x}, {end_y}]
''')
print("="*50)

# 4. 验证窗口坐标（可选）
print("\n💡 提示：")
print("- 这些坐标是绝对屏幕坐标，程序会自动转换为相对于报价器窗口的坐标")
print("- 如果以后调整了报价器窗口位置，需要重新获取坐标")