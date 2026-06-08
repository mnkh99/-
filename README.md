
# I Don't Know Less Than You

This is a Warcraft Logs timeline tool built for World of Warcraft healer players.

It did not begin as a grand software project. It started from one very specific, very practical question:

> Where should a Mistweaver Monk actually press cooldowns?

From that question, we gradually shaped it into a desktop app that can read WCL reports, detect dungeons and bosses, and display boss abilities, healing cooldowns, defensives, trinkets and potions, deaths, health lines, damage taken, and healing intensity on a single timeline.

Its goal is not to replace Warcraft Logs, and it is not trying to become an intimidating data platform. It is closer to a dungeon review companion for healers: it gathers scattered log information into one readable timeline, so you can quickly see when danger happens, when teammates drop low, whether cooldowns covered key moments, and where you should prepare earlier next time.

The app follows a few clear design principles:

1. **Built for real healer review, not for showing off.**  
   Every feature exists to help players understand fights, plan cooldowns, and reduce bad reads.

2. **Configuration should be extendable.**  
   Dungeons, bosses, abilities, potions, and defensives are kept as configurable as possible, so the tool can keep growing with seasons, affixes, and player needs.

3. **The interface should be approachable.**  
   API tokens, report links, fight selection, config maintenance, and MRT export are all handled inside the app as much as possible. Users should not have to dig through code.

4. **The timeline should serve judgment.**  
   Overview mode helps you scan event distribution. Detail mode combines health lines, damage taken, and healing intensity to show real pressure. The timeline is not pretty for its own sake; it is there to help healers make better decisions.

5. **It should keep a little sense of humor.**  
   “I Don't Know Less Than You” is not a solemn product slogan. It is the app’s personality: a little stubborn, a little funny, but genuinely trying to help you understand the timeline.

The most valuable part of this project is not only the code, but the way it came into being. It grew through real testing, screenshots, feedback, revised requirements, expanded configuration, and small usability fixes. Many features were not “correct” from the start. They became right because someone actually opened the app, inspected a real log, noticed what felt awkward, and we fixed that awkwardness.

So if you use this tool, I hope it does not merely help you memorize a fixed cooldown plan. I hope it helps you understand the fight better: when pressure is raid-wide, when it is a single-target mechanic, when a defensive saves someone, and when the healing gap actually began ten seconds earlier.

It was not made to prove who knows more.

It is simply here to say:

**I don't know less than you, but I can help you see it clearly.**

---

## Features

* Read Warcraft Logs report links and select specific fights.
* Automatically detect Mythic+ dungeons and Boss segments.
* Display Boss abilities, healing cooldowns, personal/raid defensive cooldowns, trinkets, and potions.
* Overview mode for quickly observing event distribution.
* Detail mode for reviewing health curves, damage heatmaps, healing heatmaps, and death information.
* Support MRT-format export for easy copying into in-game notes.
* Maintain `config.yaml` inside the application, with support for adding, deleting, importing, exporting, and restoring configurations.
* Support both Chinese and English interfaces.
* Run as a Windows desktop application after packaging.

## Usage

### Run from Source

1. Install Python 3.14 or a compatible version.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Double-click `start_app.bat`, or run:

```powershell
python app.py
```

4. Save your Warcraft Logs API Token in the application settings.
5. Paste a WCL report link, load the fight list, and generate the timeline.

### Browser Debug Mode

```powershell
python app.py --browser
```

## Build

After installing the dependencies, run the following command in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_one_click.ps1
```

The build output will be located at:

```text
dist\i dont know less than you
```

Compress this directory to share it with other users. Users only need to double-click:

```text
i dont know less than you.exe
```

## Files

* `app.py`: Local service, WCL data fetching, configuration management, and desktop window entry point.
* `index.html`: Frontend interface and timeline rendering.
* `config.yaml`: Configuration for dungeons, Bosses, abilities, defensive cooldowns, trinkets, and potions.
* `title.gif`: Meme image resource displayed below the title.
* `start_app.bat`: One-click startup script for running from source.
* `build_one_click.ps1`: Windows build script.
* `requirements.txt`: Python dependencies.

## Configuration

`config.yaml` is the core of this tool’s future growth. When adding new dungeons, Bosses, or abilities, it is recommended to maintain them through the Config panel inside the application. You may also edit the YAML file manually.

For damage-type Boss abilities, three display strategies are supported:

* `target`: Deduplicate by target. Suitable for targeted DOT effects.
* `interval`: Display at fixed intervals. Suitable for high-frequency damage with a regular rhythm.
* `aura`: Display only the starting point for continuous ground or aura damage.

## Notes

* The WCL API Token is stored locally in `token.txt` and will not be uploaded to the repository.
* Each time the configuration is written through the application, a `config.yaml.bak` file is automatically generated.
* `dist/`, `build/`, `token.txt`, backup files, and packaged build artifacts are not recommended for submission to GitHub.

---

# 我不比你懂

这是一个为《魔兽世界》治疗玩家制作的 Warcraft Logs 时间轴工具。

它最初不是一个宏大的软件项目，而是一个非常具体、非常朴素的问题：

> 奶僧到底应该在哪里开技能？

从这个问题开始，我们一点点把它做成了一个可以读取 WCL 日志、识别副本和 Boss、展示 Boss 技能、治疗技能、减伤、饰品药水、死亡、血线、承伤和治疗热度的桌面程序。

它的目标不是取代 Warcraft Logs，也不是做一个复杂到让人敬畏的数据平台。它更像一个治疗玩家身边的副本复盘助手：把日志里分散的信息收拢到同一条时间线上，让你能更快看清“危险什么时候发生”“队友什么时候掉血”“技能有没有覆盖到关键点”“下一次我该提前在哪里做准备”。

这个程序有几个很明确的设计原则：

1. **面向实际治疗复盘，而不是炫技。**  
   所有功能都围绕“看懂战斗、安排技能、减少误判”展开。

2. **配置应该能扩展。**  
   副本、Boss、技能、药水和减伤都尽量放进配置文件里，让它可以随着赛季、词缀和玩家需求继续成长。

3. **界面要让普通玩家敢用。**  
   Token、日志链接、战斗选择、配置维护、导出 MRT，都尽量放在软件内完成，不要求用户去翻代码。

4. **时间轴应该服务判断。**  
   Overview 用来快速看事件分布，Detail 用来结合血线、承伤和治疗热度看真实压力。它不是为了漂亮而漂亮，而是为了让治疗玩家更快做决定。

5. **它保留一点幽默感。**  
   “I Don't Know Less Than You” 不是一句严肃的产品宣言，更像这个工具的性格：有点嘴硬，有点好笑，但确实想帮你把轴抄明白。

这个项目最珍贵的地方，不只是代码，而是它的形成过程。它是在一次次真实测试、截图反馈、需求修正、配置补全和细节打磨里长出来的。很多功能不是一开始就“设计正确”的，而是因为用户真正打开软件、真的去看一场日志、真的觉得哪里别扭，然后我们把那个别扭修掉。

所以如果你正在使用它，希望它帮你的不是背一份死轴，而是更好地理解战斗：什么时候危险是全队压力，什么时候只是单点点名，什么时候减伤是救命，什么时候治疗缺口其实早在十几秒前就已经出现。

它不是为了证明谁比谁懂。

它只是想说：

**我不比你懂，但我可以陪你一起看明白。**

---

## 功能 / Features

- 读取 Warcraft Logs 报告链接并选择具体战斗。
- 自动识别大秘境副本与 Boss 分段。
- 展示 Boss 技能、治疗 CD、个人/团队减伤、饰品和药水。
- Overview 模式用于快速观察事件分布。
- Detail 模式用于查看血线、承伤热度、治疗热度和死亡信息。
- 支持 MRT 格式导出，方便复制到副本内笔记。
- 软件内维护 `config.yaml`，可添加、删除、导入、导出和恢复配置。
- 支持中英文界面。
- 打包后作为 Windows 桌面应用窗口运行。

## 使用方式 / Usage

### 直接运行源码

1. 安装 Python 3.14 或兼容版本。
2. 安装依赖：

```powershell
python -m pip install -r requirements.txt
```

3. 双击 `start_app.bat`，或运行：

```powershell
python app.py
```

4. 在软件设置里保存 Warcraft Logs API Token。
5. 粘贴 WCL 报告链接，读取战斗列表，生成时间轴。

### 浏览器调试模式

```powershell
python app.py --browser
```

## 打包 / Build

安装依赖后，在 PowerShell 中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_one_click.ps1
```

打包输出位于：

```text
dist\i dont know less than you
```

压缩这个目录即可发给其他用户。用户只需要双击：

```text
i dont know less than you.exe
```

## 文件说明 / Files

- `app.py`：本地服务、WCL 数据读取、配置维护和桌面窗口入口。
- `index.html`：前端界面和时间轴渲染。
- `config.yaml`：副本、Boss、技能、减伤、饰品和药水配置。
- `title.gif`：标题下方的梗图资源。
- `start_app.bat`：源码运行的一键启动脚本。
- `build_one_click.ps1`：Windows 打包脚本。
- `requirements.txt`：Python 依赖。

## 配置说明 / Config

`config.yaml` 是这个工具继续成长的核心。后续添加新副本、Boss 或技能时，优先在软件的 Config 面板内维护；也可以手动编辑 YAML。

对 damage 类型 Boss 技能，支持三种显示策略：

- `target`：按目标去重，适合点名 DOT。
- `interval`：固定间隔显示，适合高频但有节奏的伤害。
- `aura`：连续场地/光环伤害只显示开始点。

## 注意 / Notes

- WCL API Token 会保存在本地 `token.txt`，不会上传到仓库。
- 每次通过软件写入配置时，会自动生成 `config.yaml.bak`。
- `dist/`、`build/`、`token.txt`、备份文件和打包产物不建议提交到 GitHub。

