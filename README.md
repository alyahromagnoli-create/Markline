# Markline

成绩管理与 GPA 试算。Windows 单 EXE 便携版，PySide6 + SQLite。

**[下载最新版 Windows EXE](https://github.com/alyahromagnoli-create/Markline/releases/latest)** · [详细使用说明](docs/USER_GUIDE.zh-CN.md)

当前版本：**1.0.1**。无需安装 Python 或开发库，不要求电脑存在 D 盘。

## 功能

- XLS / XLSX / CSV 成绩导入、课程维护、去重更新与导出。
- 多个比较对象、单科最低分反推、多科试算和最高成绩可行性检查。
- 方案快照与数据库备份恢复；全程本地计算。
- 固定四分制：60–89 分对应 (成绩−50)/10，90–100 分为 4.0。优95、良85、中等75、合格/及格65。
- 四六级、形势与政策、零学分课程排除统计。

## 使用与数据

下载 Release 中的 `Markline.exe`，放在可写文件夹后双击。首次解包需要几秒，解包使用 Windows 系统临时目录，程序退出后由运行时清理。

全新使用只需 EXE。保留已有记录时，先退出旧版，再把 EXE 和旁边的 **data** 文件夹一起移动或备份。持续修改的数据独立存储，不能永久写回 EXE。本仓库和下载包不包含真实个人记录。

仅支持本软件说明中的固定计分规则与 60–100 分分析，不会自动执行学校的重修替代政策。手填已舍入 GPA 得到的是基于输入值的估算，请与原始成绩核对。

## 验证范围

27 项项目测试通过；独立 EXE 在清理 Python 环境变量、限制 PATH、中文空格路径和不同工作目录下运行，并验证程序连同 data 复制到新位置后的重启与记录恢复。发布 EXE 与对应 Python 核心源码已核对。

目前仅在本机 Windows 11 x64 验证；尚未在第二台实体电脑、Windows 10 或其他架构实机验证。程序未签名。

## 从源码构建

Windows x64 + Python 3.12：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\build.ps1
```

构建缓存和中间文件放在项目内的 work，输出路径见构建脚本。EXE 仅作为 Release 附件发布。

## 许可

原始应用与图标：**MIT**，见 [LICENSE](LICENSE)。第三方组件保留各自许可，相关原文随源码或便携包附带。
