#!/usr/bin/env python3
"""
策略管理CLI工具

提供策略的查看、注册、删除、参数管理功能。

Usage:
    python tools/strategy_cli.py list [--all]
    python tools/strategy_cli.py info <strategy_name>
    python tools/strategy_cli.py register <name> <class_path> [options]
    python tools/strategy_cli.py delete <strategy_name>
    python tools/strategy_cli.py params <strategy_name> [--set KEY=VALUE...]
"""
import sys
sys.path.insert(0, '/Users/mawenhao/Desktop/code/股票策略')

import argparse
import json
from typing import Optional

from database.db_manager import DatabaseManager
from strategies.registry import Registry


def cmd_list(args):
    registry = Registry()
    if args.all:
        strategy_names = registry.list_all()
    else:
        strategy_names = registry.list(status='active')

    if not strategy_names:
        print("没有找到策略")
        return

    print(f"=== 策略列表 ({len(strategy_names)} 个) ===")
    for name in strategy_names:
        metadata = registry.get_metadata(name)
        if metadata:
            threshold = "需要threshold" if metadata.threshold_required else "不需要threshold"
            print(f"  {name:<30} | {threshold} | 最小数据: {metadata.min_data_days}天")
        else:
            print(f"  {name}")


def cmd_info(args):
    db = DatabaseManager()
    strategy = db.get_strategy(args.name)

    if not strategy:
        print(f"策略 '{args.name}' 不存在")
        return

    print(f"=== 策略信息: {args.name} ===")
    print(f"  ID: {strategy.get('id', 'N/A')}")
    print(f"  显示名称: {strategy.get('display_name', 'N/A')}")
    print(f"  类路径: {strategy.get('class_path', 'N/A')}")
    print(f"  源文件: {strategy.get('source_file', 'N/A')}")
    print(f"  描述: {strategy.get('description', 'N/A')}")
    print(f"  版本: {strategy.get('version', 'N/A')}")
    print(f"  作者: {strategy.get('author', 'N/A')}")
    print(f"  状态: {strategy.get('status', 'N/A')}")
    print(f"  策略类型: {strategy.get('strategy_type', 'N/A')}")
    print(f"  需要threshold: {strategy.get('threshold_required', 'N/A')}")
    print(f"  最小数据天数: {strategy.get('min_data_days', 'N/A')}")
    print(f"  创建时间: {strategy.get('created_at', 'N/A')}")
    print(f"  更新时间: {strategy.get('updated_at', 'N/A')}")

    params = db.get_strategy_params(args.name)
    if params:
        print(f"\n  参数列表:")
        for p in params:
            default = p.get('default_value')
            current = p.get('current_value')
            print(f"    {p['param_name']}: current={current}, default={default}")
            if p.get('description'):
                print(f"      描述: {p['description']}")
    else:
        print(f"\n  参数: 无")


def cmd_register(args):
    db = DatabaseManager()

    existing = db.get_strategy(args.name)
    if existing:
        print(f"策略 '{args.name}' 已存在，使用 update 模式")
        strategy_data = {
            'name': args.name,
            'class_path': args.class_path,
            'display_name': args.display_name or args.name,
            'description': args.description or '',
            'version': args.version or '1.0.0',
            'author': args.author or '',
            'threshold_required': not args.no_threshold,
            'min_data_days': args.min_data_days or 60,
            'status': 'active',
        }
    else:
        strategy_data = {
            'name': args.name,
            'class_path': args.class_path,
            'display_name': args.display_name or args.name,
            'description': args.description or '',
            'version': args.version or '1.0.0',
            'author': args.author or '',
            'threshold_required': not args.no_threshold,
            'min_data_days': args.min_data_days or 60,
            'status': 'active',
        }

    success = db.save_strategy(strategy_data)
    if success:
        print(f"策略 '{args.name}' 注册成功")
    else:
        print(f"策略 '{args.name}' 注册失败")
        sys.exit(1)


def cmd_delete(args):
    registry = Registry()

    if not registry.is_registered(args.name):
        print(f"策略 '{args.name}' 不存在")
        sys.exit(1)

    success = registry.soft_delete(args.name)
    if success:
        print(f"策略 '{args.name}' 已标记为删除 (deprecated)")
    else:
        print(f"策略 '{args.name}' 删除失败")
        sys.exit(1)


def cmd_params(args):
    db = DatabaseManager()

    strategy = db.get_strategy(args.name)
    if not strategy:
        print(f"策略 '{args.name}' 不存在")
        sys.exit(1)

    if args.set:
        params_to_update = {}
        for param_spec in args.set:
            if '=' not in param_spec:
                print(f"参数格式错误: {param_spec}，应使用 KEY=VALUE 格式")
                sys.exit(1)
            key, value = param_spec.split('=', 1)
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
            params_to_update[key] = value

        success = db.update_strategy_params(args.name, params_to_update)
        if success:
            print(f"参数更新成功")
        else:
            print(f"参数更新失败")
            sys.exit(1)
    else:
        params = db.get_strategy_params(args.name)
        if not params:
            print(f"策略 '{args.name}' 没有参数")
            return

        print(f"=== 策略参数: {args.name} ===")
        for p in params:
            print(f"\n  {p['param_name']} ({p['param_type']})")
            print(f"    当前值: {p['current_value']}")
            print(f"    默认值: {p['default_value']}")
            print(f"    必填: {p['is_required']}")
            if p.get('description'):
                print(f"    描述: {p['description']}")
            if p.get('constraints'):
                print(f"    约束: {p['constraints']}")


def cmd_scan(args):
    """扫描并加载所有策略文件，触发 @register 装饰器"""
    from pathlib import Path
    import importlib.util

    strategies_dir = Path(__file__).parent.parent / 'strategies'
    loaded = []
    failed = []

    for py_file in strategies_dir.glob('*.py'):
        if py_file.name.startswith('_') or py_file.name == '策略模板.py':
            continue

        module_name = f"strategies.{py_file.stem}"

        if module_name in sys.modules and not args.force:
            print(f"跳过 (已加载): {py_file.name}")
            continue

        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if not spec or not spec.loader:
            failed.append((py_file.name, "无法创建模块spec"))
            continue

        if module_name in sys.modules:
            del sys.modules[module_name]

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
            loaded.append(py_file.name)
            print(f"注册成功: {py_file.name}")
        except Exception as e:
            failed.append((py_file.name, str(e)))
            print(f"注册失败: {py_file.name} - {e}")

    print(f"\n=== 扫描完成 ===")
    print(f"成功: {len(loaded)} 个")
    print(f"失败: {len(failed)} 个")
    if loaded:
        print(f"已注册: {', '.join(loaded)}")
    if failed:
        print(f"失败列表:")
        for name, err in failed:
            print(f"  - {name}: {err}")

    registry = Registry()
    print(f"\n当前已注册策略 ({len(registry._metadata)} 个):")
    for name in sorted(registry._metadata.keys()):
        print(f"  - {name}")


def main():
    parser = argparse.ArgumentParser(
        description='策略管理CLI工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s list                    # 列出所有活跃策略
  %(prog)s list --all              # 列出所有策略(包括已废弃)
  %(prog)s scan                    # 扫描并注册所有策略文件
  %(prog)s scan --force            # 强制重新扫描
  %(prog)s info 天宫B1策略v2        # 查看策略详细信息
  %(prog)s register my_strategy strategies.my_strategy --description "我的策略"
  %(prog)s delete my_strategy      # 删除策略(软删除)
  %(prog)s params my_strategy       # 查看策略参数
  %(prog)s params my_strategy --set threshold=10 --set stop_loss=0.05
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    parser_list = subparsers.add_parser('list', help='列出策略')
    parser_list.add_argument('--all', action='store_true', help='列出所有策略(包括已废弃)')

    parser_scan = subparsers.add_parser('scan', help='扫描并注册所有策略文件')
    parser_scan.add_argument('--force', action='store_true', help='强制重新扫描')

    parser_info = subparsers.add_parser('info', help='查看策略信息')
    parser_info.add_argument('name', help='策略名称')

    parser_register = subparsers.add_parser('register', help='注册新策略')
    parser_register.add_argument('name', help='策略名称')
    parser_register.add_argument('class_path', help='策略类路径')
    parser_register.add_argument('--display-name', help='显示名称')
    parser_register.add_argument('--description', help='策略描述')
    parser_register.add_argument('--version', default='1.0.0', help='版本号')
    parser_register.add_argument('--author', help='作者')
    parser_register.add_argument('--no-threshold', action='store_true', help='不需要threshold参数')
    parser_register.add_argument('--min-data-days', type=int, default=60, help='最小数据天数')

    parser_delete = subparsers.add_parser('delete', help='删除策略(软删除)')
    parser_delete.add_argument('name', help='策略名称')

    parser_params = subparsers.add_parser('params', help='查看或更新策略参数')
    parser_params.add_argument('name', help='策略名称')
    parser_params.add_argument('--set', nargs='+', metavar='KEY=VALUE', help='设置参数')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'list':
        cmd_list(args)
    elif args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'info':
        cmd_info(args)
    elif args.command == 'register':
        cmd_register(args)
    elif args.command == 'delete':
        cmd_delete(args)
    elif args.command == 'params':
        cmd_params(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()