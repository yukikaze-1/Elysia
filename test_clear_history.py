#!/usr/bin/env python3
"""
测试重构后的Service API功能
包含Token管理和聊天历史记录管理的所有API
"""

import requests
import json
import time

# 服务器地址
BASE_URL = "http://localhost:11100"

def test_token_apis():
    """测试Token管理相关API"""
    print("=== 测试Token管理API ===\n")
    
    try:
        # 1. 获取详细Token统计
        print("1. 获取详细Token统计...")
        response = requests.get(f"{BASE_URL}/chat/token_stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✓ 总Token数: {stats['total_stats']['total_tokens']}")
        else:
            print(f"   ✗ 失败: {response.status_code}")
        
        # 2. 获取简化Token统计
        print("\n2. 获取简化Token统计...")
        response = requests.get(f"{BASE_URL}/chat/token_stats/simple")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✓ 本地Token: {stats['local_tokens']}")
            print(f"   ✓ 云端Token: {stats['cloud_tokens']}")
            print(f"   ✓ 总Token: {stats['total_tokens']}")
        else:
            print(f"   ✗ 失败: {response.status_code}")
        
        # 3. 保存Token统计
        print("\n3. 保存Token统计...")
        response = requests.post(f"{BASE_URL}/chat/save_token_stats")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ {result['message']}")
        else:
            print(f"   ✗ 失败: {response.status_code}")
        
        print("\n=== Token管理API测试完成 ===")
        
    except Exception as e:
        print(f"Token API测试出错: {e}")

def test_history_apis():
    """测试历史记录管理相关API"""
    print("\n=== 测试历史记录管理API ===\n")
    
    try:
        # 1. 获取历史统计
        print("1. 获取历史统计...")
        response = requests.get(f"{BASE_URL}/chat/history_stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✓ 总消息数: {stats['total_messages']}")
            print(f"   ✓ 用户消息: {stats['human_messages']}")
            print(f"   ✓ AI消息: {stats['ai_messages']}")
            initial_count = stats['total_messages']
        else:
            print(f"   ✗ 失败: {response.status_code}")
            return
        
        # 2. 备份历史记录
        if initial_count > 0:
            print("\n2. 备份历史记录...")
            response = requests.post(f"{BASE_URL}/chat/backup_history")
            if response.status_code == 200:
                backup_info = response.json()
                print(f"   ✓ 备份成功: {backup_info['backup_file']}")
                print(f"   ✓ 备份消息数: {backup_info['message_count']}")
            else:
                print(f"   ✗ 失败: {response.status_code}")
        else:
            print("\n2. 跳过备份（没有历史记录）")
        
        # 3. 清除历史记录
        print("\n3. 清除历史记录...")
        response = requests.post(f"{BASE_URL}/chat/clear_history")
        if response.status_code == 200:
            clear_info = response.json()
            print(f"   ✓ {clear_info['message']}")
            print(f"   ✓ 清除消息数: {clear_info['details']['cleared_messages']}")
            print(f"   ✓ 剩余消息数: {clear_info['details']['remaining_messages']}")
        else:
            print(f"   ✗ 失败: {response.status_code}")
        
        # 4. 验证清除结果
        print("\n4. 验证清除结果...")
        response = requests.get(f"{BASE_URL}/chat/history_stats")
        if response.status_code == 200:
            new_stats = response.json()
            print(f"   ✓ 验证结果 - 剩余消息数: {new_stats['total_messages']}")
            if new_stats['total_messages'] == 0:
                print("   ✓ 历史记录清除成功")
            else:
                print("   ⚠ 历史记录清除可能不完整")
        else:
            print(f"   ✗ 验证失败: {response.status_code}")
        
        # 5. 测试重新加载
        print("\n5. 测试重新加载...")
        response = requests.post(f"{BASE_URL}/chat/reload_history")
        if response.status_code == 200:
            reload_info = response.json()
            print(f"   ✓ {reload_info['message']}")
            print(f"   ✓ 重新加载前: {reload_info['old_count']} 条消息")
            print(f"   ✓ 重新加载后: {reload_info['new_count']} 条消息")
        else:
            print(f"   ✗ 失败: {response.status_code}")
        
        print("\n=== 历史记录管理API测试完成 ===")
        
    except Exception as e:
        print(f"历史记录API测试出错: {e}")

def test_basic_health():
    """测试基础健康检查"""
    print("=== 测试基础服务健康检查 ===\n")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"   ✓ 服务状态: {health['status']}")
        else:
            print(f"   ✗ 健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"健康检查出错: {e}")

def show_current_history():
    """显示当前历史记录"""
    try:
        print("\n=== 当前历史记录 ===")
        response = requests.get(f"{BASE_URL}/chat/show_history")
        if response.status_code == 200:
            history = response.json()
            print(f"当前历史记录 ({len(history)} 条消息):")
            for i, msg in enumerate(history[:10]):  # 只显示前10条
                print(f"  {msg}")
            if len(history) > 10:
                print(f"  ... 还有 {len(history) - 10} 条消息")
        else:
            print(f"获取历史记录失败: {response.status_code}")
    except Exception as e:
        print(f"显示历史记录时出错: {e}")

def main():
    print("选择测试选项:")
    print("1. 测试所有API（推荐）")
    print("2. 仅测试Token管理API")
    print("3. 仅测试历史记录管理API")
    print("4. 仅测试基础健康检查")
    print("5. 显示当前历史记录")
    
    choice = input("请输入选择 (1-5): ").strip()
    
    try:
        # 首先检查服务是否运行
        requests.get(f"{BASE_URL}/health", timeout=3)
    except requests.exceptions.RequestException:
        print("错误: 无法连接到服务器，请确保服务正在运行 (python service.py)")
        return
    
    if choice == "1":
        test_basic_health()
        test_token_apis()
        test_history_apis()
        show_current_history()
    elif choice == "2":
        test_token_apis()
    elif choice == "3":
        test_history_apis()
    elif choice == "4":
        test_basic_health()
    elif choice == "5":
        show_current_history()
    else:
        print("无效选择")

if __name__ == "__main__":
    main()
