# PS高级排版 / ps-ip-layout

用于 Codex 的 Photoshop 排版 skill：参考图片和素材制作 IP 展板、海报与系列版式，保留真正可编辑的文字、智能对象和 Photoshop 蒙版。

## 最简单的使用方法

安装后，把参考图与素材路径发给 Codex，然后说：

> 用 $ps-ip-layout，参考这张图和素材做排版，输出 A3 分层 PSD。

也可以用来处理现有文件：

> 用 $ps-ip-layout，把这个 PSD 改成 A3、300 dpi，等比例适配并保留图层。

> 用 $ps-ip-layout，放大这三张展板里的小标题、英文和说明文字，图片内部的字不动，仍交付 PSD。

## 安装

下载本仓库 ZIP，解压后把整个 `ps-ip-layout` 文件夹放到 `~/.codex/skills/`，最终路径应为：

```text
~/.codex/skills/ps-ip-layout/SKILL.md
```

若解压得到 `ps-ip-layout-main`，将文件夹改名为 `ps-ip-layout` 后再放入。也可让 Codex 按本仓库地址安装这个 skill。通过 Git 获取时，在目标目录尚不存在的情况下可使用：

```bash
git clone https://github.com/1379074387-hue/ps-ip-layout.git ~/.codex/skills/ps-ip-layout
```

在新对话中调用 `$ps-ip-layout`；使用时提供本地可访问的素材与参考。

## 能做什么

- 根据参考建立图文层次、配色、留白与连续系列语言。
- 在 Photoshop 内选择主体、添加可修改蒙版，灰底检查抠图。
- 保留独立文字、图片、底板、装饰和按板块命名的文件夹。
- 原图内嵌为智能对象，以取景蒙版控制画面，避免外部链接丢失。
- A3 横/竖版适配，默认 300 dpi，等比例缩放并补足背景。
- 按文字层级放大小字，检查重叠、越界和可读性。
- 用 Photoshop 实际打开、保存、导出预览，再回读验证 PSD 结构。

完整场景图内部的建筑、产品和包装字不会因为成为智能对象就自动拆层；需要拆分时应另行处理。

## 运行环境

- 需要可用的桌面版 Adobe Photoshop 与 Codex 桌面控制/脚本执行通道。
- 脚本生成器仅使用 Python 标准库；PSD 结构检查器需要已有的 `psd-tools` Python 环境。
- 这套辅助操作已在 macOS、Photoshop 2026（27.5.0）中实测；其他系统和版本需要按当前环境检查连接方式。
- 正常的排版、PS 抠图与尺寸调整不需要额外图像 API 密钥。需要生成新图片时再使用当前可用的图像生成工具。
- 本仓库不捆绑 Photoshop、第三方排版引擎、商业字体或设计素材。

## 文件结构

```text
SKILL.md                         入口与工作约定
agents/openai.yaml               显示名称和调用示例
references/design.md             参考分析与系列版式
references/editing.md            A3 与文字调整
references/photoshop.md          PS 执行、参数与验证
scripts/make_photoshop_script.py  生成原生 Photoshop JSX
scripts/inspect_psd.py            检查 PSD 结构和文字变化
```

参数和使用示例见 [Photoshop 操作参考](references/photoshop.md)。生成器不会自行控制桌面，不覆盖输入文件；应由 Codex 在当前授权范围内执行并检查实际结果。
