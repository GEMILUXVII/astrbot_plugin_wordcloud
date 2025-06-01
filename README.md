# <div align="center">☁️ CloudRank</div>

<div align="center"><em>智能词云分析 · 聊天热度排行</em></div>

<br>

<div align="center">
  <a href="#-更新日志"><img src="https://img.shields.io/badge/version-v1.3.8--rev1-blueviolet?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_cloudrank/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"></a>
  <a href="https://github.com/AstrBotDevs/AstrBot"><img src="https://img.shields.io/badge/AstrBot-Compatible-00d4aa?style=for-the-badge&logo=robot&logoColor=white" alt="AstrBot Compatible"></a>
</div>

<div align="center">
  <a href="https://github.com/botuniverse/onebot-11"><img src="https://img.shields.io/badge/OneBotv11-AIOCQHTTP-1e90ff?style=for-the-badge&logo=qq&logoColor=white" alt="OneBot v11 Support"></a>
  <a href="https://github.com/WeChatPadPro/WeChatPadPro"><img src="https://img.shields.io/badge/WeChat-PadPro-07c160?style=for-the-badge&logo=wechat&logoColor=white" alt="WeChatPadPro Support"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_cloudrank/commits/main"><img src="https://img.shields.io/badge/updated-2025--05--30-brightgreen?style=for-the-badge&logo=calendar&logoColor=white" alt="Last Updated"></a>
</div>

## 👥 插件贡献者

<p align="center">
  <a href="https://github.com/GEMILUXVII" target="_blank">
    <img src="https://github.com/GEMILUXVII.png" width="60" height="60" alt="GEMILUXVII" style="border-radius: 50%; margin: 0 10px;">
  </a>
  <a href="https://github.com/xu-wish" target="_blank">
    <img src="https://github.com/xu-wish.png" width="60" height="60" alt="xu-wish" style="border-radius: 50%; margin: 0 10px;">
  </a>
</p>

## 📝 介绍

CloudRank 插件是一款用于 AstrBot 的插件，能够将群聊或私聊中的文本消息进行分析，并生成美观的词云图像。通过词云，用户可以直观地了解一段时间内聊天内容的关键词和热点话题。插件同时提供用户活跃度排名功能，展示群内最活跃的成员。插件支持自动定时生成和手动触发生成，并提供了丰富的配置选项，让您可以定制个性化的词云和排名显示。

## ✨ 功能特性

- 🕒 **定时自动生成**：支持 Cron 表达式配置，定时为指定群聊或所有启用的会话生成词云
- 📅 **每日词云**：可在每日固定时间生成当天的聊天词云并推送到指定群聊，可自定义标题
- ⌨️ **手动触发生成**：用户可以通过命令手动生成指定天数内的聊天词云
- 🖼️ **多种视觉定制**：
  - **背景颜色**：自定义词云图片的背景色
  - **配色方案**：选择不同的预设配色方案，改变词语的颜色分布
  - **字体**：支持指定自定义字体文件，解决特殊字符显示问题或实现特定视觉风格
  - **形状**：支持预设形状（如圆形、矩形、菱形、三角形），更重要的是支持通过 **自定义蒙版图片 (`custom_mask_path`)** 来定义任意词云轮廓
- ⚙️ **灵活的配置管理**：
  - **群聊启用/禁用**：可以指定哪些群聊启用词云功能
  - **词语过滤**：设置最小词长度、最大词数量
  - **停用词**：支持自定义停用词列表，过滤常见但无意义的词语
  - **机器人消息统计**：可配置是否将机器人自身发送的消息计入词云统计 (`include_bot_messages`)
- 📊 **用户活跃度排行**：
  - 词云生成后自动显示群内活跃用户排行榜
  - 可自定义排行显示人数和奖牌样式
  - 显示用户名称和发言贡献度
- 📜 **消息历史记录**：插件会自动记录消息用于分析，用户无需额外操作
- 🚀 **易于使用**：提供简洁的命令进行交互
- 🐛 **调试模式**：可选的详细日志输出，方便排查问题

## 📱 支持平台

CloudRank 插件基于 AstrBot 平台开发：

- **QQ**：支持 QQ 群聊的词云生成
- **微信**：支持基于 WeChatPadPro 微信群聊的词云生成

## 🚀 安装方法

1.  **下载插件**:
    - 通过 `git clone https://github.com/GEMILUXVII/astrbot_plugin_cloudrank.git` 克隆仓库到本地
2.  **放置插件文件**:
    - 解压下载的压缩包
    - 将整个插件文件夹 ( `CloudRank`) 复制到 AstrBot 的插件目录: `AstrBot/data/plugins/`
    - 最终路径应为 `AstrBot/data/plugins/cloudrank/`
3.  **安装依赖**:
    - 打开终端或命令行，进入插件目录: `cd AstrBot/data/plugins/cloudrank/`
    - 安装所需的 Python 包: `pip install -r requirements.txt`
4.  **重启 AstrBot**:
    - 完全重启 AstrBot 以加载新插件
5.  **配置插件**:
    - 在 AstrBot 的插件管理界面找到 "CloudRank" 插件，进行相关配置

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
    <td><code>timezone</code></td>
    <td><code>string</code></td>
    <td>自定义插件使用的时区</td>
    <td><code>Asia/Shanghai</code></td>
    <td>有效的 IANA 时区名称，例如 `Asia/Shanghai`, `Europe/London`, `America/New_York`, 或者 `UTC`</td>
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
    <td>以英文逗号分隔的群号列表，例如 <code>123456789,987654321</code>。仅在此处填写的群号才会启用词云功能。如果留空，则默认所有群聊都不启用词云功能</td>
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
    <td><code>min_word_frequency</code></td>
    <td><code>int</code></td>
    <td>最小词频</td>
    <td><code>1</code></td>
    <td>出现次数低于此值的词将被过滤，以优化词云视觉效果，设为1则不过滤</td>
  </tr>
  <tr>
    <td><code>min_font_size</code></td>
    <td><code>int</code></td>
    <td>词云中最小字体大小</td>
    <td><code>8</code></td>
    <td>控制低频词汇的最小显示字体大小，与max_font_size配合调整词云的字体大小对比度</td>
  </tr>
  <tr>
    <td><code>max_font_size</code></td>
    <td><code>int</code></td>
    <td>词云中最大字体大小</td>
    <td><code>170</code></td>
    <td>控制高频词汇的最大显示字体大小，与min_font_size配合调整词云的字体大小对比度，使高频词更加突出</td>
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
    <td>指定一个文本文件，每行包含一个要忽略的词语。路径相对于插件 <code>resources/</code> 目录或绝对路径</td>
  </tr>
  <tr>
    <td><code>include_bot_messages</code></td>
    <td><code>bool</code></td>
    <td>是否将机器人自身的消息计入词云统计</td>
    <td><code>false</code></td>
    <td><code>true</code> 时，机器人自己发送的消息也会被用于生成词云。默认为关闭</td>
  </tr>
  <tr>
    <td><code>shape</code></td>
    <td><code>string</code></td>
    <td>词云的预设形状</td>
    <td><code>rectangle</code></td>
    <td>支持 <code>rectangle</code> (矩形), <code>circle</code> (圆形), <code>diamond</code> (菱形), <code>triangle_up</code> (上三角)。如果设置了下方的"自定义蒙版图片路径"，则此选项无效</td>
  </tr>
  <tr>
    <td><code>custom_mask_path</code></td>
    <td><code>string</code></td>
    <td>自定义蒙版图片路径</td>
    <td><code>&quot;&quot;</code> (空字符串)</td>
    <td>提供一个图片文件的路径作为词云的形状蒙版：图片中白色区域将被忽略，非白色区域将用于绘制词语。如果设置了此路径，则预设的 '形状' 选项将无效。支持相对路径（相对于插件数据目录下的 <code>resources/images/</code> 子目录）或绝对路径</td>
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
    <td>生成当前会话 (群聊或私聊) 的词云，可选择指定统计过去多少天的消息</td>
    <td><code>/wordcloud</code> (使用默认天数) <br> <code>/wordcloud 3</code> (最近3天)</td>
  </tr>
  <tr>
    <td><code>/wc help</code></td>
    <td>显示本插件的帮助信息，包括命令列表</td>
    <td><code>/wc help</code></td>
  </tr>
  <tr>
    <td><code>/wc test</code></td>
    <td>生成测试词云，无需历史数据</td>
    <td><code>/wc test</code></td>
  </tr>
  <tr>
    <td><code>/wc today</code></td>
    <td>手动触发生成当前会话今天的词云</td>
    <td><code>/wc today</code></td>
  </tr>
  <tr>
    <td><code>/wc enable [群号]</code></td>
    <td>在指定群聊启用词云功能，如果未提供群号，则在当前群聊启用 (管理员权限)</td>
    <td><code>/wc enable 123456789</code></td>
  </tr>
  <tr>
    <td><code>/wc disable [群号]</code></td>
    <td>在指定群聊禁用词云功能，如果未提供群号，则在当前群聊禁用 (管理员权限)</td>
    <td><code>/wc disable 123456789</code></td>
  </tr>
  <tr>
    <td><code>/wc force_daily</code></td>
    <td>强制为所有配置了每日词云的会话立即生成一次每日词云(管理员权限) </td>
    <td><code>/wc force_daily</code></td>
  </tr>
</table>

## 🗣️ 自然语言关键词

除了上述命令外，您还可以使用以下自然语言关键词触发相应功能：

<table width="100%">
  <tr>
    <th width="25%">关键词</th>
    <th width="40%">功能描述</th>
    <th width="35%">等效命令</th>
  </tr>
  <tr>
    <td>今日词云<br>获取今日词云<br>查看今日词云<br>生成今日词云</td>
    <td>生成当前会话今天的词云图</td>
    <td><code>/wc today</code></td>
  </tr>
  <tr>
    <td>生成词云<br>查看词云<br>最近词云<br>历史词云</td>
    <td>生成最近7天（或配置的默认天数）的词云图</td>
    <td><code>/wordcloud</code></td>
  </tr>
  <tr>
    <td>词云帮助<br>词云功能<br>词云说明<br>词云指令</td>
    <td>显示词云插件的帮助信息</td>
    <td><code>/wc help</code></td>
  </tr>
</table>

> [!TIP]
>
> 使用自然语言关键词可以更方便地触发功能，无需记忆复杂的命令格式

### 自定义关键词

如果您想添加或修改触发关键词，可以编辑 `constant.py` 文件中的 `NATURAL_KEYWORDS` 字典：

```python
# 自然语言关键词 - 用于触发命令的关键词
# 格式: {"command": ["关键词1", "关键词2", ...]}
NATURAL_KEYWORDS = {
    "today": ["今日词云", "获取今日词云", "查看今日词云", "生成今日词云"],
    "wordcloud": ["生成词云", "查看词云", "最近词云", "历史词云"],
    "help": ["词云帮助", "词云功能", "词云说明", "词云指令"],
}
```

您可以根据需要添加新的命令和关键词，或者为现有命令添加更多关键词。修改后重启机器人即可生效

## 🖼️ 词云样例

![Image](https://i.imgur.com/GdOOd7y.png)

> [!NOTE]
>
> <small><i>上图词云样例采用以下主要配置生成：`max_word_count`: 50, `min_word_length`: 2, `min_word_frequency`: 2, `min_font_size`: 8, `max_font_size`: 170, `background_color`: pink, `colormap`: magma, `font_path`: (使用内置霞鹜文楷), `shape`: circle.</i></small>

## 📁 项目结构 (简化)

```
cloudrank/
├── wordcloud_core/           # 核心词云生成与管理逻辑
│   ├── generator.py          # 词云图像生成器
│   ├── history_manager.py    # 聊天历史记录管理
│   ├── scheduler.py          # 定时任务调度器
│   └── __init__.py           # 包初始化文件
├── fonts/                    # 字体文件目录
├── _conf_schema.json         # 插件配置文件结构定义
├── main.py                   # 插件主逻辑 (Star 类定义)
├── constant.py               # 插件内部常量和自然语言关键词配置
├── utils.py                  # 工具函数
├── stop_words.txt            # 默认停用词列表
├── requirements.txt          # Python 依赖包列表
├── metadata.yaml             # 插件元数据 (供 AstrBot 识别)
├── LICENSE                   # 开源许可证
└── README.md                 # 本说明文档
```

数据目录结构 (通过 StarTools.get_data_dir 动态创建):

```
AstrBot/data/plugin_data/cloudrank/
├── resources/                # 资源文件目录
│   ├── fonts/                # 字体文件目录（存放LXGWWenKai-Regular.ttf等字体）
│   ├── images/               # 自定义蒙版图片存放目录 (例如 my_mask.png)
│   └── stop_words.txt        # 自定义停用词列表
├── images/                   # 生成的词云图片缓存目录 (这是插件输出图片的目录)
└── debug/                    # 调试信息目录（仅在排查问题时使用）
```

## ⚙️ 高级说明与定制

- **自定义停用词**: 编辑位于数据目录的 `resources/stop_words.txt` 文件，每行添加一个不想出现在词云中的词
- **自定义字体**: 将字体文件 (如 `.ttf`, `.otf`) 放入数据目录 `resources/fonts/` 下，然后在插件配置中将 `font_path` 设置为该字体文件的名称 (例如 `my_font.ttf`)。如果字体在系统其他位置，可以设置绝对路径
- **自定义词云形状 (使用蒙版图片)**:
  1.  **准备蒙版图片**:
      - 创建一个图像文件 (推荐使用 `.png` 格式，背景透明更佳，但 `.jpg` 等常见格式也可以)
      - 在图片中，**您希望词语出现的区域应该是深色（如黑色）**，而**希望留空的背景区域应该是浅色（如白色）**。词云生成器会将图片中接近纯黑色的部分作为词语填充的有效区域，纯白色部分则会忽略
      - 图片尺寸会影响最终词云的分辨率和细节，但插件会尝试适应。一个几百像素到一千像素宽高的图片通常效果不错
  2.  **放置蒙版图片**:
      - 将您的蒙版图片文件（例如 `my_mask.png`）放置到插件的数据目录下的 `resources/images/` 子目录中，这个目录的完整路径通常是 `AstrBot/data/plugin_data/cloudrank/resources/images/`，如果该 `images` 子目录不存在，插件在启动时会自动创建它
  3.  **配置插件**:
      - 在 AstrBot 的插件管理界面，找到 "CloudRank" 插件的配置
      - 在 **"自定义蒙版图片路径 (`custom_mask_path`)"** 配置项中，填入您放置的图片文件名，例如 `my_mask.png`
      - **注意**: 如果您在这里配置了有效的图片路径，那么预设的 "词云的预设形状 (`shape`)" 配置项将会被忽略
  4.  **重新加载/测试**:
      - 保存配置后，建议重新加载插件或重启 AstrBot (如果插件管理界面支持热重载，则可能无需重启)
      - 然后尝试生成一个词云 (例如使用 `/wc test` 命令) 来查看自定义形状的效果
- **自定义时区**:
  - 插件允许您配置运行时使用的时区，这对于确保定时任务（如每日词云生成、CRON 表达式定义的任务）按照您期望的本地时间执行至关重要
  - **配置方法**: 在 AstrBot 的插件管理界面，找到 "CloudRank" 插件的配置中的 **"自定义插件使用的时区 (IANA 时区名称) (`timezone`)"** 选项
  - **有效值**: 您需要输入一个有效的 IANA 时区名称，例如 `Asia/Shanghai` (默认值), `Europe/London`, `America/New_York`, 或者 `UTC`
  - 您可以参考 [维基百科的时区列表](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) 或通过 Python 的 `pytz.all_timezones` (如果您熟悉 Python 环境) 来查找合适的时区名称
  - **影响范围**: 此设置会影响所有与时间相关的调度，包括每日词云的生成时间和 CRON 任务的触发时间

## ⚠️ 注意事项

- **首次使用**: 首次生成词云或插件加载时，可能需要一些时间来初始化分词库 (如 `jieba`) 和其他资源
- **中文字体**: 为确保中文在词云中正确显示，建议在配置中明确指定一个包含中文字符的字体路径 (`font_path`)。插件会尝试使用内置的霞鹜文楷字体，如果加载失败或需要特定字体，则此配置项非常重要
- **资源存储**: 插件会在 AstrBot 的数据目录 (通常是 `AstrBot/data/plugin_data/cloudrank/` 或由 `StarTools.get_data_dir(PLUGIN_NAME)` 返回的路径) 下存储字体、停用词和生成的图片缓存。此目录包含三个主要子目录：`resources/`（存放字体和停用词）、`images/`（存放生成的词云图片）和`debug/`（存放调试信息）。请确保 AstrBot 运行的用户对此目录有读写权限，并有足够的存储空间
- **消息数据存储与 session_id 标准化**:
  - 本插件的消息历史记录存储在 **AstrBot 核心的中央 SQLite 数据库**中 (通常是 `AstrBot/data/data_v3.db` 或类似路径)，具体表名为 `wordcloud_message_history`。插件本身不在其独立的插件数据目录下创建数据库文件
  - 这一更改意味着，更新插件后，新记录的群聊消息将使用此标准 ID。旧的群聊消息如果之前是按其他 `session_id` 格式存储的，可能不会被包含在更新后的群聊词云查询中，除非进行数据迁移。查看或备份消息数据需要访问 AstrBot 的主数据库
- **消息内容与统计范围**:
  - 本插件设计的初衷是基于**文本内容**生成词云。因此，在记录消息时，只有那些实际包含文本的消息才会被存储到 `wordcloud_message_history` 数据库表中。纯图片、文件、系统提示、语音消息或大部分表情符号（如果它们没有附带文本描述）等非文本内容将**不会**被记录，也不会计入词云生成的消息总数中
  - 因此，插件报告的"共统计了 X 条消息"或"共产生 X 条发言"是指在指定时间段内，**被插件记录下来的、包含文本内容的消息数量**，这个数量可能少于您在该聊天中看到的总事件数
- **性能考虑**: 记录和分析大量聊天数据可能会消耗一定的系统资源，对于非常活跃的机器人或服务器资源有限的情况，请适当调整历史记录天数和词云生成频率
- **依赖冲突**: 确保 `requirements.txt` 中列出的依赖版本与您的 Python 环境和其他 AstrBot 插件兼容

## ❓ 问题排查 (FAQ)

- **词云不显示中文/中文显示为方框**:
  - **原因**: 未找到合适的中文字体或配置的字体不包含所需字符
  - **解决**: 在插件配置中设置 `font_path` 为一个有效的中文字体文件路径，可以将字体文件放入 `resources/fonts/` 目录并指定文件名，或使用系统字体的绝对路径
- **命令没有反应**:
  - **原因**: 插件未正确加载、被禁用、命令输入错误或权限不足
  - **解决**: 检查 AstrBot 后台插件是否已启用，查看 AstrBot 日志有无报错，确认命令格式正确，以及执行需要权限的命令时是否拥有相应权限
- **自动生成词云未按时执行**:
  - **原因**: CRON 表达式配置错误、AstrBot 或插件在此期间未运行、或任务调度器出现问题
  - **解决**: 检查 `auto_generate_cron` 和 `daily_generate_time` 的配置格式是否正确，确保 AstrBot 持续运行，查看日志中与 `TaskScheduler` 或词云生成相关的错误
- **如何添加更多停用词**:
  - **解决**: 找到插件的数据目录下的 `resources/stop_words.txt` 文件，直接编辑该文件，每行添加一个词
- **词云颜色不喜欢**:
  - **解决**: 修改配置项 `background_color` 设置背景色，修改 `colormap` 选择不同的词语配色方案
- **自然语言关键词没有触发**:
  - **原因**: 关键词未正确配置、关键词大小写或空格不匹配、或消息被识别为命令
  - **解决**: 确保消息格式完全匹配 `constant.py` 中定义的关键词，包括空格和标点符号，确保消息不以 `/` 开头，否则会被视为命令而非普通消息

## 🔄 更新日志

#### **v1.3.8-rev1** (2025-05-30)

**效果改进**:

- 移除了词云生成时对最大字体大小 (`max_font_size`) 的硬编码上限(原为 120)及 `relative_scaling` 参数的固定设置，允许用户通过配置更自由地控制字体大小

**修复**:

- 修正 `min_word_frequency` 配置项的默认值为 `1`
- 统一了 `_conf_schema.json`, `main.py` 和 `README.md` 中关于 `min_word_frequency` 的默认值描述
- 调整了 `README.md` 中配置项表格的顺序，使其与 `_conf_schema.json` 一致

#### **v1.3.8** (2025-05-30)

**新增功能**:

- 新增 `min_word_frequency` 配置项，允许用户设置词云生成时词语的最小出现频率
- 出现次数低于此配置值的词语将被过滤，有助于生成更清晰、更聚焦高频词汇的词云
- 默认值为 `2`，即词语至少出现 2 次才会被统计，设置为 `1` 则不进行词频过滤

**配置更新：**

- `min_word_frequency`: 控制词云中词语的最小出现次数（默认值：2）

#### **v1.3.7**（2025-05-29）

**平台支持扩展：**

- 新增 WeChatPadPro 平台词云生成支持

**贡献者：**

- 感谢 [@xu-wish](https://github.com/xu-wish) 通过 [PR #9](https://github.com/GEMILUXVII/astrbot_plugin_cloudrank/pull/9) 贡献 WeChatPadPro 平台支持

#### **v1.3.6**（2025-05-28）

**停用词系统更新：**

- 大幅增强停用词过滤系统，从原有的 4 个示例停用词扩展到 700+个综合停用词
- 新增中文常用停用词：的、了、在、和、是等基础词汇
- 新增中文语气词和感叹词：阿、啊、哈哈、呵呵等表情化词汇
- 新增中文代词和指示词：俺们、这个、那个、某些等指代词汇
- 新增中文连词和介词：按照、从而、对于、关于等连接词汇
- 新增英文常用停用词：a、the、and、but 等英文基础词汇
- 新增网络用语和表情符号文字：emmm、哈哈哈、呵呵等网络表达
- 新增常见无意义词汇：东西、事情、情况、方面等模糊词汇
- 新增标点符号和特殊字符过滤支持

**改进效果：**

- 显著提升词云质量，过滤掉无意义的高频词汇
- 让关键词汇更加突出，提高词云的可读性和价值
- 支持中英文混合文本的高质量词云生成

#### **v1.3.5**（2025-05-28）

**新功能：**

- 新增 `min_font_size` 和 `max_font_size` 配置项，允许自定义词云字体大小范围
- 改进字体大小对比度，从默认的 10-120 调整为 8-170，使高频词汇更加突出
- 增强词云视觉效果，提供更好的高低频词汇对比显示

**配置更新：**

- `min_font_size`: 控制低频词汇的最小字体大小（默认值：8）
- `max_font_size`: 控制高频词汇的最大字体大小（默认值：170）
- 这些配置项允许用户根据需要调整词云的视觉对比度

#### **v1.3.4**（2025-05-27）

**重要修复：**

- 修复词云生成时包含群成员@提及 ID 的问题
- 在`segment_text`函数中添加正则表达式过滤，自动移除@用户提及内容
- 确保词云统计结果更加准确和美观，不再出现如"@6emasvii"等用户 ID

#### **v1.3.3**（2025-05-23）

**新功能与改进：**

- 新增 `timezone` 配置项，允许用户为插件任务自定义时区
- 新增 `custom_mask_path` 配置项，允许用户指定自定义图片作为词云形状蒙版
- 新增 `include_bot_messages` 配置项，允许用户选择是否将机器人自身发送的消息计入词云统计

#### **v1.3.2**（2025-05-12）

**优化与修复：**

- 确保每日词云和排行榜统计准确反映当天数据
- 修复 `/wc force_daily`指令 `no attribute 'data_dir'`的问题
- 修复每日词云可能无法正常生成的问题
- 解决排行榜 SQL 查询和消息构建中的问题
- 统一排行榜输出样式，修复会话 ID 格式错误
- 新增用户统计方法，提升灵活性

#### **v1.3.1**（2025-05-11）

**日志与线程改进：**

- 标准化日志输出，便于问题排查
- 解决线程重载警告，提升稳定性

#### **v1.3.0**（2025-05-10）

**性能与安全提升：**

- 修复定时任务重复问题，优化资源管理
- 增强线程安全性，改进词云生成过程
- 完善日志记录，优化性能

#### v1.2.1（2025-05-09）

**关键词与文档更新：**

- 添加自然语言关键词处理，提高命令稳定性
- 完善文档，添加更多使用说明

#### **v1.2.0**（2025-05-08）

**配置逻辑调整：**

- 修改群聊启用逻辑，更新配置文件提示

#### **v1.1.2**（2025-05-08）

**线程安全修复：**

- 解决非主线程生成词云时的 `RuntimeError`

#### **v1.1.1**（2025-05-08）

**会话与日志优化：**

- 修复会话 ID 处理逻辑，优化日志输出

#### **v1.1.0**（2025-05-08）

**功能扩展：**

- 插件更名为 "CloudRank"，新增用户活跃度排行榜功能

#### **v1.0.0**（2025-05-08）

**初始发布：**

- 发布基础词云生成功能，支持多种视觉定制和配置管理

## 📄 许可证

本项目采用 [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.html) 许可证

## 🙏 致谢

本项目基于或参考了以下开源项目:

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) - 提供强大的聊天机器人平台支持
- [LXGW WenKai](https://github.com/lxgw/LxgwWenKai) - 霞鹜文楷字体项目，提供了美观的开源中文字体
