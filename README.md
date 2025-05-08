# <div align="center">📊 CloudRank </div>

<div align="center">
  <img src="https://img.shields.io/badge/version-v1.1.0-blueviolet?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/AstrBot-Compatible-green?style=flat-square" alt="AstrBot Compatible">
  <img src="https://img.shields.io/badge/updated-2024--05--09-brightgreen?style=flat-square" alt="Last Updated">
</div>

## 📝 介绍

CloudRank插件是一款用于 AstrBot 的插件，能够将群聊或私聊中的文本消息进行分析，并生成美观的词云图像。通过词云，用户可以直观地了解一段时间内聊天内容的关键词和热点话题。插件同时提供用户活跃度排名功能，展示群内最活跃的成员。插件支持自动定时生成和手动触发生成，并提供了丰富的配置选项，让您可以定制个性化的词云和排名显示。

## ✨ 功能特性

- 🕒 **定时自动生成**：支持 Cron 表达式配置，定时为指定群聊或所有启用的会话生成词云。
- 📅 **每日词云**：可在每日固定时间生成当天的聊天词云并推送到指定群聊，可自定义标题。
- ⌨️ **手动触发生成**：用户可以通过命令手动生成指定天数内的聊天词云。
- 🖼️ **多种视觉定制**：
    - **背景颜色**：自定义词云图片的背景色。
    - **配色方案**：选择不同的预设配色方案，改变词语的颜色分布。
    - **字体**：支持指定自定义字体文件，解决特殊字符显示问题或实现特定视觉风格。
    - **形状**：目前支持圆形和矩形两种词云形状。
- ⚙️ **灵活的配置管理**：
    - **群聊启用/禁用**：可以指定哪些群聊启用词云功能。
    - **词语过滤**：设置最小词长度、最大词数量。
    - **停用词**：支持自定义停用词列表，过滤常见但无意义的词语。
- 📊 **用户活跃度排行**：
    - 词云生成后自动显示群内活跃用户排行榜
    - 可自定义排行显示人数和奖牌样式
    - 显示用户名称和发言贡献度
- 📜 **消息历史记录**：插件会自动记录消息用于分析，用户无需额外操作。
- 🚀 **易于使用**：提供简洁的命令进行交互。
- 🐛 **调试模式**：可选的详细日志输出，方便排查问题。

## 🚀 安装方法

1.  **下载插件**:
    *   通过 `git clone https://github.com/GEMILUXVII/astrbot_plugin_cloudrank.git` 克隆仓库到本地。
2.  **放置插件文件**:
    *   解压下载的压缩包。
    *   将整个插件文件夹 ( `CloudRank`) 复制到 AstrBot 的插件目录: `AstrBot/data/plugins/`。
    *   最终路径应为 `AstrBot/data/plugins/cloudrank/`。
3.  **安装依赖**:
    *   打开终端或命令行，进入插件目录: `cd AstrBot/data/plugins/cloudrank/`。
    *   安装所需的 Python 包: `pip install -r requirements.txt`。
4.  **重启 AstrBot**:
    *   完全重启 AstrBot 以加载新插件。
5.  **配置插件**:
    *   在 AstrBot 的插件管理界面找到 "CloudRank" 插件，进行相关配置。

## 🛠️ 配置说明

插件的配置通过 `_conf_schema.json` 文件定义，您可以在 AstrBot 后台的插件配置页面进行修改。以下是主要的配置项及其说明：

<table width="100%">
  <tr>
    <th width="15%">配置项</th>
    <th width="8%">类型</th>
    <th width="25%">描述</th>
    <th width="12%">默认值</th>
    <th width="40%">效果说明</th>
  </tr>
  <tr>
    <td><code>auto_generate_enabled</code></td>
    <td><code>bool</code></td>
    <td>是否启用自动生成词云功能</td>
    <td><code>true</code></td>
    <td><code>true</code> 时，插件会根据 <code>auto_generate_cron</code> 的设置定时生成词云</td>
  </tr>
  <tr>
    <td><code>auto_generate_cron</code></td>
    <td><code>string</code></td>
    <td>自动生成词云的 CRON 表达式</td>
    <td><code>0 20 * * *</code></td>
    <td>标准 CRON 格式 (<code>分 时 日 月 周</code>)。例如，默认值表示每天晚上20:00执行</td>
  </tr>
  <tr>
    <td><code>daily_generate_enabled</code></td>
    <td><code>bool</code></td>
    <td>是否启用每日词云生成功能</td>
    <td><code>true</code></td>
    <td><code>true</code> 时，插件会根据 <code>daily_generate_time</code> 的设置每日生成词云</td>
  </tr>
  <tr>
    <td><code>daily_generate_time</code></td>
    <td><code>string</code></td>
    <td>每日词云的生成时间</td>
    <td><code>23:30</code></td>
    <td>格式为 <code>HH:MM</code>。例如，<code>23:30</code> 表示每天晚上11点30分</td>
  </tr>
  <tr>
    <td><code>daily_summary_title</code></td>
    <td><code>string</code></td>
    <td>每日词云图片的标题模板</td>
    <td><code>"{date} {group_name} 今日词云"</code></td>
    <td>支持占位符: <code>{date}</code> (当前日期), <code>{group_name}</code> (群聊名称)</td>
  </tr>
  <tr>
    <td><code>enabled_group_list</code></td>
    <td><code>string</code></td>
    <td>启用词云功能的群聊列表</td>
    <td><code>""</code> (空字符串)</td>
    <td>以英文逗号分隔的群号列表，例如 <code>123456789,987654321</code>。如果留空，则表示在所有群聊中都启用词云功能 (除非群聊被单独禁用过)</td>
  </tr>
  <tr>
    <td><code>history_days</code></td>
    <td><code>int</code></td>
    <td>手动生成词云时，默认统计的历史消息天数</td>
    <td><code>7</code></td>
    <td>当用户使用 <code>/wordcloud</code> 命令且未指定天数时，将使用此值</td>
  </tr>
  <tr>
    <td><code>max_word_count</code></td>
    <td><code>int</code></td>
    <td>词云图片中显示的最大词语数量</td>
    <td><code>100</code></td>
    <td>控制词云的密集程度和信息量。建议值在 50 到 200 之间</td>
  </tr>
  <tr>
    <td><code>min_word_length</code></td>
    <td><code>int</code></td>
    <td>参与词频统计的最小词语长度</td>
    <td><code>2</code></td>
    <td>小于此长度的词语（通常是单个字或无意义的短词）将被忽略</td>
  </tr>
  <tr>
    <td><code>background_color</code></td>
    <td><code>string</code></td>
    <td>词云图片的背景颜色</td>
    <td><code>white</code></td>
    <td>可以是颜色名称 (如 <code>white</code>, <code>black</code>, <code>lightyellow</code>) 或十六进制颜色代码 (如 <code>#FFFFFF</code>)</td>
  </tr>
  <tr>
    <td><code>colormap</code></td>
    <td><code>string</code></td>
    <td>词云的配色方案，决定词语的颜色</td>
    <td><code>viridis</code></td>
    <td>不同的 Colormap 会给词云带来完全不同的视觉风格。可选值包括: <code>viridis</code>, <code>plasma</code>, <code>inferno</code>, <code>rainbow</code>, <code>jet</code> 等</td>
  </tr>
  <tr>
    <td><code>font_path</code></td>
    <td><code>string</code></td>
    <td>自定义字体文件的路径</td>
    <td><code>""</code> (空字符串)</td>
    <td>如果留空，插件会尝试使用内置的默认字体 (通常是霞鹜文楷) 或系统字体。可指定 <code>.ttf</code> 或 <code>.otf</code> 字体文件</td>
  </tr>
  <tr>
    <td><code>stop_words_file</code></td>
    <td><code>string</code></td>
    <td>停用词文件的路径</td>
    <td><code>stop_words.txt</code></td>
    <td>指定一个文本文件，每行包含一个要忽略的词语。路径相对于插件 <code>resources/</code> 目录</td>
  </tr>
  <tr>
    <td><code>shape</code></td>
    <td><code>string</code></td>
    <td>词云的整体形状</td>
    <td><code>circle</code></td>
    <td>目前支持 <code>circle</code> (圆形) 和 <code>rectangle</code> (矩形)。未来可能支持自定义图片蒙版</td>
  </tr>
  <tr>
    <td><code>show_user_ranking</code></td>
    <td><code>bool</code></td>
    <td>是否在每日词云中显示用户活跃度排行</td>
    <td><code>true</code></td>
    <td><code>true</code> 时，词云生成后会同时显示当天发言最活跃的用户排行榜，包含发言人数统计和贡献度排名</td>
  </tr>
  <tr>
    <td><code>ranking_user_count</code></td>
    <td><code>int</code></td>
    <td>用户排行榜显示的人数</td>
    <td><code>5</code></td>
    <td>设置排行榜显示前多少名活跃用户，建议设置5-10之间的值，过多可能导致排行榜信息过长</td>
  </tr>
  <tr>
    <td><code>ranking_medals</code></td>
    <td><code>string</code></td>
    <td>排行榜奖牌表情</td>
    <td><code>🥇,🥈,🥉,🏅,🏅</code></td>
    <td>用逗号分隔的表情符号，前三名会使用前三个表情，其余位置使用后续表情</td>
  </tr>
  <tr>
    <td><code>debug_mode</code></td>
    <td><code>bool</code></td>
    <td>是否启用详细调试日志</td>
    <td><code>false</code></td>
    <td><code>true</code> 时，插件会在控制台输出更详细的运行信息，主要用于开发者排查问题</td>
  </tr>
</table>

## 💻 使用命令

以下是与词云插件交互的主要命令:

<table width="100%">
  <tr>
    <th width="30%">命令</th>
    <th width="40%">描述</th>
    <th width="30%">示例</th>
  </tr>
  <tr>
    <td><code>/wordcloud [天数]</code></td>
    <td>生成当前会话 (群聊或私聊) 的词云。可选择指定统计过去多少天的消息。</td>
    <td><code>/wordcloud</code> (使用默认天数) <br> <code>/wordcloud 3</code> (最近3天)</td>
  </tr>
  <tr>
    <td><code>/wc help</code></td>
    <td>显示本插件的帮助信息，包括命令列表。</td>
    <td><code>/wc help</code></td>
  </tr>
  <tr>
    <td><code>/wc test</code></td>
    <td>生成测试词云，无需历史数据。</td>
    <td><code>/wc test</code></td>
  </tr>
  <tr>
    <td><code>/wc today</code></td>
    <td>手动触发生成当前会话今天的词云。</td>
    <td><code>/wc today</code></td>
  </tr>
  <tr>
    <td><code>/wc enable [群号]</code></td>
    <td>在指定群聊启用词云功能。如果未提供群号，则在当前群聊启用。 (管理员权限)</td>
    <td><code>/wc enable 123456789</code></td>
  </tr>
  <tr>
    <td><code>/wc disable [群号]</code></td>
    <td>在指定群聊禁用词云功能。如果未提供群号，则在当前群聊禁用。 (管理员权限)</td>
    <td><code>/wc disable 123456789</code></td>
  </tr>
  <tr>
    <td><code>/wc force_daily</code></td>
    <td>强制为所有配置了每日词云的会话立即生成一次每日词云。(管理员权限) </td>
    <td><code>/wc force_daily</code></td>
  </tr>
</table>

**注意**:
*   命令前缀 (`/`) 可能因 AstrBot 的全局配置而有所不同。
*   部分命令可能需要管理员权限。

## 🖼️ 词云样例

![Image](https://github.com/user-attachments/assets/eb622282-7e1a-4a34-9afb-0551ff596e32)

## 📁 项目结构 (简化)

```
cloudrank/
├── wordcloud_core/           # 核心词云生成与管理逻辑
│   ├── generator.py          # 词云图像生成器
│   ├── history_manager.py    # 聊天历史记录管理
│   └── scheduler.py          # 定时任务调度器
├── resources/                # 存放字体、默认停用词等资源
│   ├── fonts/                # 字体文件目录
│   └── stop_words.txt        # 默认停用词列表
├── _conf_schema.json         # 插件配置文件结构定义
├── main.py                   # 插件主逻辑 (Star 类定义)
├── constant.py               # 插件内部常量
├── utils.py                  # 工具函数
├── requirements.txt          # Python 依赖包列表
├── metadata.yaml             # 插件元数据 (供 AstrBot 识别)
└── README.md                 # 本说明文档
```

## ⚙️ 高级说明与定制

*   **自定义停用词**: 编辑位于插件数据目录 `resources/stop_words.txt` 的文件，每行添加一个不想出现在词云中的词。
*   **自定义字体**: 将字体文件 (如 `.ttf`, `.otf`) 放入插件数据目录 `resources/fonts/` 下，然后在插件配置中将 `font_path` 设置为该字体文件的名称 (例如 `my_font.ttf`)。如果字体在系统其他位置，可以设置绝对路径。

## ⚠️ 注意事项

*   **首次使用**: 首次生成词云或插件加载时，可能需要一些时间来初始化分词库 (如 `jieba`) 和其他资源。
*   **中文字体**: 为确保中文在词云中正确显示，建议在配置中明确指定一个包含中文字符的字体路径 (`font_path`)。插件会尝试使用内置的霞鹜文楷字体，如果加载失败或需要特定字体，则此配置项非常重要。
*   **资源存储**: 插件会在 AstrBot 的数据目录 (通常是 `AstrBot/data/plugins/cloudrank/` 或由 `StarTools.get_data_dir(PLUGIN_NAME)` 返回的路径) 下存储字体、停用词、生成的图片缓存以及聊天记录数据库。请确保 AstrBot 运行的用户对此目录有读写权限，并有足够的存储空间。
*   **性能考虑**: 记录和分析大量聊天数据可能会消耗一定的系统资源。对于非常活跃的机器人或服务器资源有限的情况，请适当调整历史记录天数和词云生成频率。
*   **依赖冲突**: 确保 `requirements.txt` 中列出的依赖版本与您的 Python 环境和其他 AstrBot 插件兼容。

## ❓ 问题排查 (FAQ)

*   **词云不显示中文/中文显示为方框**:
    *   **原因**: 未找到合适的中文字体或配置的字体不包含所需字符。
    *   **解决**: 在插件配置中设置 `font_path` 为一个有效的中文字体文件路径。可以将字体文件放入 `resources/fonts/` 目录并指定文件名，或使用系统字体的绝对路径。
*   **命令没有反应**:
    *   **原因**: 插件未正确加载、被禁用、命令输入错误或权限不足。
    *   **解决**: 检查 AstrBot 后台插件是否已启用，查看 AstrBot 日志有无报错，确认命令格式正确，以及执行需要权限的命令时是否拥有相应权限。
*   **自动生成词云未按时执行**:
    *   **原因**: CRON 表达式配置错误、AstrBot 或插件在此期间未运行、或任务调度器出现问题。
    *   **解决**: 检查 `auto_generate_cron` 和 `daily_generate_time` 的配置格式是否正确。确保 AstrBot 持续运行。查看日志中与 `TaskScheduler` 或词云生成相关的错误。
*   **如何添加更多停用词**:
    *   **解决**: 找到插件的 `stop_words.txt` 文件 (通常在插件的 `resources` 目录下或数据存储目录中)，直接编辑该文件，每行添加一个词。
*   **词云颜色不喜欢**:
    *   **解决**: 修改配置项 `background_color` 设置背景色，修改 `colormap` 选择不同的词语配色方案。

## 📋 迭代日志

### v1.1.0
- ✨ 更新插件名称：从"WordCloud"更名为"CloudRank"
- 🔄 添加用户活跃度排行榜功能：
  - 词云生成后自动显示群内活跃用户排行
  - 支持配置排行榜显示人数和奖牌样式
  - 展示用户名称和发言贡献度
- 🛠️ 新增配置选项：
  - `show_user_ranking`: 控制是否显示用户排行榜
  - `ranking_user_count`: 设置排行榜显示的用户数量
  - `ranking_medals`: 自定义排行榜奖牌表情符号

### v1.0.0
- 🚀 初始版本发布
- 📊 基础词云生成功能
- 🕒 支持定时自动生成和手动触发生成
- 🖼️ 多种视觉定制选项（背景颜色、配色方案、字体、形状）
- ⚙️ 灵活的配置管理

## 📄 许可证

本项目采用 [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.html) 许可证。


---


## 🙏 致谢

本项目基于或参考了以下开源项目:

- [AstrBot](https://github.com/shandianlala/AstrBot) - 提供强大的聊天机器人平台支持
- [LXGW WenKai](https://github.com/lxgw/LxgwWenKai) - 霞鹜文楷字体项目，提供了美观的开源中文字体

