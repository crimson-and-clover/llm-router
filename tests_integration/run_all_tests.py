"""
集成测试主程序
运行所有测试阶段
"""

from pathlib import Path
import subprocess
import sys


def run_test(test_file):
    """运行单个测试文件"""
    print(f"\n{'='*60}")
    print(f"运行: {test_file}")
    print('='*60)

    test_path = Path(__file__).parent / test_file
    result = subprocess.run(
        [sys.executable, str(test_path)],
        capture_output=False,  # 直接输出到控制台
        text=True
    )

    return result.returncode == 0


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("API Mirror 集成测试套件")
    print("="*60)

    tests = [
        ("test_01_init.py", "数据库初始化测试"),
        ("test_02_cli_users.py", "CLI 用户管理测试"),
        ("test_03_cli_keys.py", "CLI API Key 管理测试"),
        ("test_04_api.py", "API 端点测试"),
        ("test_05_edge_cases.py", "边界条件测试"),
        ("test_06_edge_worker.py", "边缘 Worker 能力测试"),
    ]

    results = []

    for test_file, description in tests:
        success = run_test(test_file)
        results.append((test_file, description, success))

        if not success:
            print(f"\n[FAIL] {description} 失败，是否继续? (y/n): ", end="")
            # 自动继续
            print("y")

    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    for test_file, description, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} - {description} ({test_file})")

    passed = sum(1 for _, _, s in results if s)
    total = len(results)

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n[SUCCESS] 所有测试通过!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
