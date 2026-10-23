"""PyInstaller 使用的桌面入口；与命令行入口分开避免自动打开浏览器。"""

from gh_daily.desktop import main

if __name__ == "__main__":
    raise SystemExit(main())
