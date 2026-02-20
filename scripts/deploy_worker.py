#!/usr/bin/env python3
"""
Worker 部署脚本

功能：
1. 读取项目根目录的 .env 文件
2. 自动上传 secrets 到 Cloudflare Workers
3. 部署 Worker（支持 api 和 settlement 环境）

用法：
    python scripts/deploy_worker.py [选项] [目标]

目标：
    api           只部署 API Worker
    settlement    只部署 Settlement Worker
    all           部署全部 Worker (默认)

选项：
    --dry-run      模拟运行，检查配置
    --secrets-only 只上传 secrets，不部署
    --deploy-only  只部署，不上传 secrets
    -h, --help     显示帮助

示例：
    python scripts/deploy_worker.py api                  # 部署 API Worker
    python scripts/deploy_worker.py --dry-run            # 检查配置
    python scripts/deploy_worker.py --secrets-only all   # 只上传 secrets
    python scripts/deploy_worker.py --deploy-only api    # 只部署
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import dotenv_values


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
WORKER_DIR = PROJECT_ROOT / "worker"
ENV_FILE = PROJECT_ROOT / ".env"

# 需要上传到 Workers 的 secrets（从 .env 读取）
SECRETS_TO_UPLOAD = [
    "KIMI_API_KEY",
    "DEEPSEEK_API_KEY",
    "SECRET_KEY",
    "INTERNAL_SECRET",
]


def get_npx_command() -> str:
    """根据操作系统返回正确的 npx 命令"""
    if platform.system() == "Windows":
        return "npx.cmd"
    return "npx"


def get_wrangler_command() -> list:
    """返回 wrangler 命令列表，跨平台兼容"""
    npx = get_npx_command()
    return [npx, "wrangler"]


def parse_env_file(env_path: Path) -> Dict[str, str]:
    """解析 .env 文件，返回 key-value 字典（使用 python-dotenv）"""
    if not env_path.exists():
        print(f"❌ 错误：找不到 .env 文件: {env_path}")
        sys.exit(1)

    # 使用 dotenv_values 解析，它会自动处理引号和注释
    env_vars = dotenv_values(env_path)

    # 过滤掉 None 值，确保返回 Dict[str, str]
    return {k: v for k, v in env_vars.items() if v is not None}


def upload_secret(secret_name: str, secret_value: str, env: str) -> bool:
    """上传单个 secret 到 Cloudflare Workers"""
    print(f"  📤 上传 secret: {secret_name} ...", end=" ", flush=True)

    # 检查 secret 值是否有效
    if not secret_value or not secret_value.strip():
        print("⚠️  跳过 (值为空)")
        return True  # 空值不算失败，只是跳过

    try:
        # wrangler secret put 从 stdin 读取值
        # 使用 input 参数传递值，适用于 Windows 和 Unix
        cmd = ["npx.cmd", "wrangler", "secret", "put", secret_name, "--env", env]

        # 添加换行符模拟用户输入
        input_value = secret_value.strip() + "\n"

        result = subprocess.run(
            cmd,
            input=input_value,
            cwd=WORKER_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=False,  # 不使用 shell，避免安全问题
        )

        if result.returncode == 0:
            print("✅ 成功")
            return True
        else:
            print(f"❌ 失败")
            stderr = result.stderr.strip() if result.stderr else "未知错误"
            # 如果已经存在，不算失败
            if "already exists" in stderr.lower() or "already uploaded" in stderr.lower():
                print(f"     ℹ️  Secret 已存在，将使用新值更新")
                return True
            print(f"     错误: {stderr}")
            if result.stdout:
                print(f"     输出: {result.stdout.strip()}")
            return False

    except FileNotFoundError:
        print(f"❌ 失败")
        print(f"     错误: 找不到 wrangler 命令")
        print(f"     请确保已安装 wrangler CLI: npm install -g wrangler")
        return False
    except Exception as e:
        print(f"❌ 失败")
        print(f"     错误: {e}")
        return False


def upload_secrets(env: str, env_vars: Dict[str, str], dry_run: bool = False) -> bool:
    """上传所有需要的 secrets"""
    print(f"\n🔐 {'[模拟] ' if dry_run else ''}上传 secrets 到 Workers ({env} 环境)...")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for secret_name in SECRETS_TO_UPLOAD:
        secret_value = env_vars.get(secret_name, "")

        if not secret_value:
            print(f"  ⚠️  跳过 {secret_name}: 在 .env 中未找到或为空")
            skipped_count += 1
            continue

        if dry_run:
            # 模拟模式：只显示前10个字符
            masked = secret_value[:10] + \
                "..." if len(secret_value) > 10 else secret_value
            print(f"  📤 {secret_name}: {masked}")
            success_count += 1
            continue

        if upload_secret(secret_name, secret_value, env):
            success_count += 1
        else:
            fail_count += 1

    print(
        f"\n📊 Secrets 结果: {success_count} 成功, {fail_count} 失败, {skipped_count} 跳过")
    return fail_count == 0


def check_wrangler_version() -> Tuple[bool, str]:
    """检查 wrangler 版本"""
    try:
        result = subprocess.run(
            ["npx.cmd", "wrangler", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=WORKER_DIR,
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            return True, version
        return False, "无法获取版本"
    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        return False, "wrangler 未安装"
    except Exception as e:
        return False, str(e)


def deploy_worker(env: str) -> bool:
    """部署 Worker"""
    print(f"\n🚀 部署 Worker ({env} 环境)...")

    try:
        cmd = ["npx", "wrangler", "deploy", "--env", env]

        result = subprocess.run(
            cmd,
            cwd=WORKER_DIR,
            capture_output=False,  # 显示实时输出
            text=True,
            encoding="utf-8",
        )

        if result.returncode == 0:
            print(f"\n✅ Worker ({env}) 部署成功！")
            return True
        else:
            print(f"\n❌ Worker ({env}) 部署失败")
            return False

    except FileNotFoundError:
        print("❌ 错误: 找不到 wrangler 命令")
        print("请先安装 wrangler CLI: npm install -g wrangler")
        return False
    except Exception as e:
        print(f"❌ 部署出错: {e}")
        return False


def check_wrangler_login() -> bool:
    """检查 wrangler 是否已登录"""
    try:
        result = subprocess.run(
            ["npx.cmd", "wrangler", "whoami"],
            cwd=WORKER_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def print_usage():
    """打印使用说明"""
    print("""
用法: python scripts/deploy_worker.py [选项] [目标]

目标:
    api           只部署 API Worker
    settlement    只部署 Settlement Worker
    all           部署全部 Worker (默认)

选项:
    --dry-run     模拟运行，不上传 secrets 也不部署
    --secrets-only 只上传 secrets，不部署
    --deploy-only  只部署，不上传 secrets
    -h, --help    显示帮助信息

示例:
    python scripts/deploy_worker.py api                    # 部署 API Worker
    python scripts/deploy_worker.py --dry-run              # 检查配置
    python scripts/deploy_worker.py --secrets-only api     # 只上传 secrets
    python scripts/deploy_worker.py all                    # 部署全部
""")


def main():
    # 解析命令行参数
    args = sys.argv[1:]

    # 选项标志
    dry_run = "--dry-run" in args
    secrets_only = "--secrets-only" in args
    deploy_only = "--deploy-only" in args
    show_help = "-h" in args or "--help" in args

    # 移除选项，剩下的是目标
    for opt in ["--dry-run", "--secrets-only", "--deploy-only", "-h", "--help"]:
        while opt in args:
            args.remove(opt)

    if show_help:
        print_usage()
        sys.exit(0)

    target = args[0] if args else "all"

    if target not in ["api", "settlement", "all"]:
        print(f"❌ 错误: 未知的部署目标 '{target}'")
        print_usage()
        sys.exit(1)

    print("=" * 60)
    print("🚀 API Mirror Worker 部署脚本")
    if dry_run:
        print("   [模拟模式 - 不会实际部署]")
    print("=" * 60)

    # 检查 wrangler
    print("\n📋 检查 wrangler CLI...")
    version_ok, version = check_wrangler_version()
    if not version_ok:
        print(f"❌ {version}")
        print("请安装 wrangler: npm install -g wrangler")
        sys.exit(1)
    print(f"✅ wrangler {version}")

    # 检查登录状态
    if not dry_run and not check_wrangler_login():
        print("❌ 未登录 Cloudflare")
        print("请运行: wrangler login")
        sys.exit(1)
    if not dry_run:
        print("✅ 已登录 Cloudflare")

    # 解析 .env 文件
    print(f"\n📖 读取环境变量: {ENV_FILE}")
    env_vars = parse_env_file(ENV_FILE)
    print(f"✅ 读取到 {len(env_vars)} 个环境变量")

    # 显示将要上传的 secrets
    print("\n📦 将要处理的 Secrets:")
    for secret_name in SECRETS_TO_UPLOAD:
        status = "✓" if env_vars.get(secret_name) else "✗ (缺失)"
        print(f"   {status} {secret_name}")

    # 部署目标列表
    targets = ["api", "settlement"] if target == "all" else [target]

    # 模拟模式提前退出
    if dry_run:
        print("\n✅ 配置检查完成 (模拟模式)")
        sys.exit(0)

    all_success = True

    for env in targets:
        print("\n" + "=" * 60)
        print(f"🎯 部署目标: {env}")
        print("=" * 60)

        # 上传 secrets（如果不是仅部署模式）
        if not deploy_only:
            if not upload_secrets(env, env_vars):
                print(f"\n⚠️ 部分 secrets 上传失败，是否继续部署？ (y/n): ", end="")
                try:
                    response = input().strip().lower()
                    if response != 'y':
                        all_success = False
                        continue
                except KeyboardInterrupt:
                    print("\n❌ 已取消")
                    sys.exit(1)

        # 部署 Worker（如果不是仅 secrets 模式）
        if not secrets_only:
            if not deploy_worker(env):
                all_success = False

    # 总结
    print("\n" + "=" * 60)
    if all_success:
        print("✅ 所有部署任务完成！")
    else:
        print("⚠️ 部分部署任务失败，请检查日志")
    print("=" * 60)

    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
