# Remotion + ElevenLabs 视频制作完整教程

> 📚 本文档供 AI Agent 参考，用于创建专业级技术解释视频和动画内容

---

## 📋 目录

1. [核心概念](#核心概念)
2. [组件系统](#组件系统)
3. [动画系统](#动画系统)
4. [时间控制](#时间控制)
5. [音频集成](#音频集成)
6. [渲染配置](#渲染配置)
7. [ElevenLabs 集成](#elevenlabs-集成)
8. [设计系统](#设计系统)
9. [最佳实践](#最佳实践)
10. [完整工作流](#完整工作流)

---

## 核心概念

### Remotion 是什么？

Remotion 是一个 **基于 React 的视频生成框架**，允许你用代码创建视频和动画。

### 核心术语

| 术语 | 说明 |
|------|------|
| **Composition** | 视频组合，定义视频的时长、帧率、尺寸 |
| **Frame** | 帧，视频的最小单位（如 30fps = 每秒 30 帧） |
| **Sequence** | 序列，控制子组件在特定时间范围内显示 |
| **Spring** | 弹簧动画，基于物理的弹性动画 |
| **Interpolate** | 插值，将一个值范围映射到另一个范围 |
| **Timeline** | 时间轴，视频的时间维度 |

---

## 组件系统

### 1. `<AbsoluteFill>` - 全屏填充

```tsx
import { AbsoluteFill } from 'remotion';

// 用途：创建全屏容器
<AbsoluteFill style={{ backgroundColor: '#f5f5f0' }}>
  <div>内容</div>
</AbsoluteFill>
```

**属性：**
- `style` - 内联样式
- `className` - CSS 类名

### 2. `<Sequence>` - 时间序列

```tsx
import { Sequence } from 'remotion';

// 用途：控制子组件在特定时间范围内显示
<Sequence from={0} durationInFrames={100}>
  <Scene1 />
</Sequence>

<Sequence from={100} durationInFrames={150}>
  <Scene2 />
</Sequence>
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `from` | number | 开始帧（从 0 开始） |
| `durationInFrames` | number | 持续帧数 |
| `name` | string | 序列名称（调试用） |
| `layout` | 'absolute-fill' \| 'none' | 布局方式 |

**示例：多场景视频**
```tsx
export const MyVideo: React.FC = () => {
  const { fps } = useVideoConfig();
  
  const scene1Duration = 4.5 * fps; // 4.5秒
  const scene2Duration = 5.5 * fps; // 5.5秒
  
  return (
    <>
      <Sequence from={0} durationInFrames={scene1Duration}>
        <Audio src={staticFile("audio/scene1.mp3")} />
        <Scene1Visual />
      </Sequence>
      
      <Sequence from={scene1Duration} durationInFrames={scene2Duration}>
        <Audio src={staticFile("audio/scene2.mp3")} />
        <Scene2Visual />
      </Sequence>
    </>
  );
};
```

### 3. `<Series>` - 顺序序列

```tsx
import { Series } from 'remotion';

// 用途：自动连续播放多个场景
<Series>
  <Series.Sequence durationInFrames={100}>
    <Scene1 />
  </Series.Sequence>
  <Series.Sequence durationInFrames={150}>
    <Scene2 />
  </Series.Sequence>
</Series>
```

### 4. `<Loop>` - 循环播放

```tsx
import { Loop } from 'remotion';

// 用途：重复播放内容
<Loop durationInFrames={30}>
  <AnimationFrame />
</Loop>
```

### 5. `<Composition>` - 视频组合定义

```tsx
import { Composition } from 'remotion';

// 用途：在 Root.tsx 中定义视频组合
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MyVideo"
      component={MyVideo}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | string | 组合唯一标识 |
| `component` | Component | React 组件 |
| `durationInFrames` | number | 总帧数 |
| `fps` | number | 帧率（通常 30 或 60） |
| `width` | number | 宽度（像素） |
| `height` | number | 高度（像素） |
| `defaultProps` | object | 默认属性 |

---

## 动画系统

### 1. `spring()` - 弹簧动画

```tsx
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';

const frame = useCurrentFrame();
const { fps } = useVideoConfig();

// 基础弹簧动画
const value = spring({
  frame,
  fps,
  config: {
    damping: 10,      // 阻尼（越小越弹）
    mass: 1,           // 质量（越小越快）
    stiffness: 100,    // 刚度（越大越快）
  },
});
```

**参数说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `frame` | - | 当前帧 |
| `fps` | - | 帧率 |
| `from` | 0 | 起始值 |
| `to` | 1 | 结束值 |
| `config.damping` | 10 | 阻尼系数 |
| `config.mass` | 1 | 质量 |
| `config.stiffness` | 100 | 刚度 |
| `config.overshootClamping` | false | 是否阻止过冲 |
| `durationInFrames` | - | 持续帧数 |
| `delay` | 0 | 延迟帧数 |
| `reverse` | false | 是否反向 |

**使用示例：弹性入场**
```tsx
const scale = spring({
  frame,
  fps,
  config: { damping: 15, stiffness: 200 },
});

<div style={{
  transform: `scale(${scale})`,
  opacity: scale,
}}>
  弹性显示的内容
</div>
```

**使用示例：延迟动画**
```tsx
// 延迟 20 帧后开始动画
const value = spring({
  frame: Math.max(0, frame - 20), // 关键：frame - delay
  fps,
});
```

### 2. `interpolate()` - 线性插值

```tsx
import { interpolate, useCurrentFrame } from 'remotion';

const frame = useCurrentFrame();

// 基础插值
const opacity = interpolate(
  frame,
  [0, 20],        // 输入范围
  [0, 1]          // 输出范围
);

// 带选项的插值
const scale = interpolate(
  frame,
  [0, 30, 60],    // 多个关键帧
  [0, 1.2, 1],    // 对应的输出值
  {
    extrapolateLeft: 'clamp',   // 左侧不超出
    extrapolateRight: 'clamp',  // 右侧不超出
  }
);
```

**extrapolate 选项：**

| 值 | 说明 |
|----|------|
| `'extend'` | 默认，超出范围继续插值 |
| `'clamp'` | 限制在范围内 |
| `'wrap'` | 循环 |
| `'identity'` | 返回原始值 |

**使用示例：淡入淡出**
```tsx
const { durationInFrames } = useVideoConfig();

const opacity = interpolate(
  frame,
  [0, 20, durationInFrames - 20, durationInFrames],
  [0, 1, 1, 0],
  { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
);
```

**使用示例：动画驱动**
```tsx
// 用 spring 驱动 interpolate
const driver = spring({ frame, fps });
const marginLeft = interpolate(driver, [0, 1], [0, 200]);

<div style={{ marginLeft }} />
```

### 3. `Easing` - 缓动函数

```tsx
import { interpolate, Easing } from 'remotion';

// 贝塞尔曲线缓动
interpolate(frame, [0, 100], [0, 1], {
  easing: Easing.bezier(0.8, 0.22, 0.96, 0.65),
});

// 预设缓动
Easing.linear        // 线性
Easing.ease          // 默认缓动
Easing.in(Easing.cubic)    // 缓入
Easing.out(Easing.cubic)   // 缓出
Easing.inOut(Easing.cubic) // 缓入缓出
```

### 4. `interpolateColors()` - 颜色插值

```tsx
import { interpolateColors } from 'remotion';

const color = interpolateColors(
  frame,
  [0, 60],
  ['#000000', '#ffffff']  // 从黑色到白色
);
```

---

## 时间控制

### `useCurrentFrame()` - 获取当前帧

```tsx
const frame = useCurrentFrame(); // 返回 0 到 durationInFrames 之间的值
```

### `useVideoConfig()` - 获取视频配置

```tsx
const { fps, durationInFrames, width, height } = useVideoConfig();
```

**返回值：**

| 属性 | 说明 |
|------|------|
| `fps` | 帧率（如 30） |
| `durationInFrames` | 总帧数 |
| `width` | 宽度 |
| `height` | 高度 |

### 时间计算示例

```tsx
const { fps, durationInFrames } = useVideoConfig();

// 秒转帧
const secondsToFrames = (seconds: number) => Math.round(seconds * fps);

// 帧转秒
const framesToSeconds = (frames: number) => frames / fps;

// 当前时间（秒）
const currentTime = frame / fps;

// 剩余时间（秒）
const remainingTime = (durationInFrames - frame) / fps;
```

---

## 音频集成

### `<Audio>` - 音频组件

```tsx
import { Audio, staticFile } from 'remotion';

// 播放本地音频
<Audio src={staticFile("audio/voiceover.mp3")} />

// 播放外部音频
<Audio src="https://example.com/sound.mp3" />

// 带音量控制
<Audio src={staticFile("audio.mp3")} volume={0.5} />
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `src` | string | 音频文件路径 |
| `volume` | number \| (f) => number | 音量（0-1） |
| `startFrom` | number | 从第几帧开始 |
| `endAt` | number | 到第几帧结束 |
| `loop` | boolean | 是否循环 |

**使用示例：带淡入淡出的音频**
```tsx
<Audio
  src={staticFile("audio.mp3")}
  volume={(f) => interpolate(
    f,
    [0, 30, durationInFrames - 30, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  )}
/>
```

### `staticFile()` - 静态文件

```tsx
import { staticFile } from 'remotion';

// 引用 public/ 目录下的文件
<Audio src={staticFile("audio/voiceover.mp3")} />
<Img src={staticFile("images/logo.png")} />
<Video src={staticFile("videos/background.mp4")} />
```

---

## 渲染配置

### CLI 渲染命令

```bash
# 基础渲染
npx remotion render src/index.ts MyVideo output.mp4

# 指定编码器
npx remotion render src/index.ts MyVideo output.mp4 --codec h264
npx remotion render src/index.ts MyVideo output.mp4 --codec h265
npx remotion render src/index.ts MyVideo output.mp4 --codec vp8
npx remotion render src/index.ts MyVideo output.mp4 --codec gif

# 指定分辨率
npx remotion render src/index.ts MyVideo output.mp4 --width 1080 --height 1920

# 指定帧范围
npx remotion render src/index.ts MyVideo output.mp4 --frames 0-100

# 调整质量（CRF，越小质量越高，默认18）
npx remotion render src/index.ts MyVideo output.mp4 --crf 15

# 并发渲染（加快速度）
npx remotion render src/index.ts MyVideo output.mp4 --concurrency 4

# 传入 props
npx remotion render src/index.ts MyVideo output.mp4 --props '{"title": "Hello"}'
```

### 编码器对比

| 编码器 | 用途 | 文件大小 | 质量 |
|--------|------|----------|------|
| `h264` | 通用，兼容性最好 | 中等 | 高 |
| `h265` | 更高压缩率 | 更小 | 高 |
| `vp8` | WebM 格式 | 中等 | 中等 |
| `gif` | 动图 | 较大 | 低 |

### 编程式渲染

```tsx
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';

// 打包
const bundleLocation = await bundle({
  entryPoint: './src/index.ts',
});

// 选择组合
const composition = await selectComposition({
  serveUrl: bundleLocation,
  id: 'MyVideo',
});

// 渲染
await renderMedia({
  composition,
  serveUrl: bundleLocation,
  codec: 'h264',
  outputLocation: './output/video.mp4',
});
```

---

## ElevenLabs 集成

### elevenlabs-remotion skill

这是一个专门用于生成视频配音的 skill。

### 场景脚本格式 (scenes.json)

```json
{
  "name": "product-demo",
  "voice": "George",
  "character": "narrator",
  "model": "eleven_multilingual_v2",
  "scenes": [
    {
      "id": "scene1",
      "text": "Welcome to our product demo.",
      "duration": 4.5,
      "character": "dramatic"
    },
    {
      "id": "scene2",
      "text": "Simple setup. Powerful features.",
      "duration": 5.5,
      "delay": 0.3
    },
    {
      "id": "scene3",
      "text": "Get started today.",
      "duration": 8
    }
  ]
}
```

### Character Presets（角色预设）

| 预设 | 描述 | 适用场景 |
|------|------|----------|
| `literal` | 逐字朗读 | 屏幕文字、引用 |
| `narrator` | 专业叙述者 | 解释视频、纪录片 |
| `salesperson` | 热情有说服力 | 营销、广告 |
| `expert` | 权威自信 | 教程、法律内容 |
| `conversational` | 休闲友好 | 社交媒体 |
| `dramatic` | 强烈情感 | 开场、问题陈述 |
| `calm` | 舒缓柔和 | 信任建立、结尾 |

### 生成命令

```bash
# 生成单个语音
node .claude/skills/elevenlabs/generate.js \
  --text "Your text here" \
  --character narrator \
  --output public/audio/voiceover.mp3

# 批量生成场景
node .claude/skills/elevenlabs/generate.js \
  --scenes remotion/scenes.json \
  --output-dir public/audio/project/

# 重新生成单个场景
node .claude/skills/elevenlabs/generate.js \
  --scenes scenes.json \
  --scene scene2 \
  --new-text "Updated text" \
  --output-dir public/audio/project/

# 验证音频
node .claude/skills/elevenlabs/generate.js \
  --validate public/audio/project/
```

### 音频验证结果

```
🔍 Validating product-demo (3 scenes)

❌ scene1: 3.00s (expected: 4.5s)
   ❌ Audio 1.50s shorter than expected
   👍 8 words @ 3.1 words/sec

⚠️ scene2: 6.35s (expected: 5.5s)
   ⚠️ Leading silence: 235ms
   🐢 10 words @ 1.8 words/sec

✅ scene3: 4.36s (expected: 4s)
   👍 9 words @ 2.3 words/sec
```

### info.json 输出格式

```json
{
  "scenes": [
    {
      "id": "scene1",
      "duration": 4.5,
      "actualDuration": 3.0,
      "leadingSilence": 0.05,
      "wordsPerSecond": 3.1
    }
  ]
}
```

---

## 设计系统

### 颜色定义

```tsx
const COLORS = {
  // 主色
  primary: '#2C5282',
  secondary: '#1E3A5F',
  
  // 强调色
  accent: '#F43F5E',
  highlight: '#D4A574',
  
  // 中性色
  background: '#f5f5f0',
  surface: '#FFFFFF',
  text: '#1A202C',
  textMuted: '#6B7280',
  
  // 边框
  borderBlue: '#3182CE',
  borderPink: '#ED64A6',
};
```

### 字体设置

```tsx
const FONTS = {
  // 标题字体（手写风格）
  heading: 'Caveat, cursive',
  
  // 正文字体
  body: 'Inter, sans-serif',
  
  // 代码字体
  mono: 'Fira Code, monospace',
};
```

### 动画常量

```tsx
const ANIMATION = {
  // 过渡帧数
  TRANSITION_FRAMES: 18,
  
  // 弹簧配置
  SPRING_CONFIG: {
    damping: 15,
    stiffness: 200,
  },
  
  // 时序
  TIMING: {
    FAST: 0.2,
    NORMAL: 0.3,
    SLOW: 0.5,
  },
};
```

---

## 最佳实践

### 1. 场景设计

```tsx
// ✅ 好的实践：每个场景独立
<Sequence from={0} durationInFrames={scene1Frames}>
  <Audio src={staticFile("audio/scene1.mp3")} />
  <Scene1 />
</Sequence>

// ❌ 避免：音频放在 TransitionSeries 内部
```

### 2. 动画延迟

```tsx
// ✅ 好的实践：场景 2+ 的动画需要延迟
const TRANSITION_FRAMES = 18;

const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // 延迟到过渡完成后
  const animFrame = Math.max(0, frame - TRANSITION_FRAMES);
  
  const opacity = spring({ frame: animFrame, fps });
  
  return (
    <AbsoluteFill style={{ opacity }}>
      内容
    </AbsoluteFill>
  );
};
```

### 3. 音频放置

```tsx
// ✅ 好的实践：音频放在 TransitionSeries 外部
export const MyVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* 音频序列在 TransitionSeries 外部 */}
      <Sequence from={0} durationInFrames={scene1Frames}>
        <Audio src={staticFile("audio/scene1.mp3")} />
      </Sequence>
      
      <Sequence from={scene2Start} durationInFrames={scene2Frames}>
        <Audio src={staticFile("audio/scene2.mp3")} />
      </Sequence>
      
      {/* 视觉 TransitionSeries */}
      <TransitionSeries>
        <TransitionSeries.Transition />
        {/* 场景组件（无音频） */}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
```

### 4. 文本处理

```tsx
// ✅ 好的实践：数字写成文字
// "500" → "five hundred"
// "24h" → "twenty-four hours"

// ✅ 好的实践：使用标点控制节奏
// "Simple. Powerful. Instant."（句号停顿）
// "Fast, reliable, secure"（逗号短停）
```

---

## 完整工作流

### 步骤 1：设计系统准备

```bash
# 检查设计文件
ls design.md design-system.md 2>/dev/null || echo "No design file"

# 从项目提取设计
cat app/globals.css  # CSS 变量
cat tailwind.config.js  # 主题颜色
ls remotion/  # 现有组件
```

### 步骤 2：创建场景脚本

```json
// scenes.json
{
  "name": "lifi-intents-explainer",
  "voice": "George",
  "character": "narrator",
  "scenes": [
    {
      "id": "scene1",
      "text": "Wait, compare, sign, execute. That's the old way.",
      "duration": 4.5,
      "character": "dramatic"
    },
    {
      "id": "scene2",
      "text": "Alice has USDC on Base. She wants USDC on Arbitrum.",
      "duration": 5.5,
      "character": "narrator"
    }
  ]
}
```

### 步骤 3：生成配音

```bash
# 生成所有场景
node .claude/skills/elevenlabs/generate.js \
  --scenes scenes.json \
  --output-dir public/audio/explainer/

# 验证音频
node .claude/skills/elevenlabs/generate.js \
  --validate public/audio/explainer/
```

### 步骤 4：创建 Remotion 组件

```tsx
// src/Explainer.tsx
import { AbsoluteFill, Sequence, Audio, staticFile, useCurrentFrame, useVideoConfig, spring } from 'remotion';

const COLORS = {
  background: '#f5f5f0',
  text: '#1A202C',
  accent: '#3182CE',
};

const SCENE_DURATIONS = {
  scene1: 4.5,
  scene2: 5.5,
};

export const Explainer: React.FC = () => {
  const { fps } = useVideoConfig();
  
  const scene1Frames = Math.round(SCENE_DURATIONS.scene1 * fps);
  const scene2Frames = Math.round(SCENE_DURATIONS.scene2 * fps);
  
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.background }}>
      {/* 场景 1 */}
      <Sequence from={0} durationInFrames={scene1Frames}>
        <Audio src={staticFile("audio/explainer/scene1.mp3")} />
        <Scene1 />
      </Sequence>
      
      {/* 场景 2 */}
      <Sequence from={scene1Frames} durationInFrames={scene2Frames}>
        <Audio src={staticFile("audio/explainer/scene2.mp3")} />
        <Scene2 />
      </Sequence>
    </AbsoluteFill>
  );
};

const Scene1: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const opacity = spring({ frame, fps, config: { damping: 15 } });
  
  return (
    <AbsoluteFill style={{ opacity }}>
      <h1 style={{ color: COLORS.text }}>THE FLIP</h1>
      <p>Wait, compare, sign, execute.</p>
    </AbsoluteFill>
  );
};

const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const scale = spring({ frame, fps, config: { damping: 15 } });
  
  return (
    <AbsoluteFill style={{ transform: `scale(${scale})` }}>
      <h1 style={{ color: COLORS.text }}>THE INTENT</h1>
      <p>Alice has USDC on Base.</p>
    </AbsoluteFill>
  );
};
```

### 步骤 5：注册组合

```tsx
// src/Root.tsx
import { Composition } from 'remotion';
import { Explainer } from './Explainer';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="LifiIntentsExplainer"
      component={Explainer}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
```

### 步骤 6：渲染视频

```bash
# 渲染最终视频
npx remotion render src/index.ts LifiIntentsExplainer output.mp4 --codec h264

# 嵌入缩略图
node .claude/skills/elevenlabs/generate.js \
  --embed-thumbnail output.mp4 \
  --thumbnail thumbnail.png \
  --output final.mp4
```

---

## 常见动画模式

### 1. 淡入效果

```tsx
const opacity = interpolate(frame, [0, 20], [0, 1], {
  extrapolateRight: 'clamp',
});

<div style={{ opacity }}>内容</div>
```

### 2. 弹性缩放

```tsx
const scale = spring({
  frame,
  fps,
  config: { damping: 12, stiffness: 200 },
});

<div style={{ transform: `scale(${scale})` }}>内容</div>
```

### 3. 滑动入场

```tsx
const translateX = interpolate(
  spring({ frame, fps }),
  [0, 1],
  [-100, 0]
);

<div style={{ transform: `translateX(${translateX}px)` }}>内容</div>
```

### 4. 打字机效果

```tsx
const text = "Hello World";
const charsToShow = Math.floor(
  interpolate(frame, [0, 60], [0, text.length], {
    extrapolateRight: 'clamp',
  })
);

<div>{text.slice(0, charsToShow)}</div>
```

### 5. 路径动画

```tsx
import { interpolatePath, Easing } from 'remotion';

const path = "M 0 0 Q 100 100 200 0";
const progress = interpolate(frame, [0, 60], [0, 1]);

<svg>
  <path
    d={path}
    stroke="blue"
    fill="none"
    strokeDasharray={1000}
    strokeDashoffset={interpolate(progress, [0, 1], [1000, 0])}
  />
</svg>
```

---

## 调试技巧

### 1. 预览视频

```bash
# 启动 Remotion Studio
npx remotion studio
```

### 2. 检查帧信息

```tsx
console.log(`Current frame: ${frame}`);
console.log(`Total frames: ${durationInFrames}`);
console.log(`Current time: ${frame / fps}s`);
```

### 3. 音频验证

```bash
# 使用 ffprobe 检查音频
ffprobe -v quiet -show_format audio.mp3
ffprobe -v quiet -show_streams audio.mp3
```

---

## 参考资源

- [Remotion 官方文档](https://www.remotion.dev/docs)
- [Spring 动画文档](https://www.remotion.dev/docs/spring)
- [Interpolate 文档](https://www.remotion.dev/docs/interpolate)
- [elevenlabs-remotion skill](https://github.com/Maartenlouis/elevenlabs-remotion-skill)
- [ElevenLabs MCP](https://github.com/elevenlabs/elevenlabs-mcp)

---

*最后更新：2026-06-06*
