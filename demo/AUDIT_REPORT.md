# 当前 Demo 审查报告

## 项目概述
- **英文版**: `/root/eth-beijing-2026/demo/index.html`
- **中文版**: `/root/eth-beijing-2026/demo/index-zh.html`
- **Docs 英文版**: `/root/eth-beijing-2026/demo/docs/en/index.html`
- **Docs 中文版**: `/root/eth-beijing-2026/demo/docs/zh/index.html`
- **GitHub 仓库**: `https://github.com/tiyadegure/eth-beijing-2026`

---

## 链接问题

### 1. [中等] View Report 按钮无功能
- **位置**: Hero 终端区域右上角 `#btnReport`
- **问题**: 按钮只有 `id="btnReport"`，没有 `onclick` 或 `href`，点击无任何效果
- **影响**: 用户点击后无反应，体验差

### 2. [轻微] Docs 链接使用相对路径
- **位置**: 导航栏 `docs/en/` 和 `docs/zh/`
- **问题**: 使用相对路径，如果 demo 不在根目录部署可能 404
- **建议**: 考虑使用绝对路径或确保部署结构一致

### 3. [通过] GitHub 链接正确
- 导航栏、Hero 按钮、Footer 均指向 `https://github.com/tiyadegure/eth-beijing-2026` ✓

### 4. [通过] 语言切换链接正确
- EN → `index-zh.html` ✓
- ZH → `index.html` ✓

### 5. [轻微] Footer 缺少 Docs 链接
- Footer Resources 区域没有指向文档的链接

---

## 显示问题

### 1. [严重] 字体加载不一致
- **英文版**: 只加载 `Inter` 字体
- **中文版**: 加载 `Inter` + `Noto Sans SC` 字体
- **问题**: 英文版 CSS 变量声明了 `'Noto Sans SC'` 但未实际加载该字体
- **影响**: 英文版如果包含中文字符会 fallback 到系统字体

### 2. [中等] 搜索图标字符兼容性
- **位置**: `.search-icon` 使用 `⌕` (U+2315 TELEPHONE RECORDER)
- **问题**: 该字符在某些系统/浏览器上可能显示为方框或不显示
- **建议**: 使用 SVG 图标或更通用的 Unicode 字符

### 3. [中等] 终端 Emoji 显示一致性
- **位置**: 终端动画中的 🔍 🧠 📚 🔄 ✅ 🛡️ 🔧 🔗
- **问题**: Emoji 在不同操作系统渲染差异大，Windows 可能显示为黑白
- **建议**: 考虑使用纯文本标记或 SVG 图标

### 4. [轻微] Stats Bar backdrop-filter 无效
- **位置**: `.stats-bar`
- **代码**: `backdrop-filter:blur(20px)`
- **问题**: 背景是不透明的 `var(--canvas-parchment)` (#f5f5f7)，blur 效果不可见
- **建议**: 移除或改用半透明背景

### 5. [轻微] 搜索结果在暗色背景上对比度不足
- **位置**: Knowledge Layer 搜索结果
- **问题**: `.search-result` 使用 `background:rgba(255,255,255,.06)` 在暗色背景上太暗
- **建议**: 提高不透明度至 0.1 或使用更明显的背景色

### 6. [通过] 响应式布局
- 4 个断点 (1068px, 833px, 640px, 419px) 覆盖完整 ✓
- 移动端按钮堆叠、卡片单列显示正常 ✓

### 7. [通过] 颜色一致性
- Demo 和 Docs 的 CSS 变量完全一致 ✓
- 主色 #0066cc / #2997ff 保持统一 ✓

---

## 功能问题

### 1. [严重] RAG 搜索是假数据
- **位置**: `#ragInput` 搜索框
- **问题**: 搜索结果来自硬编码的 `fakeData` 数组，不是真实 API 调用
- **代码**: `const fakeData = [...]` 直接在前端定义
- **影响**: 演示时如果评委深入测试会发现是假的

### 2. [严重] View Report 按钮无功能
- **问题**: 按钮在终端动画完成后显示，但点击无任何效果
- **建议**: 应链接到实际报告或显示模态框

### 3. [中等] 终端动画无法重播
- **问题**: 动画播放一次后结束，用户无法重新触发
- **建议**: 添加重播按钮或自动循环

### 4. [轻微] 滚动动画不重置
- **问题**: `.reveal` 元素进入视口后添加 `in-view` 类，但滚动离开后不移除
- **影响**: 用户向下滚动后返回顶部，再向下滚动时动画不会重新触发
- **代码**: Observer 只添加类，没有 `else` 分支移除

### 5. [通过] 语言切换功能
- EN ↔ ZH 切换正常 ✓

### 6. [通过] 平滑滚动
- Hero 按钮 `scrollIntoView({behavior:'smooth'})` 正常 ✓

---

## 一致性问题

### 1. [严重] Demo 与 Docs 设计风格完全不同
- **Demo**: Apple 风格单页设计，自定义 CSS，无框架
- **Docs**: MkDocs Material 主题，标准文档布局
- **差异**:
  - Demo 有固定顶部导航栏 (44px 黑色)
  - Docs 有 Material 风格侧边栏导航
  - Demo 无面包屑、无目录树
  - Docs 无 Hero 区域、无终端动画
- **建议**: 重写时统一设计语言，或明确区分用途

### 2. [中等] Docs 使用不同字体栈
- **Demo**: `'Inter','Noto Sans SC',system-ui,...`
- **Docs**: `'Inter','SF Mono'` (通过 MkDocs Material 配置)
- **问题**: 中文文档可能 fallback 到非预期字体

### 3. [轻微] Logo 实现方式不同
- **Demo**: 文字 `◆ AuditAI`
- **Docs**: SVG 图标 (MkDocs Material 默认)
- **建议**: 统一使用 SVG Logo

### 4. [轻微] Favicon 可能不一致
- **Demo**: 无 Favicon 声明
- **Docs**: 使用 `../assets/images/favicon.png`
- **建议**: Demo 也添加 Favicon

---

## 代码质量观察

### 1. [中等] 内联样式过多
- 所有 CSS 都在 `<style>` 标签内 (~350 行)
- 所有 JS 都在 `<script>` 标签内 (~100 行)
- **影响**: 维护困难，无法缓存
- **建议**: 重写时分离为独立文件

### 2. [轻微] 无 meta description
- Demo 页面没有 `<meta name="description">`
- **影响**: SEO 和社交分享预览

### 3. [轻微] 无 Open Graph 标签
- 缺少 `og:title`, `og:description`, `og:image`
- **影响**: 社交媒体分享时无预览卡片

---

## 建议

### 重写优先级
1. **P0 - 必须修复**:
   - View Report 按钮功能
   - RAG 搜索接入真实 API 或更真实的模拟
   - 字体加载一致性

2. **P1 - 强烈建议**:
   - Demo 与 Docs 设计统一
   - 分离 CSS/JS 文件
   - 添加 Favicon 和 Meta 标签

3. **P2 - 可选优化**:
   - 终端动画重播功能
   - 滚动动画重置
   - 搜索图标改用 SVG
   - Stats Bar 移除无效 blur

### 重写方向建议
1. 考虑使用 Next.js 或 Astro 构建，支持 SSR/SSG
2. 组件化：Hero、Terminal、SearchResult 等独立组件
3. 接入真实数据源或使用更高级的模拟（如 MSW）
4. 统一 Demo 和 Docs 的设计系统
5. 添加暗色模式支持（当前只有部分区域是暗色）

---

## 文件清单

| 文件 | 大小 | 状态 |
|------|------|------|
| `demo/index.html` | 27KB | 需重写 |
| `demo/index-zh.html` | 27KB | 需重写 |
| `demo/docs/en/index.html` | 由 MkDocs 生成 | 需更新配置 |
| `demo/docs/zh/index.html` | 由 MkDocs 生成 | 需更新配置 |
| `demo/docs/stylesheets/extra.css` | 自定义覆盖 | 需更新 |
| `demo/assets/` | SVG logos | 可复用 |

审查完成于 2026-06-07
