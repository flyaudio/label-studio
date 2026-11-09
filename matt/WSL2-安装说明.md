# WSL2 安装说明（Ubuntu 22.04 LTS）

安装日期：2026-11-07

## 安装结果

| 项目 | 值 |
| --- | --- |
| 发行版名称 | `Ubuntu-22.04` |
| 版本类型 | WSL 2 |
| 系统版本 | Ubuntu 22.04.5 LTS |
| 内核 | 5.10.16.3-microsoft-standard-WSL2 |
| 默认登录用户 | `dev`（uid 1000，已加入 `sudo` 组） |
| 安装位置 | `C:\WSL\Ubuntu-22.04`（虚拟磁盘 `ext4.vhdx`，约 1.2GB） |
| WSL 内核包 | 已安装（`C:\Windows\System32\lxss\tools\kernel`） |
| 默认版本 | 2（`wsl --set-default-version 2` 已设置） |
| apt 源 | 清华镜像（https://mirrors.tuna.tsinghua.edu.cn/ubuntu/） |

> **登录密码提示**：`dev` 的初始密码是 `dev`，只用于本次安装后首次使用。
> 请尽快改成你自己的密码：在 WSL 里执行 `sudo passwd dev`。

## 本机特殊背景

这台机器的系统镜像是精简版：`Microsoft-Windows-Subsystem-Linux` 和
`VirtualMachinePlatform` 原本只有"已启用"的登记状态，实际文件和服务
（`wsl.exe`、`vmcompute.exe`、`LxssManager`、`vmcompute`、`hns`）全部缺失。

修复方式是先用 DISM 重新部署这两个功能，重启后组件才真正落位。
如果以后系统又出现 `wsl` 命令找不到的情况，按同样思路处理：

```powershell
dism /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /featurename:VirtualMachinePlatform /norestart
dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /featurename:VirtualMachinePlatform /all /norestart
# 然后重启
```

## 常用命令

```powershell
wsl                              # 进入默认发行版（dev 用户）
wsl -d Ubuntu-22.04 -e uname -a  # 直接在 Linux 里跑单条命令
wsl -l -v                        # 列出所有发行版和版本类型
wsl --shutdown                   # 关闭所有发行版和 WSL2 轻量虚拟机
wsl --terminate Ubuntu-22.04     # 只关闭这个发行版（改配置后用它让配置生效）
wsl --export Ubuntu-22.04 D:\backup\ubuntu.tar   # 备份
wsl --unregister Ubuntu-22.04    # 删除该发行版（不可恢复，vhdx 会一并删除）
```

注意：Windows 10 自带的 `wsl.exe` 是比较老的版本，**不支持** `wsl --version`
和 `wsl --status` 这两个参数（会报 `Invalid command line option`）。
查看内核版本用 `wsl -e uname -a`。

## 已做的配置

### apt 源换成清华镜像

原文件备份在 `/etc/apt/sources.list.bak`，需要恢复时：

```powershell
wsl -u root -e cp /etc/apt/sources.list.bak /etc/apt/sources.list
```

实测 `apt-get update` 下载 51.1MB 用时 13 秒（约 3.9 MB/s）。

### 默认用户 dev

写入 `/etc/wsl.conf`，保留了原有的 `[boot] systemd=true`：

```ini
[boot]
systemd=true

[user]
default=dev
```

改了用户相关配置后需要 `wsl --terminate Ubuntu-22.04` 才生效。

## 可选：限制 WSL2 内存占用

本机只有 8GB 内存，WSL2 默认最多可用一半。如果希望更严格地限制，
在 `C:\Users\Administrator\.wslconfig` 写入：

```ini
[wsl2]
memory=4GB
processors=2
swap=2GB
```

改完执行 `wsl --shutdown` 生效。

## 已保留的文件

- `C:\WSL\ubuntu22.04-rootfs.tar.gz`（325MB，原始 rootfs，可再次导入）
- `C:\WSL\wsl_update_x64.msi`（16MB，内核更新包，微软官方签名）
