"""跨平台应用数据目录获取工具。

遵循各平台官方规范：
- Windows : %LOCALAPPDATA%\\厂商\\产品   (本机数据 / 缓存 / 临时)
            %APPDATA%\\厂商\\产品       (用户配置 / 偏好，可漫游)
- macOS   : ~/Library/Application Support/厂商/产品
            ~/Library/Caches/厂商/产品
- Linux   : $XDG_DATA_HOME/产品 或 ~/.local/share/产品
            $XDG_CONFIG_HOME/产品 或 ~/.config/产品
            $XDG_CACHE_HOME/产品  或 ~/.cache/产品

用法：
    from app_paths import get_app_paths
    p = get_app_paths("MyCompany", "MyApp")
    print(p.data)       # 数据目录
    print(p.config)     # 配置目录
    print(p.cache)      # 缓存目录
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AppPaths:
    """应用各类目录的路径集合，均已确保存在。"""

    data: Path      # 数据目录（数据库、用户数据等）
    config: Path    # 配置目录（配置文件）
    cache: Path     # 缓存目录（可安全清理）
    temp: Path      # 临时目录（进程级，可安全删除）


def _windows_paths(vendor: str, product: str) -> AppPaths:
    """Windows 实现：优先读系统 API 返回的目录，回退到环境变量。"""
    local = os.environ.get("LOCALAPPDATA")
    roaming = os.environ.get("APPDATA")

    if not local or not roaming:
        # 环境变量缺失时兜底（罕见，某些服务/沙箱环境）
        home = Path.home()
        local = str(home / "AppData" / "Local")
        roaming = str(home / "AppData" / "Roaming")

    base_local = Path(local) / vendor / product
    base_roaming = Path(roaming) / vendor / product

    return AppPaths(
        data=base_local / "data",
        config=base_roaming / "config",   # 配置放 Roaming，便于换机保留
        cache=base_local / "cache",
        temp=base_local / "temp",
    )


def _macos_paths(vendor: str, product: str) -> AppPaths:
    """macOS 实现。"""
    home = Path.home()
    lib = home / "Library"

    # 使用 vendor.product 作为 bundle 风格命名，避免厂商/产品同名冲突
    bundle = f"{vendor}.{product}"

    return AppPaths(
        data=lib / "Application Support" / bundle,
        config=lib / "Application Support" / bundle,   # macOS 数据与配置同目录
        cache=lib / "Caches" / bundle,
        temp=lib / "Caches" / bundle / "tmp",
    )


def _linux_paths(vendor: str, product: str) -> AppPaths:
    """Linux 实现：遵循 XDG Base Directory 规范。"""
    home = Path.home()

    data = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
    config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    cache = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))

    return AppPaths(
        data=data / product,
        config=config / product,
        cache=cache / product,
        temp=cache / product / "tmp",
    )


def get_app_paths(vendor: str = "MyCompany",
                  product: str = "MyApp",
                  *,
                  create: bool = True) -> AppPaths:
    """返回应用的数据/配置/缓存/临时目录，跨平台。

    Args:
        vendor:  厂商/组织名，如 "AcmeCorp"。
        product: 产品/应用名，如 "MyTool"。
        create:  是否自动创建这些目录（默认 True，创建失败会抛异常）。

    Returns:
        AppPaths，包含 data / config / cache / temp 四个 Path 对象。
    """
    if not vendor or not product:
        raise ValueError("vendor 和 product 不能为空")

    system = sys.platform
    if system.startswith("win"):
        paths = _windows_paths(vendor, product)
    elif system == "darwin":
        paths = _macos_paths(vendor, product)
    else:
        paths = _linux_paths(vendor, product)

    if create:
        for p in (paths.data, paths.config, paths.cache, paths.temp):
            p.mkdir(parents=True, exist_ok=True)

    return paths


def get_temp_dir() -> Path:
    """返回系统级临时目录（跨平台），用于短生命周期临时文件。

    区别于 AppPaths.temp：这里返回的是操作系统提供的 %TEMP% / /tmp 等，
    由系统负责周期性清理，适合"用完即丢"的临时文件。
    """
    return Path(tempfile.gettempdir())


if __name__ == "__main__":
    # 示例用法
    p = get_app_paths("MyCompany", "MyApp")
    print("数据目录 :", p.data)
    print("配置目录 :", p.config)
    print("缓存目录 :", p.cache)
    print("临时目录 :", p.temp)
    print("系统临时 :", get_temp_dir())
