# PubMed Skill · Claude Code 文献检索技能

一句话让 Claude Code 完成 PubMed 文献检索与综述准备：多维检索策略、跨库自动去重、元数据提取、CSV 导出、引用生成（GB/T 7714 / Vancouver / APA）。

## 安装

把本仓库 clone 到 Claude Code 的 skills 目录：

```bash
# 用户级（全局可用）
git clone https://github.com/guomarketing-droid/pubmed-skill.git ~/.claude/skills/pubmed

# 或项目级（仅当前项目）
git clone https://github.com/guomarketing-droid/pubmed-skill.git .claude/skills/pubmed
```

依赖：`pip install requests`

## 使用

**对话方式**（装好技能后对 Claude 说）：
- “帮我查一下 roxadustat 治疗 CKD 贫血的临床试验文献”
- “文献检索：儿童地中海贫血铁营养管理，近 5 年”

**命令行方式**：

```bash
python pubmed_search.py "iron deficiency anemia" -n 20 -y 5 -c gbt
```

参数：`-n` 数量 / `-y` 回溯年数 / `-t` 文献类型过滤 / `-c` 引用格式（gbt / vancouver / apa）

## API Key（可选，不设也能用）

不带 key 匿名访问 3 次/秒，日常检索完全够用。想提速到 10 次/秒：

1. 注册 NCBI 账号，免费申请 API Key：<https://www.ncbi.nlm.nih.gov/account/settings/>
2. 设置环境变量：

```bash
# Windows（永久生效）
setx NCBI_API_KEY "你的key"

# macOS / Linux
export NCBI_API_KEY="你的key"
```

## 文件说明

| 文件 | 说明 |
|---|---|
| `SKILL.md` | 技能定义：多维检索策略、过滤器、布尔语法、故障排查 |
| `pubmed_search.py` | 命令行检索工具：CSV 导出 + 引用生成 |
| `search_thalassemia_iron.py` | 定制检索脚本示例（单主题深度检索） |

## License

MIT
