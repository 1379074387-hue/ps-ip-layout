# Photoshop 执行与验证

## 使用本机实际可用的连接

遵守当前 AGENTS.md；如果要求 Flue，就先读取当前已安装的 Flue skill 和 Photoshop adapter。先检查上下文，不安装或修改系统配置来赌连接成功。

本机曾使用 `/Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app`，报告版本 27.5.0。路径与版本以后可能变化，应检查当前环境，不能假定路径一直有效。

过去 Flue 的 AppleScript 通道出现过 `do javascript` 编译错误和 XPC 无效连接，而 Photoshop 的原生菜单执行 JSX 正常。1–2 次有根据的连接尝试失败后，不重复同一调用，也不立即把工作推回给用户：

1. 检查当前是否提供桌面控制工具。已有可用的 Node REPL 桌面接口时，可导入 `@oai/sky` 并用 `sky.get_app_state({app:'Adobe Photoshop 2026'})` 检查实际界面；只使用当前可用且已了解的 API。
2. 用 PS「文件 → 脚本 → 浏览」运行准备好的 JSX。每次改变菜单或对话框后读取新状态，再使用最新元素索引。
3. 本机曾发现键入中文路径丢字、普通全选快捷键没有替换选中文本。优先用 ASCII 脚本文件名和路径，路径框通过 `set_value` 设置；JSX 内部的 Unicode 文件名正常保留。
4. 如果界面出现“文字图层需要更新”，在此任务输出副本中完成更新，再检查实际排版。不要宣称通过文件写入就等于 PS 验证通过。
5. 报告“通过桌面控制运行原生脚本”，不要把备用方式说成已修复 Flue。只有自动方式不可用时，才给用户一个已准备好的脚本和一次简短运行说明。

脚本应小而有界，执行后读 SUCCESS/ERROR 日志并查看导出预览。本机曾在脚本关闭全部文档后出现菜单不可用；保留最后一份输出文档打开，不要关闭用户文档或反复要求重启。不要安装常驻服务、监听器或改变全局配置。

## 生成可复用 JSX

本 skill 的脚本只生成 JSX，不自动运行 PS，不修改输入文件。它会在 PS 中复制源文档、执行指定动作、保存新的分层 PSD、可选导出 PNG。当前输出名称已经存在时拒绝覆盖；失败会记录 ERROR 并停止后续 job。默认恢复 PS 的对话框和单位偏好，最终文档保持打开。

```bash
python3 scripts/make_photoshop_script.py /absolute/task.json --out /absolute/work/task.jsx
```

把示例中的绝对路径换成当前任务的真实路径。`log` 可省略，默认与生成的 JSX 同名，执行前不能已经存在。检查权限覆盖脚本、日志、输出 PSD 和预览路径。

### A3 适配

```json
{
  "jobs": [{
    "mode": "a3",
    "input": "/absolute/source.psd",
    "output": "/absolute/output-A3.psd",
    "preview": "/absolute/output-A3.png",
    "orientation": "portrait",
    "dpi": 300,
    "paper_layer": "暖米纸张肌理"
  }]
}
```

`paper_layer` 要精确匹配一个实际背景图层，仅用于可延展的纯纸纹或底色。没有这样的层时，可省略并指定 `background: "#F5F0E5"` 新建底层；两项都不指定则保留扩展区透明。详见尺寸参考。

### PS 主体蒙版

```json
{
  "jobs": [{
    "mode": "cutout",
    "input": "/absolute/original.png",
    "output": "/absolute/subject-masked.psd",
    "preview": "/absolute/subject-transparent.png",
    "crop": [100, 475, 860, 1300]
  }]
}
```

`crop` 可省略；采用 `[left, top, right, bottom]` 像素坐标，先在复制的文档中裁到明确目标，再执行 PS 选择主体并加蒙版。不要裁断头发、道具和脚。原始完整文件始终保留。导出的透明 PNG 供排版预览，蒙版 PSD 才是可修边的源。

若选错主体或漏掉稻穗、细枝等，实际在 PS 修改选区/蒙版并复查；不能因为脚本成功就当抠图合格。把透明结果放在灰底检查。

### 把源图嵌入已组装的排版

```json
{
  "jobs": [{
    "mode": "embed_images",
    "input": "/absolute/layout-draft.psd",
    "output": "/absolute/layout-native.psd",
    "preview": "/absolute/layout-native.png",
    "replacements": [
      {"name": "场景完整画面", "file": "/absolute/original.jpg", "frame": [80, 470, 1520, 850], "fit": "contain", "radius": 8},
      {"name": "独立人物素材", "file": "/absolute/subject-masked.psd", "subject": true}
    ]
  }]
}
```

每个待替换图层名称必须唯一；可以在草稿中先明确命名。普通图片按 frame 等比例 cover/contain，添加外部取景蒙版；原图仍内嵌。subject 只用于同一人物素材的预览层与其蒙版 PSD 替换，保留原有包围盒的中心和比例。该模式不执行抠图，源主体蒙版必须已经实际完成。

### 指定文字放大

```json
{
  "jobs": [{
    "mode": "enlarge_text",
    "input": "/absolute/source-A3.psd",
    "output": "/absolute/source-A3-readable.psd",
    "preview": "/absolute/source-A3-readable.png",
    "changes": [
      {"name": "模块标题", "text": "亲切·表情包", "factor": 1.28},
      {"name": "模块英文", "text": "SMILE / EMOJI", "factor": 1.70, "move": [0, 8]}
    ]
  }]
}
```

每条规则用图层名匹配，可加 `text` 和/或 `path`（例如 `第二排/表情/模块标题`）缩小范围。确实要处理多个同名层才指定 `all_matches: true`。多行 `text` 在 JSON 中使用 `\r`。`move` 是放大后的像素位移，可省略。没有匹配或出现歧义时，不交付部分修改的结果，应修正规则另存后重跑。这个模式仅缩放文字层，不更改文字内容。

只需要原生另存和导出验证时用 `mode: "save"`，配相同的 input/output/preview 字段。

## 文件检查

使用有 psd-tools 的已有 Python：

```bash
python scripts/inspect_psd.py /absolute/output.psd --embedded-masks --out /absolute/report.json
python scripts/inspect_psd.py /absolute/readable.psd --compare /absolute/source.psd --out /absolute/comparison.json
```

比较报告会提示新文字间重叠、文字内容变化和非文字层包围盒变化。修改尺寸时非文字层变化正常；只放大文字时应保持不变。智能对象源可能是 JPEG/PNG，无法作为内嵌 PSD 读取不代表损坏；真正的主体蒙版源应能读出嵌套蒙版。不要把所有取景蒙版都称作“真实抠图”。

回读之后仍需查看 Photoshop 导出的预览。路径、日志、验证范围和保存状态以当前实际结果为准。
