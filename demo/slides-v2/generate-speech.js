const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle, PageBreak, LevelFormat } = require('docx');
const fs = require('fs');

const FONT = "Microsoft YaHei";
const FONT_EN = "Arial";

// Helper: normal paragraph
function p(text, opts = {}) {
  const runs = parseRuns(text, opts.fontSize || 24, opts.bold);
  return new Paragraph({
    spacing: { after: opts.after !== undefined ? opts.after : 160, line: opts.line || 340 },
    children: runs,
    ...(opts.pageBreakBefore ? { pageBreakBefore: true } : {}),
    ...(opts.numbering ? { numbering: opts.numbering } : {}),
    ...(opts.indent ? { indent: opts.indent } : {}),
  });
}

// Helper: parse **bold** markers in text
function parseRuns(text, fontSize, allBold) {
  const runs = [];
  const parts = text.split(/(\*\*.*?\*\*)/g);
  for (const part of parts) {
    if (part.startsWith('**') && part.endsWith('**')) {
      runs.push(new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, size: fontSize }));
    } else if (part) {
      runs.push(new TextRun({ text: part, bold: allBold || false, font: FONT, size: fontSize }));
    }
  }
  return runs;
}

// Helper: section heading (page title)
function slideHeading(slideNum, title, time) {
  return new Paragraph({
    spacing: { before: 360, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "0052D9", space: 8 } },
    children: [
      new TextRun({ text: `P${slideNum}: ${title}`, font: FONT, size: 28, bold: true, color: "0052D9" }),
      new TextRun({ text: `  ${time}`, font: FONT_EN, size: 20, color: "999999" }),
    ],
  });
}

// Helper: stage direction (italics)
function stage(text) {
  return new Paragraph({
    spacing: { after: 160, line: 340 },
    children: [new TextRun({ text, font: FONT, size: 22, italics: true, color: "888888" })],
  });
}

// Helper: divider line
function divider() {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: "DDDDDD", space: 4 } },
    children: [new TextRun({ text: " ", font: FONT, size: 8 })],
  });
}

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: FONT, size: 24 } },
    },
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 }, // A4
        margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 },
      },
    },
    children: [
      // Title
      new Paragraph({
        spacing: { after: 120 },
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "CodeBuddy 怎么改变我的工作方式", font: FONT, size: 40, bold: true, color: "0052D9" })],
      }),
      new Paragraph({
        spacing: { after: 80 },
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "演讲稿", font: FONT, size: 28, color: "666666" })],
      }),
      new Paragraph({
        spacing: { after: 400 },
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "预估时长：20–25 分钟（含两个现场 Demo 各 3 分钟）", font: FONT, size: 22, color: "999999" })],
      }),
      divider(),

      // P1
      slideHeading(1, "封面", "[~30秒]"),
      p("大家好，今天跟大家聊一个话题：CodeBuddy 怎么改变我的工作方式。"),
      p("我在外汇交易台，不是做技术的，就是个外汇民工。过去一年用 CodeBuddy 折腾了不少东西，今天把真实经验跟大家分享一下。"),
      divider(),

      // P2
      slideHeading(2, "先说说我的工作", "[~1分钟]"),
      p("先简单说下我的日常。报表、定价、策略、市场情报，还要跟产研同学提需求、推功能上线。"),
      p("今天分三个部分来聊："),
      p("第一块，**分析与交易** —— 数据分析、策略回测、定价模拟这些。"),
      p("第二块，**文字与表达** —— 提需求、写报告、做演示、跟人沟通。"),
      p("第三块，**知识沉淀** —— 搭 Agent、建知识体系。"),
      p('为什么会有\u201C文字与表达\u201D这块呢？因为我们除了跟数字打交道，还有大量需要跟产研沟通、给管理层汇报、给客户写东西的场景。这部分以前其实挺痛苦的。'),
      divider(),

      // P3
      slideHeading(3, "Section — 分析与交易", "[翻页即过]"),
      p("好，先来第一部分，分析与交易。"),
      divider(),

      // P4
      slideHeading(4, "核心变化：做工具的成本崩塌了", "[~2分钟]"),
      p("这页讲的是我觉得最核心的一个变化。"),
      p("以前想做个 desk tool，两条路。"),
      p("第一条，找人做。提需求、找产品、找研发、排期。但交易台的需求太小众、不通用，经常被砍。在座的可能也有类似经历。"),
      p("第二条，自己做。我自己是会写代码的，之前在 WeData 上手搓了一些。能跑，但很糙。想升级成像样的工具吧，精力不够，重构成本太高。左边这个截图就是当时手搓的代码。"),
      p("现在呢？右边这个 —— 同样一个回测工具，在 CodeBuddy 里几句话描述就出来了。迭代几轮直接用，几十分钟到几小时搞定。"),
      p('底下这句话我觉得是关键：以前会纠结\u201C这个需求值不值得提\u201D，现在试一下的成本几乎为零。'),
      divider(),

      // P5
      slideHeading(5, "例子：周末预锁价策略", "[~1.5分钟]"),
      p("说个具体的例子。"),
      p("周末预锁价策略 —— 周五晚间客户锁汇需求集中，市场流动性差、点差会拉大。那能不能提前锁定价格赚这个价差？"),
      p("我没有一上来就想做什么回测平台，先拿这一个策略跑个回测，跑通了再说。屏幕上这个就是当时做出来的回测结果。"),
      p("策略跑通了，接下来的问题是：参数怎么选最优？"),
      divider(),

      // P6
      slideHeading(6, "参数扫描找最优", "[~1.5分钟]"),
      p("还是这个策略。这里我把两个核心参数全量扫了一遍：一个是信号强弱，就是置信度；一个是二次确认，就是灵敏度。"),
      p("大家看这个热力图，颜色越深代表这组参数收益越好。那个星号就是最优参数组合。"),
      p("关键在于：一个策略跑通了、参数调好了，就可以把它抽象成通用引擎。换个策略、换组参数就能跑。这个思路后面一直在用。"),
      divider(),

      // P7
      slideHeading(7, "LIVE — 周末预锁价回测系统", "[~3分钟]"),
      p("好，说了这么多不如直接看。"),
      stage("（点击进入 Portal，现场演示：选策略、配参数、跑回测、看结果。自然讲解即可。）"),
      divider(),

      // P8
      slideHeading(8, "同一个思路，一年做了这些", "[~1.5分钟]"),
      p("演示完回来看这页。"),
      p("同一个思路 —— 先做一个、跑通、再扩展 —— 一年下来做了这些东西。"),
      p("左边两大类。分析可视化这边有损益分析、反推定价参数、持仓敞口监控这些。策略定价这边有 Strategy Lab、加点定价引擎、FIXING 价差回测、港币套利。"),
      p("右边是真实的 Portal 截图，每个工具一张卡片，能看状态、一键启动。"),
      p("底下这句话：大脑，也就是 Token，公司已经给了。真正的难点是数据。数据清理好了，工具才跑得起来。"),
      divider(),

      // P9
      slideHeading(9, "Section — 文字与表达", "[翻页即过]"),
      p("好，第二部分，文字与表达。"),
      divider(),

      // P10
      slideHeading(10, "方法论：先让想法看得见", "[~1.5分钟]"),
      p("先说个痛点。"),
      p("跟产品研发沟通需求的时候，你心里想的东西，写成文档或者口头一说，到对方那里总有偏差。来回对齐好几轮，做出来可能还不是你要的。"),
      p("后来我发现一件事：脑子里有个模糊的想法，可以先跟 CodeBuddy 聊，让它帮你捋清楚。不用一开始就想得多完整。"),
      p("三步：说出想法，从小到大跑通，变成能演示的原型。"),
      p("多一个沟通方式，少一点来回对齐。"),
      divider(),

      // P11
      slideHeading(11, "例子：金融日历", "[~2分钟]"),
      p("举个具体例子。"),
      p("金融日历 —— 就是接入 Bloomberg 经济日历，根据事件的重要性，比如非农、FOMC、CPI 这些，自动控制定价系统拉宽点差、风控系统减仓对冲。以前这些全靠手动，忙的时候容易漏。"),
      p("我跟 CodeBuddy 是怎么聊的呢？"),
      p("首先，用 iWiki MCP 让它读我们的内部文档，搞懂定价管线和对冲逻辑。然后花了很多时间聊业务细节：哪些事件要覆盖、响应参数怎么定、五个阶段怎么走。最后我说，我想要一个交互式的场景走查，能直接拿去给产品研发看。"),
      p("最后出了两个东西：一份设计文档，架构、数据表、接口都有；还有一个可交互的 Demo 界面。拿着这两样东西去讨论，效率完全不一样。"),
      p("下一页给大家看看这个界面长什么样。"),
      divider(),

      // P12
      slideHeading(12, "DEMO — 金融日历", "[~3分钟]"),
      p("这就是那个 Demo。你可以选一个事件，比如非农，然后看它五个阶段的响应。左边是定价侧，右边是风控侧。"),
      p("拿给产品研发看，他们一下子就明白你想做什么了。"),
      stage("（现场演示 Financial Calendar Demo。自然讲解即可。）"),
      divider(),

      // P13
      slideHeading(13, "还有哪些文字类工作？", "[~1分钟]"),
      p('除了金融日历这种\u201C做个工具来表达\u201D，还有一些更日常的。'),
      p("报告方面：FX 研报可以一键生成多语言版本；你们现在看的这个 PPT，也是 CodeBuddy 做的；还有架构图，描述一下需求就能出。"),
      p("日常沟通方面：有个语言美化器 —— 我说话比较直，大家可能有体会。CodeBuddy 帮我说得委婉一点。还有邮件润色、会议纪要这些。"),
      p("一句话：不是替你说，是帮你把想说的话说得更好。"),
      divider(),

      // P14
      slideHeading(14, "Section — 知识沉淀", "[~15秒]"),
      p("好，第三部分，知识沉淀。"),
      p("这部分跟前面不太一样。前面讲的都是顺利的，这部分要讲一个不那么顺利的故事。"),
      divider(),

      // P15
      slideHeading(15, "用 CodeBuddy 搭了两个 Agent", "[~1.5分钟]"),
      p("前面做工具、做 Demo 都很顺，慢慢就觉得 CodeBuddy 什么都能做。于是我搭了两个 Agent。"),
      p("左边这个，Soros Agent，外汇交易助理。每天市场信息太多了，想有个帮我过滤噪音、给点判断的。"),
      p("右边这个，林徽因 Agent。纯粹是工作之外想拓展一下认知边界，聊聊建筑、美学这些。"),
      p("我当时的计划是：把所有交易经验都喂给它，让它变成一个越用越懂我的交易大脑。"),
      divider(),

      // P16
      slideHeading(16, "然后就翻车了", "[~2分钟]"),
      p("然后就翻车了。"),
      p("前面太顺了嘛，觉得 CodeBuddy 无所不能，那就搞个大的 —— 手搓一整套知识库系统。5 本外汇经典、央行政策、危机案例，全喂进去。"),
      p("确实做了不少。8 个 Skill 加起来 25KB，5 层记忆系统，19 个工具，全量注入 System Prompt。"),
      p("结果呢？光 System Prompt 就 40 多 KB，还没开始分析，上下文就满了。越喂越笨 —— 知识越多，能思考的空间越小。"),
      p("更要命的是 —— 大家看这张图 —— 公司给的额度 10 万，我用了 10 万 8 千，直接超了。"),
      p("根因就一句话：我把「造工具」和「当工具」搞混了。CodeBuddy 帮你写代码一流，但让它长期驻留、管理记忆、调度工具 —— 那不是它干的活。"),
      divider(),

      // P17
      slideHeading(17, "吃一堑长一智", "[~1.5分钟]"),
      p("吃了瘪之后，我想了两件事。"),
      p("第一，要找到对的组合。不是什么都自己从零硬搓。CodeBuddy 加上 MCP、加上 Skill，其实就已经很强了 —— 让它做擅长的事就好。至于知识管理和长期运行 Agent 这种活，交给专门做这个的平台。后来 OpenClaw 出来了，可能是一个方向，但我还在探索，没有下结论。不过正因为之前从零搭了一遍，我对 Agent 架构才有了真实的理解，所以也不算白折腾。"),
      p("第二，对技术要保持好奇心，也要保持敬畏心。前面越顺，越容易忘了这件事。额度用爆，就是最好的提醒。"),
      divider(),

      // P18
      slideHeading(18, "总结", "[~1分钟]"),
      p("最后总结一下。三个方向，各一句话。"),
      p("**分析与交易** —— 一个痛点一个工具，先跑通一个再扩展。"),
      p("**文字与表达** —— 先做 Demo 再沟通，做的过程就是在沟通。"),
      p("**知识沉淀** —— 找到对的组合，知道边界在哪。"),
      divider(),

      // P19
      slideHeading(19, "Ending", "[~30秒]"),
      p("最后送大家一句话。"),
      p("**The Limit is Sky.**", { fontSize: 32 }),
      stage("（停顿两秒）"),
      p("…… and token."),
      p(""),
      p("谢谢大家！", { fontSize: 28, bold: true }),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  const outPath = "c:/Users/tencentren/CodeBuddy/FX_SYSTEM_DEMO/demo/slides-v2/演讲稿-CodeBuddy怎么改变我的工作方式.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("Done: " + outPath);
});
