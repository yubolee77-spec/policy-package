// ============================================================
// Policy Intelligence Workbench - Interactive Logic
// ============================================================

// --- Clock ---
function updateClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  document.getElementById('clockDisplay').textContent =
    `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}
setInterval(updateClock, 1000);
updateClock();

// --- Tab Navigation ---
const tabBtns = document.querySelectorAll('.tab-btn');
const panels = document.querySelectorAll('.panel');
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.p;
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    panels.forEach(p => p.classList.remove('active'));
    document.getElementById('p-' + target).classList.add('active');
    // Re-render charts in the visible panel
    setTimeout(() => renderChartsForPanel(target), 50);
  });
});

// ============================================================
// LAYER 0: Macro Data
// ============================================================
const macroData = {
  // 年度数据：2026年上半年（国家统计局2026年7月15日发布）
  year: [
    { name: 'GDP', val: '4.7', unit: '%', chg: '上半年同比', dir: 'pos', sub: '2026年上半年·GDP 695704亿元', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260715_1964121.html' },
    { name: 'M1货币', val: '4.0', unit: '%', chg: '7月末同比', dir: 'flat', sub: '2026年7月末·M1余额115.46万亿元', url: 'https://m.thepaper.cn/newsDetail_forward_33784453' },
    { name: 'M2-M1剪刀差', val: '3.7', unit: 'pct', chg: '7月末', dir: 'neg', sub: 'M2 7.7% - M1 4.0% = 3.7pct', url: 'https://m.thepaper.cn/newsDetail_forward_33784453' },
    { name: '社会融资规模', val: '7.4', unit: '%', chg: '7月末存量同比', dir: 'flat', sub: '2026年7月末·存量463.27万亿元', url: 'https://m.thepaper.cn/newsDetail_forward_33784453' },
    { name: '城镇调查失业率', val: '5.2', unit: '%', chg: '上半年均值', dir: 'flat', sub: '2026年上半年·与上年同期持平', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260715_1964121.html' },
    { name: 'CPI同比', val: '1.0', unit: '%', chg: '上半年同比', dir: 'pos', sub: '2026年上半年·温和上涨', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260715_1964121.html' },
    { name: 'PPI同比', val: '1.5', unit: '%', chg: '上半年同比', dir: 'pos', sub: '2026年上半年·由负转正', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260715_1964121.html' },
    { name: 'PMI', val: '49.2', unit: '%', chg: '7月', dir: 'neg', sub: '2026年7月·制造业PMI·荣枯线下', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260731_1964253.html' },
    { name: '工业企业利润', val: '18.7', unit: '%', chg: '1-6月同比', dir: 'pos', sub: '2026年1-6月·规上工业39480亿元', url: 'https://www.stats.gov.cn/sj/zxfb/202608/t20260817_1965056.html' },
    { name: '社会消费品零售总额', val: '1.3', unit: '%', chg: '上半年同比', dir: 'pos', sub: '2026年上半年·248722亿元', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260715_1964121.html' }
  ],
  // 月度数据：2026年7月最新数据（国家统计局2026年8月9日发布）
  month: [
    { name: 'GDP', val: '4.3', unit: '%', chg: 'Q2同比', dir: 'neg', sub: '2026年二季度·GDP 361511亿元', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260715_1964121.html' },
    { name: 'M1货币', val: '4.0', unit: '%', chg: '7月末同比', dir: 'flat', sub: '2026年7月末·增速与上月持平', url: 'https://m.thepaper.cn/newsDetail_forward_33784453' },
    { name: 'M2-M1剪刀差', val: '3.7', unit: 'pct', chg: '7月末', dir: 'neg', sub: 'M2 7.7% - M1 4.0% = 3.7pct·收窄', url: 'https://m.thepaper.cn/newsDetail_forward_33784453' },
    { name: '社会融资规模', val: '22.25', unit: '万亿', chg: '1-7月增量', dir: 'neg', sub: '2026年前7月·同比少1.74万亿', url: 'https://m.thepaper.cn/newsDetail_forward_33784453' },
    { name: '城镇调查失业率', val: '5.2', unit: '%', chg: '7月', dir: 'flat', sub: '2026年7月·与上年同期持平', url: 'https://www.stats.gov.cn/sj/zxfb/202608/t20260817_1965056.html' },
    { name: 'CPI同比', val: '0.5', unit: '%', chg: '7月', dir: 'neg', sub: '2026年7月·1-7月平均0.9%', url: 'https://www.stats.gov.cn/sj/zxfb/202608/t20260809_1965008.html' },
    { name: 'PPI同比', val: '3.5', unit: '%', chg: '7月', dir: 'neg', sub: '2026年7月·涨幅比上月回落0.6pct', url: 'https://www.stats.gov.cn/sj/zxfb/202608/t20260809_1965007.html' },
    { name: 'PMI', val: '49.2', unit: '%', chg: '7月', dir: 'neg', sub: '2026年7月·荣枯线下·比上月-1.1pct', url: 'https://www.stats.gov.cn/sj/zxfb/202607/t20260731_1964253.html' },
    { name: '工业增加值', val: '4.5', unit: '%', chg: '7月同比', dir: 'pos', sub: '2026年7月·规上工业增加值', url: 'https://www.stats.gov.cn/sj/zxfb/202608/t20260817_1965055.html' },
    { name: '社会消费品零售总额', val: '1.2', unit: '%', chg: '1-7月同比', dir: 'pos', sub: '2026年1-7月·社会消费品零售总额', url: 'https://www.stats.gov.cn/sj/zxfb/202608/t20260817_1965052.html' }
  ]
};

// L0 宏观数据：macroAuto 来自 data/macro.json（每日自动抓取，东方财富数据中心），
// 抓不到的指标（社融/失业率等）回退到内置 macroData 兜底卡。
var macroAuto = null;
var currentMacroPeriod = 'year';

function getMacroCards(period) {
  var auto = macroAuto && macroAuto.cards ? macroAuto.cards : [];
  var names = {};
  auto.forEach(function(c) { names[c.name] = true; });
  var fallback = macroData[period]
    .filter(function(c) { return !names[c.name]; })
    .map(function(c) {
      var copy = {};
      for (var k in c) copy[k] = c[k];
      copy.fallback = true;
      copy.sub = c.sub + '（自动数据源暂缺·手工值）';
      return copy;
    });
  return auto.concat(fallback);
}

function renderMacroCards(period) {
  currentMacroPeriod = period;
  const grid = document.getElementById('macroGrid');
  grid.innerHTML = '';
  getMacroCards(period).forEach(item => {
    const card = document.createElement('a');
    card.href = item.url;
    card.target = '_blank';
    card.className = 'data-card' + (item.fallback ? ' card-fallback' : '');
    const arrow = item.dir === 'pos' ? '▲' : (item.dir === 'neg' ? '▼' : '→');
    card.innerHTML = `
      <div class="card-hd">
        <div>
          <div class="card-title">${item.name}${item.fallback ? ' <span class="fb-tag">兜底</span>' : ''}</div>
          <div class="card-sub">${item.sub}</div>
        </div>
        <a href="${item.url}" target="_blank" class="card-src">数据源 ↗</a>
      </div>
      <div class="val-row">
        <div class="val ${item.dir}">${item.val}</div>
        <div class="unit">${item.unit}</div>
      </div>
      <span class="chg ${item.dir}">${arrow} ${item.chg}</span>
      <div class="card-meta">${item.sub}</div>
    `;
    grid.appendChild(card);
  });
}

// Macro chart
let macroChart = null;
function renderMacroChart() {
  if (!macroChart) macroChart = echarts.init(document.getElementById('macroChart'));
  // 优先用 data/macro.json 的自动序列（近13个月）；无则回退内置 2026年1-7月数据
  let monthLabels, cpiData, ppiData, pmiData;
  if (macroAuto && macroAuto.series && macroAuto.series.dates && macroAuto.series.dates.length) {
    const s = macroAuto.series;
    monthLabels = s.dates;
    cpiData = s.cpi.slice();
    ppiData = s.ppi.slice();
    pmiData = s.pmi.slice();
  } else {
    monthLabels = ['2026-01','2026-02','2026-03','2026-04','2026-05','2026-06','2026-07'];
    cpiData = [null, 1.3, 1.0, 1.2, 1.2, 1.0, 0.5];
    ppiData = [null, null, null, null, null, 4.1, 3.5];
    pmiData = [49.3, 49.0, 50.4, 50.3, 50.0, 50.3, 49.2];
  }
  const chartTitle = '核心宏观指标趋势（' + monthLabels[0] + ' 至 ' + monthLabels[monthLabels.length - 1] + '）';
  const softAmber = '#c9a86a';
  const softRed  = '#c97878';
  const softGreen = '#7ab88c';
  const softSand = '#d4b07a';
  const option = {
    backgroundColor: 'transparent',
    title: {
      text: chartTitle,
      subtext: macroAuto ? '数据来源：国家统计局 · 每日自动更新（' + (macroAuto.lastUpdated || '') + ' 抓取）' : '数据来源：国家统计局 · CPI/PPI 同比(%)、PMI',
      left: 'center',
      textStyle: { color: '#d0d0d0', fontSize: 13, fontWeight: 500 },
      subtextStyle: { color: '#9e9e9e', fontSize: 10 }
    },
    tooltip: { trigger: 'axis', backgroundColor: '#1e1e1e', borderColor: '#3a3a3a', textStyle: { color: '#e2e8f0' } },
    legend: { data: ['CPI同比(%)', 'PPI同比(%)', 'PMI(%)'], top: 48, textStyle: { color: '#9e9e9e', fontSize: 11 } },
    grid: { left: '3%', right: '4%', bottom: '3%', top: 90, containLabel: true },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisLine: { lineStyle: { color: '#3a3a3a' } },
      axisLabel: { color: '#808080', fontSize: 10, rotate: 20 }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#3a3a3a' } },
      axisLabel: { color: '#808080', fontSize: 10 },
      splitLine: { lineStyle: { color: '#2a2a2a' } }
    },
    series: [
      {
        name: 'CPI同比(%)', type: 'line', data: cpiData,
        smooth: true, itemStyle: { color: softSand },
        areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(212,176,122,0.22)'},{offset:1,color:'rgba(212,176,122,0)'}])},
        symbol: 'circle', symbolSize: 5,
        connectNulls: true
      },
      {
        name: 'PPI同比(%)', type: 'line', data: ppiData,
        smooth: true, itemStyle: { color: softRed },
        symbol: 'circle', symbolSize: 5,
        connectNulls: true
      },
      {
        name: 'PMI(%)', type: 'line', data: pmiData,
        smooth: true, itemStyle: { color: softGreen },
        symbol: 'circle', symbolSize: 5,
        markLine: {
          data: [{ yAxis: 50, lineStyle: { color: softAmber, type: 'dashed', width: 1 }, label: { formatter: '荣枯线 50%', color: softAmber, fontSize: 10 } }]
        }
      }
    ]
  };
  macroChart.setOption(option);
}

// Macro period switcher
document.querySelectorAll('[data-period]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-period]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderMacroCards(btn.dataset.period);
  });
});

// ============================================================
// LAYER 1: Policy Timeline
// ============================================================
const timelineData = [
  {
    month: '2026年8月',
    items: [
      { title: '金观平：治理账款拖欠重在常态化（经济日报）', desc: '中央政治局会议提出常态化解决企业账款拖欠问题', url: 'http://adimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260821_3159304.shtml' },
      { title: '金观平：深化资本市场投融资综合改革（经济日报）', desc: '中央政治局会议提出深化资本市场投融资综合改革，提升韧性和信心', url: 'http://bgimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260802_3122358.shtml' }
    ]
  },
  {
    month: '2026年5月',
    items: [
      { title: '求是网评论员：如何提升产业链供应链韧性和安全水平', desc: '补链、强链、建链——统筹推进产业链供应链安全', url: 'http://www.qstheory.cn/20260522/13b85573bc924de2946ad7cacc741004/c.html' }
    ]
  },
  {
    month: '2026年3月',
    items: [
      { title: '求是杂志评论员：凝心聚力奋进中国式现代化', desc: '解读全国两会精神，部署"十五五"规划纲要落地落实', url: 'http://www.qstheory.cn/20260314/70a1bcaa409e4cb3bfb7c6f72c73694c/c.html' }
    ]
  },
  {
    month: '2026年2月',
    items: [
      { title: '金观平："投资于人"是破解供强需弱关键（经济日报）', desc: '供给强需求弱是当前最突出矛盾，"投资于人"是关键', url: 'http://www.ce.cn/xwzx/gnsz/gdxw/202602/t20260203_2745939.shtml' }
    ]
  },
  {
    month: '2026年1月',
    items: [
      { title: '钟才平：因地制宜做好经济工作（人民日报头版）', desc: '"钟才平"首次出现在人民日报头版，习近平总书记强调"因地制宜，本质是实事求是"', url: 'http://finance.people.com.cn/n1/2026/0107/c1004-40640698.html' },
      { title: '《中央预算内投资计划管理办法》(发改投资规〔2025〕1728号)', desc: '发改委印发，规范中央预算内投资计划管理，提升投资效益', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260123_1403428.html' },
      { title: '关于推动REITs市场高质量发展有关工作的通知(证监发〔2025〕63号)', desc: '证监会发布，大力支持商业不动产REITs，进一步优化审核流程', url: 'http://www.csrc.gov.cn/csrc/c100028/c7605715/content.shtml' },
      { title: '《政府投资基金投向评价管理办法(试行)》(发改财金规〔2025〕1753号)', desc: '发改委发布，规范政府投资基金投向评价管理', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260112_1403195.html' },
      { title: '金观平：推动物价合理回升（经济日报）', desc: 'CPI连续4个月回升，2025年12月同比上涨0.8%创近34个月新高', url: 'http://views.ce.cn/view/ent/202601/t20260130_2737865.shtml' }
    ]
  },
  {
    month: '2025年12月',
    items: [
      { title: '证监会推出商业不动产投资信托基金试点(证监会公告〔2025〕21号)', desc: '证监会公告，推出商业不动产REITs试点，从试点到全面推广', url: 'http://www.csrc.gov.cn/csrc/c101954/c7605662/content.shtml' },
      { title: '《低空经济及其核心产业统计分类(试行)》(发改低空〔2025〕1676号)', desc: '发改委印发，着力培育低空经济为新兴支柱产业，加速空域改革', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251226_1402669.html' },
      { title: '关于2026年实施大规模设备更新和消费品以旧换新政策的通知(发改环资〔2025〕1745号)', desc: '大力实施"两新"政策，持续扩大覆盖面', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251230_1402851.html' },
      { title: '《再生材料应用推广行动方案》(发改环资〔2025〕1681号)', desc: '发改委发布，推动再生材料应用推广', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251231_1402965.html' },
      { title: '《关于促进电网高质量发展的指导意见》(发改能源〔2025〕1710号)', desc: '发改委发布，促进电网高质量发展', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251231_1402949.html' },
      { title: '《产业技术基础公共服务平台管理办法》(工信部科〔2025〕261号)', desc: '工信部发布，规范产业技术基础公共服务平台管理', url: 'https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/art/2025/art_8d58788c9ccc448fb8428812a1734b86.html' }
    ]
  },
  {
    month: '2025年11月',
    items: [
      { title: '《关于进一步加快制造业中试平台体系化布局和高水平建设的通知》(工信厅科函〔2025〕456号)', desc: '工信部发布，加快制造业中试平台体系化布局和高水平建设', url: 'https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/art/2025/art_69551d935e654671a8816123f1b6ec4f.html' }
    ]
  },
  {
    month: '2025年10月',
    items: [
      { title: '《节能降碳中央预算内投资专项管理办法》(发改环资规〔2025〕1228号)', desc: '发改委发布，着力加强节能降碳中央预算内投资管理', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202510/t20251014_1400943.html' },
      { title: '《深入推动服务型制造创新发展实施方案(2025—2028年)》(工信部联政法〔2025〕202号)', desc: '工信部发布，深入推动服务型制造创新发展', url: 'https://fjca.miit.gov.cn/xwdt/bsyw/art/2025/art_b213568d30e5402685b01eae3f8c1c52.html' }
    ]
  },
  {
    month: '2025年8月',
    items: [
      { title: '《关于优化业务准入促进卫星通信产业发展的指导意见》(工信部信管〔2025〕180号)', desc: '工信部发布，大力推动手机直连卫星应用，进一步扩大向民营企业开放', url: 'https://www.miit.gov.cn/zwgk/zcwj/wjfb/yj/art/2025/art_84617e8497d84a3d8b8b3ef847f648d2.html' },
      { title: '专项债投向结构优化', desc: '新兴产业专项债与交通类占比待核实', url: 'https://yss.mof.gov.cn/zhuantilanmu/dfzgl/sjtj/' }
    ]
  }
];

// ============================================================
// 年度政策节奏时间线：按中国政策传导周期8大节点
// status: hot=进行中/当前月段最新, pass=已过, future=未来
// ============================================================
const annualTimelineNodes = [
  {
    period: '12月',
    slogan: '中央经济工作会议 · 总结今年经济 · 定调明年',
    status: 'future',
    summary: '<strong>中央经济工作会议</strong>（通常 12 月中下旬）是年度最高规格经济会议，总结当年经济运行，定调次年宏观政策基调（财政/货币/产业/防风险四大方向），明确"总盘子"和主要预期目标。同时召开<strong>全国发展和改革工作会</strong>、<strong>全国财政工作会</strong>、<strong>央行工作会</strong>、<strong>证监会系统工作会</strong>，各部委把中央定调拆解为各自次年执行条线。',
    keypoints: [
      { text: '<b>定调次年前瞻性指引：</b>财政政策"积极/加力提效/适度宽松"、货币政策"稳健/灵活适度/适度宽松"、产业政策聚焦当年重点赛道、防风险底线清单。', keywords: [{t:'ding',v:'着力'},{t:'deg',v:'持续'}] },
      { text: '<b>证监会系统工作会：</b>次年监管工作重点（全面注册制常态化、资本市场投融资综合改革、REITs推广、上市公司质量、交易所制度修订、重点行业风险处置）。', keywords: [{t:'ding',v:'大力'}] },
      { text: '<b>央行工作会：</b>次年 M2/M1 增长目标、社会融资规模增量预期、结构性货币政策工具（支农支小、科技创新、设备更新、普惠养老等）安排与节奏。', keywords: [{t:'deg',v:'进一步'}] }
    ],
    docs: [
      { label: '2024年中央经济工作会议通稿（参考模板）', url: 'https://www.gov.cn/yaowen/liebiao/202412/content_6992258.htm' },
      { label: '中国人民银行工作会例行专栏', url: 'http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html' },
      { label: '证监会·要闻·全国证券期货监管工作会', url: 'http://www.csrc.gov.cn/csrc/c100028/common_list.shtml' }
    ]
  },
  {
    period: '11月',
    slogan: '政治局会议 · 总结Q3 · 研究Q4收官',
    status: 'future',
    summary: '<strong>中央政治局会议</strong>（通常 10 月底~11 月初）分析研究前三季度经济形势和四季度经济工作，判断年初设定的 GDP、就业、物价、防风险目标能否完成，必要时对<strong>四季度增量政策工具</strong>作加提效安排（如提前下达下一年专项债额度、政策性开发性金融工具追加、结构性货币政策工具扩容）。',
    keypoints: [
      { text: '<b>三季度经济运行评估：</b>GDP增速、城镇调查失业率、CPI/PPI走势、社零与固定资产投资增速、工业企业利润恢复度、房地产销售与投资是否企稳。', keywords: [{t:'ding',v:'着力'}] },
      { text: '<b>四季度政策加码：</b>是否"加大宏观政策调控力度"、是否新增国债/特别国债、专项债是否提前发行、结构性货币政策工具是否再贷款降息。', keywords: [{t:'ding',v:'大力'},{t:'deg',v:'进一步'}] },
      { text: '<b>防风险部署：</b>地方化债、中小金融机构、房地产、城投、重点行业民营企业债券违约等底线。', keywords: [{t:'deg',v:'持续'}] }
    ],
    docs: [
      { label: '历年政治局会议·新华社通稿专栏', url: 'https://www.news.cn/politics/' },
      { label: '中国政府网·中共中央政治局集体学习/会议', url: 'https://www.gov.cn/yaowen/liebiao/' }
    ]
  },
  {
    period: '9-10月',
    slogan: '中央全会 · 讨论重大改革或五年规划',
    status: 'future',
    summary: '按五年周期惯例，<strong>逢五逢十届三中全会</strong>讨论全面深化改革重大问题（如 2013 十八届三中全会、2018 十九届三中、2023 二十届二中/三中定调机构改革、2028 二十届三中预期），<strong>逢四逢九届四中全会</strong>通常讨论治理现代化或五年规划中期评估。重大改革方向（资本市场改革、要素市场化、土地/户籍/国资国企改革）的<strong>顶层设计文件</strong>通常在全会审议通过。',
    keypoints: [
      { text: '<b>重大改革定调：</b>决议文本中"定调词+动词+程度词"的变化（推动/培育→着力→大力/坚决）是判断改革力度的核心。', keywords: [{t:'ding',v:'坚决'}] },
      { text: '<b>全会《公报》→《决定》：</b>先发布全会公报（定性摘要），几天后发布正式《决定/意见》全文（定量条款+牵头部门分工）。', keywords: [{t:'verb',v:'推动'}] },
      { text: '<b>五年规划中期评估：</b>逢偶数年（如 2026 年为"十五五"开局后第一年评估）会发布规划中期评估报告，可能调整部分指标或重点任务。', keywords: [{t:'deg',v:'进一步'}] }
    ],
    docs: [
      { label: '人民日报·二十届三中全会专题（参考框架）', url: 'https://data.people.com.cn/rmrb/' },
      { label: '求是网·全会精神解读专栏', url: 'http://www.qstheory.cn/' },
      { label: '国家规划纲要数据库', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/' }
    ]
  },
  {
    period: '7月',
    slogan: '政治局会议 · 年中调整',
    status: 'pass',
    summary: '<strong>7月30日中央政治局会议</strong>（2026年）是上半年经济形势复盘+下半年政策转向的核心窗口。定调：<strong>宏观政策发力提效</strong>、<strong>扩大内需</strong>、<strong>产业体系建设</strong>、<strong>市场竞争环境</strong>、<strong>国际经贸</strong>、<strong>民生保障</strong>六大方向。随后 <strong>8月17日金观平解读</strong>：实施好更加积极的财政政策和适度宽松的货币政策，把握力度与节奏。',
    keypoints: [
      { text: '<b>财政：</b>"更加积极"+"适度宽松"货币组合首次同时落地，意味着专项债、特别国债、政策性开发性金融工具（PSL/DFGF）下半年放量。', keywords: [{t:'ding',v:'大力'}] },
      { text: '<b>货币：</b>"适度宽松"而非"稳健"，对应降准降息、结构性工具扩容、M1修复、M2-M1剪刀差收窄（7月末 3.7pct 预期年内继续收窄）。', keywords: [{t:'deg',v:'持续'}] },
      { text: '<b>重点产业：</b>低空经济、AI、卫星通信、两新（设备更新+消费品以旧换新）、商业不动产REITs、资本市场投融资综合改革。', keywords: [{t:'ding',v:'着力'},{t:'deg',v:'进一步'}] },
      { text: '<b>防风险：</b>常态化治理企业账款拖欠（8-21 金观平专文）、REITs 化解商业不动产存量、地方化债继续推进。', keywords: [{t:'deg',v:'持续'}] }
    ],
    docs: [
      { label: '钟才文：推动高质量发展行稳致远（人民日报·8-25 · 详解政治局六大方向）', url: 'http://paper.people.com.cn/rmrb/pc/content/202608/25/content_30177036.html' },
      { label: '金观平：把握好货币政策的力度与节奏（经济日报·8-17 · 解读适度宽松）', url: 'http://www.ce.cn/xwzx/gnsz/gdxw/202608/t20260817_3150160.shtml' },
      { label: '金观平：治理账款拖欠重在常态化（经济日报·8-21 · 下半年防风险）', url: 'http://adimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260821_3159304.shtml' },
      { label: '金观平：深化资本市场投融资综合改革（经济日报·8-02 · 政治局7月配套）', url: 'http://bgimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260802_3122358.shtml' }
    ]
  },
  {
    period: '5-6月',
    slogan: '各部委密集出台政策细则',
    status: 'pass',
    summary: '全国两会闭幕后进入"部委执行期"，3~4 月的定调性文件在 5~6 月出台<strong>配套细则、专项通知、试点名单、统计口径</strong>。2026年5月重点：<strong>产业链供应链韧性和安全水平</strong>（求是网评论员 5-22）、<strong>正确政绩观四大支柱</strong>（任仲平 5-18）、<strong>低空经济统计口径</strong>（发改低空〔2025〕1676号 2025-12 落地，2026年6月起各部委按统计分类拨款）。',
    keypoints: [
      { text: '<b>部委执行节奏：</b>每年 5~6 月专项债发行加速（上半年完成 60% 额度），发改委/工信部/住建部密集召开"半年工作部署会"。', keywords: [{t:'ding',v:'着力'}] },
      { text: '<b>政绩观信号：</b>任仲平《立党为公、为民造福、科学决策、真抓实干》（5-18）是中央对地方干部考核指挥棒的定调——影响地方项目投向（惠民生 vs 纯基建）。', keywords: [{t:'verb',v:'推动'}] },
      { text: '<b>统计口径=真金白银：</b>《低空经济及其核心产业统计分类(试行)》落地后，相关行业才能申请专项债、政府投资基金、央行再贷款等"名分+资金"支持。', keywords: [{t:'deg',v:'加速'}] }
    ],
    docs: [
      { label: '求是网评论员：如何提升产业链供应链韧性和安全水平（5-22 · 补链+强链+建链）', url: 'http://www.qstheory.cn/20260522/13b85573bc924de2946ad7cacc741004/c.html' },
      { label: '任仲平：立党为公、为民造福、科学决策、真抓实干（人民日报·5-18 · 政绩观四大支柱）', url: 'http://opinion.people.com.cn/n1/2026/0518/c461529-40721407.html' },
      { label: '发改低空〔2025〕1676号·低空经济统计分类（2025-12-26 · 5-6月配套执行）', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251226_1402669.html' }
    ]
  },
  {
    period: '4月',
    slogan: '政治局会议 · 总结Q1工作 · 微调政策',
    status: 'pass',
    summary: '<strong>4月中央政治局会议</strong>复盘一季度 GDP 增速（2026 Q2 GDP 同比 4.3%，已对应上半年累计 4.7%），判断经济开局冷暖。4 月份是"开票经济"、"AI 产业化"、"房地产政策评估期"等议题高发期，如 4-18 金观平《刺破"开票经济"的数字泡沫》就是针对一季度税务稽查数据的政策信号。',
    keypoints: [
      { text: '<b>一季度评估：</b>GDP、社零、固投、工业、出口、就业、物价七大类指标与年初预期目标对比，判断是否需要"二季度加提效"。', keywords: [{t:'deg',v:'进一步'}] },
      { text: '<b>纠偏类政策：</b>虚增开票、地方虚假项目、产能过剩等问题往往在 4 月集中点名（如"开票经济"治理，对应税务总局专项稽查+发改专项债项目复核）。', keywords: [{t:'ding',v:'坚决'}] },
      { text: '<b>房地产政策评估：</b>一季度商品房销售、房企到位资金、保交楼进度数据是否支撑继续放松（限购/首付比/利率）或结构性支持（保租房 REITs / 商业不动产 REITs）。', keywords: [{t:'verb',v:'推动'}] }
    ],
    docs: [
      { label: '金观平：刺破"开票经济"的数字泡沫（经济日报·4-18 · 6类行业开票同比下降4.7%）', url: 'http://www.ce.cn/xwzx/gnsz/gdxw/202604/t20260418_2912361.shtml' },
      { label: '国家统计局·季度国民经济运行情况专栏（4 月发布 Q1）', url: 'https://www.stats.gov.cn/sj/zxfb/' }
    ]
  },
  {
    period: '3月',
    slogan: '全国两会 · 定全年总盘子',
    status: 'pass',
    summary: '<strong>3 月全国两会</strong>（3 月上旬）是年度政策的"总开关"：《政府工作报告》定 GDP/CPI/就业/赤字率/专项债/单位GDP能耗 6 大核心预期指标；人大审议"十五五"规划纲要；3 月中下旬求是网+任仲平系统解读部署。2026 年关键词：<strong>大力实施"两新"（设备更新+消费品以旧换新）</strong>、<strong>十五五规划纲要落地</strong>、<strong>中国式现代化理论四维度创新</strong>。',
    keypoints: [
      { text: '<b>6 大预期指标：</b>GDP增速目标（2026约5%左右）、CPI（3%左右）、城镇调查失业率（5.5%左右）、赤字率（3%左右）、新增地方政府专项债、单位GDP能耗下降率。', keywords: [{t:'ding',v:'大力'}] },
      { text: '<b>"十五五"规划纲要：</b>2026 开局第一年——重大生产力布局、102 项重大工程项目清单、区域协调发展（长三角/粤港澳/成渝/京津冀）、战略性新兴产业占比。', keywords: [{t:'ding',v:'着力'}] },
      { text: '<b>任仲平万字长文：</b>3-30《从中国式现代化理论领悟为什么中国一定能成功》系统解读：新发展理念、新质生产力理论、新型举国体制、构建新发展格局。', keywords: [{t:'ding',v:'大力'}] }
    ],
    docs: [
      { label: '任仲平：从中国式现代化理论领悟为什么中国一定能成功（人民日报·3-30 · 两会精神万字解读）', url: 'http://opinion.people.com.cn/n1/2026/0330/c461529-40691063.html' },
      { label: '求是杂志评论员：凝心聚力奋进中国式现代化（求是网·3-15 · 部署"十五五"纲要）', url: 'http://www.qstheory.cn/20260314/70a1bcaa409e4cb3bfb7c6f72c73694c/c.html' },
      { label: '2026年《政府工作报告》原文（十五五开局之年）', url: 'https://www.gov.cn/yaowen/liebiao/202603/content_7062625.htm' },
      { label: '发改环资〔2025〕1745号·两新政策通知（2025-12-30 · 2026年3月两会后全面实施）', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251230_1402851.html' }
    ]
  },
  {
    period: '1-2月',
    slogan: '地方两会 · 为全国两会做准备',
    status: 'hot',
    summary: '<strong>1 月各省/自治区/直辖市两会</strong>密集召开，集中发布当年政府工作报告、地方专项债发行计划、重大项目清单，是判断全年<strong>"地方版总盘子"</strong>的窗口。<strong>中央层面：</strong>人民日报头版"钟才平/钟才文"系列密集连发（2026-01-07 至 01-13 共 6 篇钟才平 + 1 篇钟才文），为全国两会中央口径预热。<strong>2 月金轩系列 10 篇</strong>（人民日报）系统解读"十四五"经济成色、对外开放、投资于人、预期寿命等核心议题。',
    keypoints: [
      { text: '<b>钟才平=中央财经委口径预热：</b>2026年1月1月7日首亮相人民日报头版《因地制宜做好经济工作》→ 其后 1月8~13 连发 5 篇（向新向优/宏观治理效能/促消费扩投资/惠民生/扩大开放），对应全国两会《政府工作报告》的 6 大板块。', keywords: [{t:'ding',v:'着力'},{t:'verb',v:'推动'}] },
      { text: '<b>金轩系列=发改委经济宣传口径：</b>2月连发 10 篇（中国经济成色/人均预期寿命含金量/更开放的姿态/有效投资等），对应发改委两新政策、十五五重大项目、外资外贸。', keywords: [{t:'ding',v:'大力'},{t:'deg',v:'进一步'}] },
      { text: '<b>中央部委密集发文：</b>1-23 发改委连发三办法（中央预算内投资计划管理办法+国家产业技术工程化中心管理办法+国家新兴产业创新中心管理办法），1-12 政府投资基金投向评价管理办法。', keywords: [{t:'ding',v:'着力'}] },
      { text: '<b>地方两会看什么：</b>各地 GDP 目标（北京/上海/广东/浙江等强省定调是"全国风向标"）、专项债额度、重大项目数量与结构（新基建 vs 传统基建）、重点产业支持（低空/AI/卫星/两新）。', keywords: [{t:'deg',v:'加速'}] }
    ],
    docs: [
      { label: '钟才平：因地制宜做好经济工作（人民日报头版·1-07 · 首次亮相头版头条）', url: 'http://finance.people.com.cn/n1/2026/0107/c1004-40640698.html' },
      { label: '钟才文：深刻把握"五个必须" 推动"十五五"良好开局（人民日报·1-13 · 中央经济工作会议精神解读）', url: 'http://paper.people.com.cn/rmrb/pc/content/202601/13/content_30131926.html' },
      { label: '金轩：如何看待中国经济发展的成色（人民日报·2-03 · 系列之一）', url: 'http://finance.people.com.cn/n1/2026/0203/c1004-40658584.html' },
      { label: '金轩：以更开放的姿态为全球发展带来广阔机遇（人民日报·2-11 · 系列之九）', url: 'http://finance.people.com.cn/n1/2026/0211/c1004-40663843.html' },
      { label: '发改投资规〔2025〕1728号·中央预算内投资计划管理办法（1-23 发布）', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260123_1403428.html' },
      { label: '发改财金规〔2025〕1753号·政府投资基金投向评价管理办法（1-12 发布）', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260112_1403195.html' }
    ]
  }
];

// 自动生成的时间线（data/timeline.json，每日随抓取任务重算）：
// 覆盖节点 status（按北京时间判定）与本周期自动收录条目；缺失时回退到上方内置文案
var timelineAuto = null;

/**
 * 渲染年度政策时间线（竖线+圆点节点+details下拉展开）
 *
 * 节点状态与「本周期自动收录」都优先用 data/timeline.json：
 * 该文件每天随抓取任务重算（status 按北京时间判定、条目按周期窗口自动筛选），
 * 因此 9 月不会再出现「1-2月 = 🔥 当前阶段」这类过期标注。
 * 拿不到文件时回退到内置的 annualTimelineNodes（status 为人工兜底值）。
 */
function renderAnnualTimeline() {
  const list = document.getElementById('annualTimeline');
  if (!list) return;
  list.innerHTML = '<div class="at-list"></div>';
  const wrap = list.querySelector('.at-list');
  const autoNodes = (timelineAuto && timelineAuto.nodes) || {};

  annualTimelineNodes.forEach(node => {
    const auto = autoNodes[node.period] || null;
    const status = (auto && auto.status) ? auto.status : node.status;
    const wrapEl = document.createElement('div');
    wrapEl.className = 'at-node at-' + status;

    // 关键词 chip 拼接
    const kpHtml = (node.keypoints || []).map(kp => {
      const kw = (kp.keywords || []).map(x => `<span class="kw-tag kw-${x.t}" style="margin-right:3px">${x.v}</span>`).join('');
      return `<div class="at-kp">${kp.text}${kw ? '<span class="at-kw">' + kw + '</span>' : ''}</div>`;
    }).join('');

    // 原文链接卡片
    const docHtml = (node.docs || []).map(d => {
      return `<a href="${d.url}" target="_blank" class="at-doc">${d.label}</a>`;
    }).join('');

    // 本周期自动收录（来自当日抓取结果，随政策发布滚动更新）
    const autoDocs = (auto && auto.docs) || [];
    const autoDocHtml = autoDocs.map(d => {
      const s = d.source ? `<span class="at-doc-src">${escapeHtml(d.source)}</span>` : '';
      return `<a href="${d.url}" target="_blank" class="at-doc at-doc-auto">` +
             `<span class="at-doc-date">${d.date}</span>${escapeHtml(d.title)}${s}</a>`;
    }).join('');

    // 未来阶段提示
    const futureNote = status === 'future'
      ? '<div class="at-future-note">⏳ 该阶段属未来政策窗口，当前展示的是<strong>历史节奏模板</strong>与<strong>往年原文入口</strong>，方便届时快速对照；实际事件需等待会议召开后更新。</div>'
      : '';

    // 当前进度状态标签
    const metaMap = {
      hot:    '🔥 当前阶段',
      pass:   '✓ 已发生',
      future: '⏳ 预期窗口'
    };

    const detailsEl = document.createElement('details');
    detailsEl.className = 'at-details';
    // 让当前默认展开，方便用户第一眼看到
    if (status === 'hot') detailsEl.open = true;

    detailsEl.innerHTML = `
      <summary class="at-summary">
        <div class="at-sum-left">
          <span class="at-period">${node.period}</span>
          <span class="at-slogan">${node.slogan}</span>
        </div>
        <span class="at-meta">${metaMap[status] || ''}</span>
      </summary>
      <div class="at-body">
        ${futureNote}
        <div class="at-section-hd">▸ 周期定调总结</div>
        <div class="at-body-summary">${node.summary}</div>
        <div class="at-section-hd">▸ 关键政策要点（关键词定调标注）</div>
        <div class="at-kp-list">${kpHtml || '<div style="padding:8px 12px;font-size:11px;color:var(--text-muted)">暂无要点</div>'}</div>
        ${autoDocs.length ? `<div class="at-section-hd">▸ 本周期自动收录（${auto.window || ''} · ${autoDocs.length} 条 · 随每日抓取滚动更新）</div>
        <div class="at-doc-list">${autoDocHtml}</div>` : ''}
        <div class="at-section-hd">▸ 政策原文件 / 权威解读原文链接</div>
        <div class="at-doc-list">${docHtml || '<div style="padding:8px 12px;font-size:11px;color:var(--text-muted)">暂无链接</div>'}</div>
      </div>
    `;

    wrapEl.appendChild(detailsEl);
    wrap.appendChild(wrapEl);
  });
}

// 来源图标与简称（与后端 scripts/update_data.py 的 SRC_* 常量一一对应）
var SRC_ICONS = {
  '国务院最新政策文件': '🏛',
  '发改委最新政策文件': '📊',
  '央行最新动态': '🏦',
  '证监会最新动态': '📋',
  '工信部最新政策文件': '🏭',
  '国家统计局最新数据发布': '📈',
  '交易所最新公告': '🏢'
};
var SRC_SHORT = {
  '国务院最新政策文件': '国务院',
  '发改委最新政策文件': '发改委',
  '央行最新动态': '央行',
  '证监会最新动态': '证监会',
  '工信部最新政策文件': '工信部',
  '国家统计局最新数据发布': '国家统计局',
  '交易所最新公告': '交易所'
};

// 每个来源默认展开显示多少条（其余折叠，避免国务院 90+ 条铺满页面）
var FEED_GROUP_SHOW = 12;
// 默认展开几个来源分组（按最新日期排序，只展开最靠前的几组）
var FEED_GROUP_OPEN = 2;

// 渲染单条政策：结构对齐 L4「本月文件」，含摘要 / 关键词 / 关键语句 / 原文链接
function renderFeedItem(item, srcLabel) {
  var kwHtml = (item.keywords || []).map(function(k) {
    return '<span class="kw-tag kw-' + k.type + '">' + escapeHtml(k.text) + '</span>';
  }).join('');
  var isNew = item.date && isWithinDays(item.date, 3);

  var h = '<div class="doc-item">';
  h += '<div class="doc-meta">';
  h += '<div class="doc-date">' + (item.date ? item.date.slice(5) : '—') + '</div>';
  h += '<div class="doc-source">' + escapeHtml(srcLabel || '') + '</div>';
  h += '</div>';
  h += '<div class="doc-body">';
  h += '<div class="doc-title">' +
       (isNew ? '<span class="lf-new-dot" title="近3天发布"></span>' : '') +
       escapeHtml(item.title) + '</div>';
  if (item.summary) {
    h += '<div class="doc-summary">' + escapeHtml(item.summary) + '</div>';
  }
  if (item.keySentence) {
    h += '<div class="doc-keysent"><span class="doc-keysent-tag">关键语句</span>' +
         escapeHtml(item.keySentence) + '</div>';
  }
  h += '<div class="doc-keywords">' + kwHtml +
       '<a href="' + item.url + '" target="_blank" rel="noopener" class="doc-link">阅读原文 ↗</a>' +
       '</div>';
  h += '</div></div>';
  return h;
}

// L1「政策速览」—— 全来源合并的紧凑速览：一眼看清「这个周期有没有新东西」。
// 与 L4「本月文件」的分工：
//   · L1（本函数）：全来源（国务院/发改委/工信部/央行/证监会/统计局/交易所），
//                  只给「日期 + 来源 + 标题」一行一条，点标题直达原文。
//   · L4：只收「人民日报/求是网/经济日报 评论员文章 + 发改委/工信部政策」，
//         给出摘要 / 定调关键词 / 关键语句的深度精读。
// 两栏都支持 日/周/月/年 切换，且周期口径完全一致（共用 filterByPeriod），
// 避免出现「L1 说 7 条、L4 说 12 条」这种对不上的情况。
var FEED_PERIOD_LABEL = { day: '近 3 天', week: '近 7 天', month: '近 30 天', year: '本年度' };

// 发改委 / 工信部 的条目在 L4 有精读版，这里打标提示，方便两栏互相对照
var FEED_L4_SOURCES = { '发改委最新政策文件': 1, '工信部最新政策文件': 1 };

var currentFeedPeriod = 'day';

function renderTimeline() {
  var list = document.getElementById('timelineList');
  if (!list) return;

  var period = currentFeedPeriod;
  var periodLabel = FEED_PERIOD_LABEL[period] || '';

  var noteEl = document.getElementById('lfPeriodNote');
  if (noteEl) noteEl.textContent = periodLabel;

  var dateEl = document.getElementById('lfDate');
  var cntEl = document.getElementById('lfCount');

  if (!latestRawData || !latestRawData.timeline) {
    list.innerHTML = '<div class="lf-empty">正在同步最新数据…</div>';
    if (cntEl) cntEl.textContent = '';
    return;
  }

  // 按当前周期过滤 + 日期降序（filterByPeriod 内部已排序，无日期条目自动排除）
  var filtered = filterByPeriod(latestRawData.timeline, period);

  var html = '';
  filtered.forEach(function(item) {
    var src = item.desc || '其他';
    var isToday = item.date && isWithinDays(item.date, 1);
    html += '<a class="lf-row" href="' + item.url + '" target="_blank" rel="noopener">';
    html += '<span class="lf-row-date">' + (item.date || '—') + '</span>';
    html += '<span class="lf-row-src">' + (SRC_ICONS[src] || '📄') + ' ' +
            escapeHtml(SRC_SHORT[src] || src) + '</span>';
    html += '<span class="lf-row-title">' +
            (isToday ? '<span class="lf-new-dot" title="今日"></span>' : '') +
            escapeHtml(item.title) + '</span>';
    if (FEED_L4_SOURCES[src]) {
      html += '<span class="lf-l4-tag" title="该条在 L4 本月文件中有摘要 / 关键词 / 关键语句精读">L4精读</span>';
    }
    html += '<span class="lf-row-go">↗</span>';
    html += '</a>';
  });

  if (!filtered.length) {
    html = '<div class="lf-empty">' + (periodLabel || '该周期') +
           '内暂无新政策 · 可切到「月 / 年」查看更早内容</div>';
  }

  // 来源分布概览：一眼看出这个周期是「谁在发文」
  var srcCount = {};
  filtered.forEach(function(x) {
    var k = x.desc || '其他';
    srcCount[k] = (srcCount[k] || 0) + 1;
  });
  var srcLine = Object.keys(srcCount).sort(function(a, b) { return srcCount[b] - srcCount[a]; })
    .map(function(k) { return escapeHtml(SRC_SHORT[k] || k) + ' ' + srcCount[k]; })
    .join(' · ');

  list.innerHTML = html;

  if (dateEl && latestRawData.lastUpdated) {
    dateEl.textContent = '抓取于 ' + latestRawData.lastUpdated;
  }
  if (cntEl) {
    cntEl.textContent = periodLabel + ' · 共 ' + filtered.length + ' 条' +
                        (srcLine ? ' ｜ ' + srcLine : '');
  }
}

// L1 政策速览：周期切换（日 / 周 / 月 / 年）
document.querySelectorAll('[data-fperiod]').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('[data-fperiod]').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    currentFeedPeriod = btn.dataset.fperiod;
    renderTimeline();
  });
});

// ============================================================
// LAYER 4: Monthly documents data & rendering
// ============================================================
// L4 数据全部来自 data/latest.json（每日自动抓取 + 逐日累积），不再手工维护。
//   · commentary：人民日报 / 求是网 / 经济日报 的评论员文章（含「化名」文章）
//                 —— 由 scripts/update_data.py 读取数字报的 <author> 署名得到
//   · policy    ：发改委 & 工信部 的产业政策文件 —— 直接取每日抓取的 timeline
// 初版手工维护的历史评论已迁移至 data/commentary_seed.json，仅作首次打底。
function commentarySource() {
  return (latestRawData && latestRawData.commentary) || [];
}

function policySource() {
  var tl = (latestRawData && latestRawData.timeline) || [];
  return tl.filter(function(x) {
    return x.desc === '发改委最新政策文件' || x.desc === '工信部最新政策文件';
  });
}


// Reference date for period filtering (使用当前本地日期，不再硬编码过去的日期；允许「未来日期」通过，避免CDN或时区时差把刚发布的人民日报/经济日报头条误判为不存在)
const MONTHLY_REF_DATE = new Date();

function filterByPeriod(articles, period) {
  const now = MONTHLY_REF_DATE;
  return articles.filter(a => {
    const d = new Date(a.date + 'T00:00:00');
    if (period === 'year') return d.getFullYear() === now.getFullYear();
    const diffMs = now - d;
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    // 放宽下界：允许未来 1 天内的文章通过（防止缓存/UTC/报纸提前一天上线被过滤掉）
    if (period === 'day')   return diffDays <= 3  && diffDays >= -1;
    if (period === 'week')  return diffDays <= 7  && diffDays >= -1;
    if (period === 'month') return diffDays <= 30 && diffDays >= -1;
    return false;
  }).sort((a, b) => new Date(b.date) - new Date(a.date));
}

// 「从上往下看」的层级标签：中央定方向 → 部委细化路径 → 地方落实执行
var TIER_LABEL = { central: '中央', dept: '部委', local: '地方' };

// 化名表（须与 scripts/update_data.py 的 BYLINE_MAP 保持一致）。
// 只有这些集体笔名才算「化名文章」；《求是》社论、《求是》杂志评论员、
// 求是网评论员属于刊物 / 机构署名，一概标成化名会失真。
var PEN_NAMES = ['钟才文', '钟才平', '任仲平', '金轩', '仲音', '任平', '国纪平',
                 '金社平', '柯教平', '钟声', '仲祖文', '吴哲', '秋石', '石平',
                 '金观平', '钟经文'];

function bylineNote(byline) {
  if (!byline) return '';
  if (PEN_NAMES.indexOf(byline) >= 0) return '化名文章 · 重点';
  if (byline.indexOf('社论') >= 0) return '无个人署名 · 社论';
  if (byline.indexOf('评论员') >= 0 || byline.indexOf('编辑部') >= 0) return '评论员署名';
  return '';
}

function renderDocItem(item) {
  var dateStr = (item.date || '').slice(5);
  var src = item.media || item.source || '';
  var byline = item.byline || '';
  var tier = item.tier || '';
  var kws = (item.keywords || []).map(function(k) {
    return '<span class="kw-tag kw-' + k.type + '">' + k.text + '</span>';
  }).join('');

  var html = '<div class="doc-item' + (byline ? ' doc-byline-item' : '') + '">';
  html += '<div class="doc-meta">';
  html += '<div class="doc-date">' + dateStr + '</div>';
  html += '<div class="doc-source">' + escapeHtml(src) + '</div>';
  if (tier) {
    html += '<div class="tier-tag tier-' + tier + '">' + (TIER_LABEL[tier] || '') + '</div>';
  }
  html += '</div>';
  html += '<div class="doc-body">';
  html += '<div class="doc-title">' + escapeHtml(item.title) + '</div>';
  if (byline) {
    var note = bylineNote(byline);
    html += '<div class="doc-byline">★ ' + escapeHtml(byline) +
            (note ? '<span class="byline-note">' + note + '</span>' : '') + '</div>';
  }
  if (item.summary) {
    html += '<div class="doc-summary">' + escapeHtml(item.summary) + '</div>';
  }
  if (kws) {
    html += '<div class="doc-kw">' + kws + '</div>';
  }
  if (item.keySentence) {
    html += '<div class="doc-key"><b>关键语句</b>' + escapeHtml(item.keySentence) + '</div>';
  }
  html += '<div class="doc-actions"><a href="' + item.url +
          '" target="_blank" class="doc-link">阅读原文 ↗</a></div>';
  html += '</div></div>';
  return html;
}

var currentMonthlyPeriod = 'day';

function renderMonthlyDocs(period) {
  var commentaryList = document.getElementById('monthlyDocListCommentary');
  var policyList = document.getElementById('monthlyDocListPolicy');
  if (!commentaryList || !policyList) return;

  var commentaryFiltered = filterByPeriod(commentarySource(), period);
  var policyFiltered = filterByPeriod(policySource(), period);

  var emptyHtml = '<div class="doc-empty">该周期内暂无文章 —— 评论库每天自动累积，时间越长「年 / 月」视图越完整</div>';

  commentaryList.innerHTML = commentaryFiltered.length
    ? commentaryFiltered.map(renderDocItem).join('')
    : emptyHtml;
  policyList.innerHTML = policyFiltered.length
    ? policyFiltered.map(renderDocItem).join('')
    : emptyHtml;

  var cntC = document.getElementById('monthlyCountCommentary');
  if (cntC) cntC.textContent = commentaryFiltered.length + ' 篇';
  var cntP = document.getElementById('monthlyCountPolicy');
  if (cntP) cntP.textContent = policyFiltered.length + ' 篇';
}

// Monthly file period switcher
document.querySelectorAll('[data-mperiod]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-mperiod]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentMonthlyPeriod = btn.dataset.mperiod;
    renderMonthlyDocs(currentMonthlyPeriod);
  });
});

// ============================================================
// LAYER 6: 资金流向页（仅展示行业方向，无图表）
// ============================================================

// ============================================================
// LAYER 3 数据：历年政策对比 — 产业赛道 × 部门 × 3年
// 按《国民经济行业分类 GB/T 4754—2017》门类组织，重点关注「十五五」规划领域
// track: emerging=战略性新兴产业, traditional=传统支柱产业, service=现代服务业与民生
// code: 国民经济行业分类门类代码（如 C39=计算机通信制造业, J67=资本市场服务）
// 每条 yr 内：text≤15字核心表述, kw=关键词tag数组, url=官方原文链接, empty=true 则该年无文
// 所有 URL 均来自 gov.cn / ndrc / miit / csrc / mohurd / cnsa 等官方渠道，经核验可访问
// ============================================================
const compareCategories = [
  {
    key: 'emerging', label: '战略性新兴产业', icon: '🚀', color: 'var(--accent-teal)',
    codes: '门类 C制造业 / I信息技术 / G交通运输 / D电力',
    focus: '十五五 6大新兴支柱+6大未来产业'
  },
  {
    key: 'traditional', label: '传统支柱产业', icon: '🏭', color: 'var(--accent-sand)',
    codes: '门类 C制造业 / E建筑业 / K房地产业 / N生态环保',
    focus: '十五五 优化提升传统产业'
  },
  {
    key: 'digital', label: '数字经济与要素', icon: '💾', color: 'var(--accent-cyan)',
    codes: '门类 I信息传输 / 软件和信息技术服务业',
    focus: '十五五 数字中国 · 数据要素 × 实体经济'
  },
  {
    key: 'green', label: '绿色低碳与能源', icon: '🌱', color: 'var(--accent-green)',
    codes: '门类 D电力热力 / N生态保护和环境治理',
    focus: '双碳目标 · 新型能源体系'
  },
  {
    key: 'service', label: '现代服务业与民生', icon: '🏥', color: 'var(--accent-orange)',
    codes: '门类 J金融业 / R文体娱乐 / Q卫生社会工作',
    focus: '十五五 服务业优质高效+民生保障'
  },
  {
    key: 'agri', label: '农业农村', icon: '🌾', color: 'var(--accent-amber)',
    codes: '门类 A农林牧渔业',
    focus: '乡村全面振兴 · 粮食安全'
  },
  {
    key: 'enterprise', label: '经营主体', icon: '💼', color: 'var(--accent-red)',
    codes: '民营经济 / 中小企业 / 专精特新',
    focus: '两个毫不动摇 · 全国统一大市场'
  }
];

const compareData = [
  // ═══ Row 1: 🚀 战略性新兴产业（新兴支柱+未来产业）═══
  {
    track: 'emerging', code: 'C39',
    topic: '集成电路产业发展',
    summary3yr: [{y:'2024',t:'—'},{y:'2025',t:'清单+优惠'},{y:'2026',t:'—'}],
    note: '2024 —  →  2025 企业清单+税收优惠双出台  →  2026 —',
    children: [{
      dept: '工信部', icon: '🏢',
      y2024: { empty: true },
      y2025: { text: '集成电路企业清单', kw: [{t:'verb',v:'做好'},{t:'deg',v:'持续'}], url: 'https://www.miit.gov.cn/jgsj/dzs/wjfb/art/2025/art_69d6afa8264e4167945d84dca7bf29e5.html' },
      y2026: { empty: true },
      note: '政策空白(2024) → 首发企业清单(2025·定调:做好+持续) → 待跟进(2026)'
    }, {
      dept: '发改委等', icon: '🏛',
      y2024: { empty: true },
      y2025: { text: '集成电路税收优惠', kw: [{t:'ding',v:'促进'},{t:'deg',v:'持续'}], url: 'https://www.gov.cn/zhengce/zhengceku/202504/content_7016929.htm' },
      y2026: { empty: true },
      note: '政策空白(2024) → 出台税收优惠(2025·定调:促进+持续·配套企业清单) → 待跟进(2026)'
    }]
  },
  {
    track: 'emerging', code: 'I65',
    topic: '人工智能产业发展',
    summary3yr: [{y:'2024',t:'未来产业'},{y:'2025',t:'—'},{y:'2026',t:'共振+伦理'}],
    note: '2024 推动未来产业（部联科12号）  →  2025 —  →  2026 AI伦理审查+模数共振双落地',
    children: [{
      dept: '工信部', icon: '🏢',
      y2024: { text: '推动未来产业发展', kw: [{t:'verb',v:'推动'},{t:'deg',v:'加快'}], url: 'https://sdca.miit.gov.cn/zwgk/zcwj/wjfb/art/2024/art_b576470b18de4a8589e24ad37a8d9848.html' },
      y2025: { empty: true },
      y2026: { text: 'AI科技伦理审查办法', kw: [{t:'verb',v:'健全'},{t:'deg',v:'规范'}], url: 'https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_2995f16b28504ddcbb604e918eb15759.html' },
      note: '推动未来产业(2024·动:推动+程:加快·部联科12号) → 政策空窗(2025) → 健全AI伦理审查(2026·动:健全+程:规范·75号)'
    }, {
      dept: '工信部/数据局', icon: '📊',
      y2024: { empty: true },
      y2025: { empty: true },
      y2026: { text: '模数共振行动', kw: [{t:'verb',v:'深入贯彻'},{t:'deg',v:'稳妥'}], url: 'https://www.miit.gov.cn/jgsj/kjs/wjfb/art/2026/art_71c830bf78a94f498bd3c187ac8b4778.html' },
      note: '——(2024/2025) → 模数共振行动(2026·动:深入贯彻+程:稳妥·落实国务院AI+意见)'
    }]
  },
  {
    track: 'emerging', code: 'C27',
    topic: '生物医药产业发展',
    summary3yr: [{y:'2024',t:'监管改革'},{y:'2025',t:'集成创新'},{y:'2026',t:'—'}],
    note: '2024 深化药品器械监管改革（国办53号）  →  2025 江苏自贸区集成创新（国函80号）  →  2026 —',
    children: [{
      dept: '国务院/国办', icon: '🏛',
      y2024: { text: '药品器械监管改革', kw: [{t:'ding',v:'深化'},{t:'deg',v:'全面'}], url: 'https://www.gov.cn/zhengce/zhengceku/202501/content_6996117.htm' },
      y2025: { text: '江苏自贸区生物医药', kw: [{t:'verb',v:'推动'},{t:'deg',v:'集成'}], url: 'https://www.gov.cn/zhengce/zhengceku/202508/content_7037375.htm' },
      y2026: { empty: true },
      note: '深化药械监管改革(2024·定:深化+程:全面·国办53号) → 江苏自贸集成创新(2025·动:推动+程:集成·国函80号) → 待跟进(2026)'
    }]
  },
  {
    track: 'emerging', code: 'G56',
    topic: '低空经济产业发展',
    summary3yr: [{y:'2024',t:'新增长引擎'},{y:'2025',t:'推动发展'},{y:'2026',t:'基础设施'}],
    note: '2024 积极打造新增长引擎（政府工作报告）  →  2025 推动安全发展  →  2026 支撑基础设施（工信厅联通信4号）',
    children: [{
      dept: '国务院', icon: '🏛',
      y2024: { text: '积极打造低空经济', kw: [{t:'ding',v:'积极'},{t:'deg',v:'新引擎'}], url: 'https://www.gov.cn/yaowen/liebiao/202403/content_6939153.htm' },
      y2025: { text: '推动低空安全发展', kw: [{t:'verb',v:'推动'},{t:'deg',v:'安全'}], url: 'https://www.gov.cn/yaowen/liebiao/202403/content_6939153.htm' },
      y2026: { empty: true },
      note: '积极打造新增长引擎(2024·定:积极+程:新引擎·政府工作报告) → 推动安全发展(2025·动:推动+程:安全·同源延续) → ——(2026)'
    }, {
      dept: '工信部等五部门', icon: '🏢',
      y2024: { empty: true },
      y2025: { empty: true },
      y2026: { text: '支撑低空基础设施', kw: [{t:'verb',v:'加强'},{t:'deg',v:'有序'}], url: 'https://www.miit.gov.cn/zwgk/zcwj/wjfb/yj/art/2026/art_d1cb1667897e4c999a303d110b6691dc.html' },
      note: '——(2024/2025) → 加强低空基础设施(2026·动:加强+程:有序·工信厅联通信4号)'
    }]
  },
  {
    track: 'emerging', code: 'D44',
    topic: '新型储能产业发展',
    summary3yr: [{y:'2024',t:'—'},{y:'2025',t:'规模化'},{y:'2026',t:'—'}],
    note: '2024 —  →  2025 推动规模化建设行动方案（2025-2027）  →  2026 —',
    children: [{
      dept: '发改委/能源局', icon: '🏛',
      y2024: { empty: true },
      y2025: { text: '规模化建设行动方案', kw: [{t:'verb',v:'推动'},{t:'deg',v:'有序'}], url: 'https://www.gov.cn/zhengce/202509/content_7040301.htm' },
      y2026: { empty: true },
      note: '——(2024) → 规模化建设行动方案(2025·动:推动+程:有序·2025-2027三年规划) → ——(2026)'
    }]
  },
  {
    track: 'emerging', code: 'C34',
    topic: '智能机器人产业发展',
    summary3yr: [{y:'2024',t:'规范条件'},{y:'2025',t:'贯彻申报'},{y:'2026',t:'—'}],
    note: '2024 突破工业机器人规范条件（第20号公告）  →  2025 贯彻规范申报（207号）  →  2026 —',
    children: [{
      dept: '工信部', icon: '🏢',
      y2024: { text: '工业机器人规范条件', kw: [{t:'verb',v:'突破'},{t:'deg',v:'重点'}], url: 'https://sdca.miit.gov.cn/zwgk/zcwj/wjfb/art/2024/art_b576470b18de4a8589e24ad37a8d9848.html' },
      y2025: { text: '规范公告申报通知', kw: [{t:'verb',v:'贯彻'},{t:'deg',v:'严格'}], url: 'https://wap.miit.gov.cn/jgsj/zbys/gzdt/art/2025/art_e1c98830d8c244cdaae022bf1f72a267.html' },
      y2026: { empty: true },
      note: '突破规范条件(2024·动:突破+程:重点·第20号公告) → 贯彻申报通知(2025·动:贯彻+程:严格·207号) → ——(2026)'
    }]
  },
  {
    track: 'emerging', code: 'C37',
    topic: '航空航天产业发展',
    summary3yr: [{y:'2024',t:'—'},{y:'2025',t:'商业+卫星'},{y:'2026',t:'—'}],
    note: '2024 —  →  2025 商业航天+卫星通信双政策落地（工信部信管180号）  →  2026 —',
    children: [{
      dept: '国家航天局', icon: '🛰',
      y2024: { empty: true },
      y2025: { text: '商业航天行动计划', kw: [{t:'verb',v:'推进'},{t:'deg',v:'高质量'}], url: 'https://www.cnsa.gov.cn/n6758823/n6758839/c10719382/content.html' },
      y2026: { empty: true },
      note: '——(2024) → 推进商业航天行动计划(2025·动:推进+程:高质量·2025-2027) → ——(2026)'
    }, {
      dept: '工信部', icon: '🏢',
      y2024: { empty: true },
      y2025: { text: '卫星通信产业发展', kw: [{t:'verb',v:'优化'},{t:'deg',v:'有序'}], url: 'https://www.akss.gov.cn/DFS/file/2025/10/14/20251014101444632b1y4af.pdf' },
      y2026: { empty: true },
      note: '——(2024) → 优化卫星通信产业(2025·动:优化+程:有序·工信部信管180号) → ——(2026)'
    }]
  },
  {
    track: 'emerging', code: 'C26',
    topic: '新材料产业发展',
    summary3yr: [{y:'2024',t:'标准引领'},{y:'2025',t:'保险补偿'},{y:'2026',t:'—'}],
    note: '2024 引领原材料标准提升  →  2025 组织首批次保险补偿  →  2026 —',
    children: [{
      dept: '工信部', icon: '🏢',
      y2024: { text: '原材料标准提升', kw: [{t:'verb',v:'引领'},{t:'deg',v:'扎实'}], url: 'https://wap.miit.gov.cn/xwfb/mtbd/twbd/art/2024/art_816d8829308c448bb1820e62b0f56ac3.html' },
      y2025: { text: '首批次新材料保险补偿', kw: [{t:'verb',v:'组织'},{t:'deg',v:'严格'}], url: 'https://www.miit.gov.cn/jgsj/ycls/wjfb/art/2025/art_a3edb4d6e1474961917c1c16c792cfc7.html' },
      y2026: { empty: true },
      note: '引领原材料标准提升(2024·动:引领+程:扎实) → 组织首批次保险补偿(2025·动:组织+程:严格·2025-2027) → ——(2026)'
    }]
  },
  {
    track: 'emerging', code: 'C36',
    topic: '新能源汽车产业发展',
    summary3yr: [{y:'2024',t:'以旧换新'},{y:'2025',t:'回收管理'},{y:'2026',t:'—'}],
    note: '2024 推动设备更新以旧换新（国发7号）  →  2025 加强动力电池回收管理（第73号令）  →  2026 —',
    children: [{
      dept: '国务院/工信部', icon: '🏛',
      y2024: { text: '设备更新以旧换新', kw: [{t:'verb',v:'推动'},{t:'deg',v:'大规模'}], url: 'https://www.gov.cn/zhengce/content/202403/content_6939232.htm' },
      y2025: { text: '动力电池回收管理', kw: [{t:'verb',v:'加强'},{t:'deg',v:'规范'}], url: 'https://www.miit.gov.cn/api-gateway/jpaas-web-server/front/document/file-download?fileName=fa504d1fd1df406884fd616317cb7fde.pdf' },
      y2026: { empty: true },
      note: '推动设备更新以旧换新(2024·动:推动+程:大规模·国发7号) → 加强动力电池回收管理(2025·动:加强+程:规范·第73号令) → ——(2026)'
    }]
  },

  // ═══ Row 2: 🏭 传统支柱产业 ═══
  {
    track: 'traditional', code: 'C31',
    topic: '钢铁产业发展',
    summary3yr: [{y:'2024',t:'暂停置换'},{y:'2025',t:'稳增长'},{y:'2026',t:'产能置换办法'}],
    note: '2024 暂停产能置换  →  2025 促进稳增长方案  →  2026 印发加严产能置换办法',
    children: [{
      dept: '工信部', icon: '🏢',
      y2024: { text: '暂停钢铁产能置换', kw: [{t:'ding',v:'暂停'}], url: 'http://www.miit.gov.cn/jgsj/ycls/wjfb/art/2024/art_beae9b1682de4457b555b42c5f839f4f.html' },
      y2025: { text: '钢铁稳增长方案', kw: [{t:'verb',v:'促进'},{t:'deg',v:'平稳'}], url: 'https://wap.miit.gov.cn/jgsj/ycls/gt/art/2025/art_cb0ea50c423b4d43a5f517ca396b87f0.html' },
      y2026: { text: '钢铁产能置换办法', kw: [{t:'verb',v:'印发'},{t:'deg',v:'加严'}], url: 'https://www.miit.gov.cn/jgsj/ycls/gt/art/2026/art_3b0a7b6ef82a43259a544f27945e5ae4.html' },
      note: '暂停产能置换(2024·定:暂停·阶段性收紧) → 促进稳增长方案(2025·动:促进+程:平稳·2025-2026) → 印发加严产能置换办法(2026·动:印发+程:加严·新版收紧)'
    }]
  },
  {
    track: 'traditional', code: 'C25',
    topic: '石化化工产业发展',
    summary3yr: [{y:'2024',t:'—'},{y:'2025',t:'—'},{y:'2026',t:'老旧装置更新'}],
    note: '2024 —  →  2025 —  →  2026 加力推进老旧装置更新（2026-2029）',
    children: [{
      dept: '工信部等七部门', icon: '🏢',
      y2024: { empty: true },
      y2025: { empty: true },
      y2026: { text: '石化老旧装置更新', kw: [{t:'ding',v:'加力'},{t:'deg',v:'推进'}], url: 'https://wap.miit.gov.cn/jgsj/ycls/gzdt/art/2026/art_d7f9d7930d3e406883e8afea6c9b3ab3.html' },
      note: '——(2024/2025) → 加力推进老旧装置更新(2026·定:加力+程:推进·2026-2029四年规划)'
    }]
  },
  {
    track: 'traditional', code: 'K70',
    topic: '房地产产业发展',
    summary3yr: [{y:'2024',t:'止跌回稳'},{y:'2025',t:'提升品质'},{y:'2026',t:'—'}],
    note: '2024 推动止跌回稳组合拳  →  2025 提升住房品质意见（建标66号）  →  2026 —',
    children: [{
      dept: '住建部', icon: '🏗',
      y2024: { text: '房地产政策组合拳', kw: [{t:'verb',v:'推动'},{t:'deg',v:'止跌回稳'}], url: 'https://www.mohurd.gov.cn/xinwen/jsyw/art/2024/art_5f5e8be879754a2b92dd4add8069170f.html' },
      y2025: { text: '提升住房品质意见', kw: [{t:'verb',v:'提升'},{t:'deg',v:'加快'}], url: 'https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2025/art_06ba6f6ac1534042bb73a98c90581120.html' },
      y2026: { empty: true },
      note: '推动止跌回稳组合拳(2024·动:推动+程:止跌回稳) → 提升住房品质意见(2025·动:提升+程:加快·建标66号) → ——(2026)'
    }]
  },
  {
    track: 'traditional', code: '多门类',
    topic: '"两新"政策(设备更新+以旧换新)',
    summary3yr: [{y:'2024',t:'推动+加力'},{y:'2025',t:'—'},{y:'2026',t:'—'}],
    note: '2024 推动+加力支持（国务院3月+发改委7月双发文）  →  2025 —  →  2026 —',
    children: [{
      dept: '国务院', icon: '🏛',
      y2024: { text: '设备更新以旧换新', kw: [{t:'verb',v:'推动'},{t:'deg',v:'大规模'}], url: 'https://www.gov.cn/zhengce/content/202403/content_6939232.htm' },
      y2025: { empty: true },
      y2026: { empty: true },
      note: '推动设备更新以旧换新(2024·动:推动+程:大规模·国发7号·顶层定调) → ——(2025/2026)'
    }, {
      dept: '发改委/财政部', icon: '🏛',
      y2024: { text: '加力支持若干措施', kw: [{t:'ding',v:'加力'},{t:'deg',v:'支持'}], url: 'https://www.ndrc.gov.cn/xwdt/ztzl/tddgmsbgxhxfpyjhx/gzdt/202407/P020240726413585348997.pdf' },
      y2025: { empty: true },
      y2026: { empty: true },
      note: '加力支持若干措施(2024·定:加力+程:支持·发改环资1104号·配套落地) → ——(2025/2026)'
    }]
  },
  {
    track: 'traditional', code: 'N77',
    topic: '节能降碳/绿色转型',
    summary3yr: [{y:'2024',t:'加大力度'},{y:'2025',t:'—'},{y:'2026',t:'—'}],
    note: '2024 加大力度节能降碳方案（国发12号，覆盖2024-2025）  →  2025 —  →  2026 —',
    children: [{
      dept: '国务院', icon: '🏛',
      y2024: { text: '2024-2025节能降碳', kw: [{t:'ding',v:'加大'},{t:'deg',v:'更高水平'}], url: 'https://www.gov.cn/zhengce/content/202405/content_6954322.htm' },
      y2025: { empty: true },
      y2026: { empty: true },
      note: '加大力度节能降碳方案(2024·定:加大+程:更高水平·国发12号·覆盖2024-2025) → ——(2025/2026)'
    }]
  },

  // ═══ Row 3: 🏥 现代服务业与民生 ═══
  {
    track: 'service', code: 'J67',
    topic: 'REITs市场发展',
    summary3yr: [{y:'2024',t:'—'},{y:'2025',t:'高质量发展'},{y:'2026',t:'—'}],
    note: '2024 —  →  2025 推动高质量发展（证监发63号）  →  2026 —',
    children: [{
      dept: '证监会', icon: '📋',
      y2024: { empty: true },
      y2025: { text: 'REITs高质量发展', kw: [{t:'verb',v:'推动'},{t:'deg',v:'有序'}], url: 'http://www.csrc.gov.cn/csrc/c100028/c7605715/content.shtml' },
      y2026: { empty: true },
      note: '——(2024) → 推动高质量发展(2025·动:推动+程:有序·证监发63号) → ——(2026)'
    }]
  },
  {
    track: 'service', code: 'Q85',
    topic: '银发经济/养老服务业',
    summary3yr: [{y:'2024',t:'加快发展'},{y:'2025',t:'深化改革'},{y:'2026',t:'—'}],
    note: '2024 发展银发经济加快（国办1号）  →  2025 深化养老服务改革（党中央国务院意见）  →  2026 —',
    children: [{
      dept: '国务院/党中央', icon: '🏛',
      y2024: { text: '发展银发经济意见', kw: [{t:'verb',v:'发展'},{t:'deg',v:'加快'}], url: 'https://www.gov.cn/zhengce/content/202401/content_6926087.htm' },
      y2025: { text: '深化养老服务改革', kw: [{t:'ding',v:'深化'},{t:'deg',v:'进一步'}], url: 'https://www.gov.cn/gongbao/2025/issue_11826/202501/content_7001310.html' },
      y2026: { empty: true },
      note: '发展银发经济意见(2024·动:发展+程:加快·国办1号·顶层布局) → 深化养老服务改革(2025·定:深化+程:进一步·党中央国务院意见·升级) → ——(2026)'
    }]
  }
];

let currentCompareFilter = 'all';

// 自动对比数据（data/compare.json，每日随抓取任务更新）；
// 缺失时回退到下方硬编码 compareData（兜底，保证页面永不空白）
var compareAuto = null;

function renderCompareFilter() {
  const chipsEl = document.getElementById('cmpFilterChips');
  if (!chipsEl) return;

  // ── 自动模式：按 compareAuto.topics 分组 ──
  if (compareAuto && compareAuto.topics && compareAuto.topics.length) {
    const topics = compareAuto.topics;
    let html = '';
    html += '<div class="cmp-filter-all"><span class="cmp-chip active" data-track="all">📋 全部产业主题（共 ' + topics.length + ' 个 · ' + compareAuto.years.join('/') + '）</span></div>';
    compareCategories.forEach(cat => {
      const inTrack = topics.filter(t => t.track === cat.key);
      if (!inTrack.length) return;
      html += `<div class="cmp-filter-row" style="--track-color:${cat.color}">`;
      html += `<div class="cmp-row-label">`;
      html += `<span class="cat-name" style="cursor:pointer" data-track="${cat.key}" title="点击筛选整个赛道">${cat.icon} ${cat.label}（${inTrack.length}）</span>`;
      html += `<span class="cat-codes">${cat.codes}</span>`;
      html += `<span class="cat-focus">${cat.focus}</span>`;
      html += `</div>`;
      html += '<div class="cmp-row-chips">';
      inTrack.forEach(t => {
        const total = Object.values(t.counts || {}).reduce((a, b) => a + b, 0);
        html += `<span class="cmp-chip" data-topic="${t.key}"><span class="cmp-chip-code">${t.code}</span>${t.label}<span class="cmp-chip-cnt">${total}</span></span>`;
      });
      html += '</div></div>';
    });
    // 兜底：compare.json 里出现 app.js 分类表未登记的新赛道时，不能静默丢弃
    // （否则 update_compare.py 新增赛道后，页面上永远看不到）
    const knownTracks = compareCategories.map(c => c.key);
    const orphan = topics.filter(t => knownTracks.indexOf(t.track) < 0);
    if (orphan.length) {
      html += '<div class="cmp-filter-row cmp-row-orphan" style="--track-color:var(--text-muted)">';
      html += '<div class="cmp-row-label">';
      html += `<span class="cat-name" style="cursor:pointer" data-track="${orphan[0].track}" title="点击筛选整个赛道">🧩 其他赛道（${orphan.length}）</span>`;
      html += '<span class="cat-codes">app.js 的赛道分类表待补充</span>';
      html += '<span class="cat-focus">新增赛道自动兜底显示</span>';
      html += '</div>';
      html += '<div class="cmp-row-chips">';
      orphan.forEach(t => {
        const total = Object.values(t.counts || {}).reduce((a, b) => a + b, 0);
        html += `<span class="cmp-chip" data-topic="${t.key}"><span class="cmp-chip-code">${t.code}</span>${t.label}<span class="cmp-chip-cnt">${total}</span></span>`;
      });
      html += '</div></div>';
    }
    chipsEl.innerHTML = html;
    chipsEl.querySelectorAll('.cmp-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        if (e.target.classList.contains('cmp-chip-code') || e.target.classList.contains('cmp-chip-cnt')) return;
        chipsEl.querySelectorAll('.cmp-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentCompareFilter = chip.dataset.topic || chip.dataset.track || 'all';
        renderCompareTable();
      });
    });
    // 分类名点击 = 筛选整条赛道
    chipsEl.querySelectorAll('.cat-name[data-track]').forEach(el => {
      el.addEventListener('click', () => {
        chipsEl.querySelectorAll('.cmp-chip').forEach(c => c.classList.remove('active'));
        currentCompareFilter = el.dataset.track;
        renderCompareTable();
      });
    });
    return;
  }

  // ── 兜底模式：硬编码 compareData ──
  let html = '';
  // 第一行：「全部」单独成行，居中
  html += '<div class="cmp-filter-all"><span class="cmp-chip active" data-track="all">📋 全部产业赛道（共' + compareData.length + '条）</span></div>';
  // 后续每行：一个分类
  compareCategories.forEach(cat => {
    const tracks = compareData.filter(d => d.track === cat.key);
    if (!tracks.length) return;
    html += `<div class="cmp-filter-row" style="--track-color:${cat.color}">`;
    html += `<div class="cmp-row-label">`;
    html += `<span class="cat-name">${cat.icon} ${cat.label}</span>`;
    html += `<span class="cat-codes">${cat.codes}</span>`;
    html += `<span class="cat-focus">${cat.focus}</span>`;
    html += `</div>`;
    html += '<div class="cmp-row-chips">';
    tracks.forEach(item => {
      const idx = compareData.indexOf(item);
      html += `<span class="cmp-chip" data-track="${cat.key}" data-idx="${idx}"><span class="cmp-chip-code">${item.code}</span>${item.topic}</span>`;
    });
    html += '</div></div>';
  });
  chipsEl.innerHTML = html;

  chipsEl.querySelectorAll('.cmp-chip').forEach(chip => {
    chip.addEventListener('click', (e) => {
      if (e.target.classList.contains('cmp-chip-code')) return;
      chipsEl.querySelectorAll('.cmp-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const track = chip.dataset.track;
      const idx = chip.dataset.idx;
      if (track === 'all') {
        currentCompareFilter = 'all';
      } else if (idx !== undefined && idx !== '') {
        currentCompareFilter = parseInt(idx, 10);
      } else {
        currentCompareFilter = track;
      }
      renderCompareTable();
    });
  });
}

function renderCompareTable() {
  const tableEl = document.getElementById('cmpTable');
  if (!tableEl) return;

  // ── 自动模式 ──
  if (compareAuto && compareAuto.topics && compareAuto.topics.length) {
    const years = compareAuto.years;
    let items = compareAuto.topics;
    if (currentCompareFilter === 'all') {
      // 全部
    } else if (items.some(t => t.key === currentCompareFilter)) {
      items = items.filter(t => t.key === currentCompareFilter);
    } else {
      items = items.filter(t => t.track === currentCompareFilter);
    }

    const asOf = compareAuto.asOf ? ` <span style="font-weight:400;color:var(--text-muted)">(${compareAuto.asOf}在途)</span>` : '';
    let html = `<div class="cmp-hd-row">
      <div>产业主题 / 部门（发文密度）</div>
      ${years.map((y, i) => `<div>${y}年${i === years.length - 1 ? asOf : ''} <span style="font-weight:400;color:var(--text-muted)">(附原文)</span></div>`).join('')}
      <div>差异说明（力度·性质·节奏）</div>
    </div>`;

    items.forEach(item => {
      const trackClass = 'cmp-track-' + item.track;
      const cntHtml = years.map(y => {
        const n = (item.counts || {})[String(y)] || 0;
        const cls = n === 0 ? 'cmp-cnt-zero' : (n >= 20 ? 'cmp-cnt-hot' : '');
        return `<span class="cmp-cnt ${cls}">${y % 100}·${n}</span>`;
      }).join('');
      html += `
        <div class="cmp-parent ${trackClass}">
          <div class="cmp-parent-topic"><span class="cmp-chip-code">${item.code}</span>${item.label}<span class="cmp-cnt-row">${cntHtml}</span></div>
          ${item.diff ? `<div class="cmp-topic-diff">${item.diff}</div>` : ''}
        </div>
      `;
      (item.children || []).forEach(ch => {
        const renderYr = (y) => {
          const cell = (ch.years || {})[String(y)];
          if (!cell) return '<div class="cmp-child-yr"><div class="cmp-yr-empty">—</div></div>';
          const kwHtml = (cell.kw || []).map(k => `<span class="kw-tag kw-${k.type}">${k.text}</span>`).join('');
          const linkHtml = cell.url ? `<a href="${cell.url}" target="_blank" class="cmp-yr-link">↗ 原文</a>` : '';
          const noHtml = cell.docno ? `<span class="cmp-docno">${cell.docno}</span>` : '';
          const ksHtml = cell.keySentence ? `<div class="cmp-keysent">${cell.keySentence}</div>` : '';
          return `<div class="cmp-child-yr"><div class="cmp-yr-text">${kwHtml}${noHtml}<a href="${cell.url || '#'}" target="_blank" class="cmp-yr-title" rel="noopener">${cell.text}</a></div>${ksHtml}${linkHtml}</div>`;
        };
        html += `
          <div class="cmp-child ${trackClass}">
            <div class="cmp-child-dept"><span class="dept-icon">📄</span>${ch.dept}</div>
            ${years.map(y => renderYr(y)).join('')}
            <div class="cmp-child-note">${ch.diff || '—'}</div>
          </div>
        `;
      });
    });
    tableEl.innerHTML = html;
    return;
  }

  // ── 兜底模式：硬编码 compareData ──
  let items = [];
  if (currentCompareFilter === 'all') {
    items = compareData;
  } else if (typeof currentCompareFilter === 'number') {
    items = [compareData[currentCompareFilter]];
  } else {
    items = compareData.filter(d => d.track === currentCompareFilter);
  }

  let html = `
    <div class="cmp-hd-row">
      <div>产业主题 / 部门</div>
      <div>2024年 <span style="font-weight:400;color:var(--text-muted)">(附原文)</span></div>
      <div>2025年 <span style="font-weight:400;color:var(--text-muted)">(附原文)</span></div>
      <div>2026年 <span style="font-weight:400;color:var(--text-muted)">(附原文)</span></div>
      <div>差异说明（每年表述变化）</div>
    </div>
  `;

  const buildChildNote = (ch) => ch.note || '—';

  items.forEach(item => {
    const trackClass = 'cmp-track-' + item.track;
    html += `
      <div class="cmp-parent ${trackClass}">
        <div class="cmp-parent-topic"><span class="cmp-chip-code">${item.code}</span>${item.topic}</div>
      </div>
    `;
    item.children.forEach(ch => {
      const renderYr = (yr) => {
        if (!yr || yr.empty) {
          return '<div class="cmp-child-yr"><div class="cmp-yr-empty">—</div></div>';
        }
        const kwHtml = (yr.kw || []).map(k => `<span class="kw-tag kw-${k.t}">${k.v}</span>`).join('');
        const linkHtml = yr.url ? `<a href="${yr.url}" target="_blank" class="cmp-yr-link">↗ 原文</a>` : '';
        return `<div class="cmp-child-yr"><div class="cmp-yr-text">${kwHtml}${yr.text}</div>${linkHtml}</div>`;
      };
      html += `
        <div class="cmp-child ${trackClass}">
          <div class="cmp-child-dept"><span class="dept-icon">${ch.icon || '📄'}</span>${ch.dept}</div>
          ${renderYr(ch.y2024)}
          ${renderYr(ch.y2025)}
          ${renderYr(ch.y2026)}
          <div class="cmp-child-note">${buildChildNote(ch)}</div>
        </div>
      `;
    });
  });

  tableEl.innerHTML = html;
}

// ============================================================
// L2 政策信息源：四张卡片的最新文件（data/sources.json，每日随抓取任务更新）
// 卡片本身（图标/描述/标签）是编辑内容，保留 HTML 静态结构；
// 这里只把「数据」部分换掉：卡片指向最新命中文件，并插入「最近更新」一行。
// ============================================================
var sourcesAuto = null;

function renderSources() {
  var grid = document.getElementById('srcGrid');
  if (!grid || !sourcesAuto || !sourcesAuto.cards) return;
  sourcesAuto.cards.forEach(function(c) {
    var card = grid.querySelector('[data-src-key="' + c.key + '"]');
    if (!card) return;
    var lt = c.latest || null;
    var box = card.querySelector('.src-latest');

    if (!lt) {                       // 完全没数据：留一句提示，不动卡片链接
      if (box) box.parentNode.removeChild(box);
      return;
    }
    // 卡片整体指向最新命中文件（不在 <a> 里再嵌 <a>，避免非法嵌套）
    card.href = c.href || c.indexUrl;

    var age = (typeof c.ageDays === 'number') ? c.ageDays : null;
    var cls = 'src-latest';
    var note = '';
    if (c.stale) {
      cls += ' src-latest--stale';
      note = '本次抓取未命中（境外网络受限），以下为上一次成功抓取的数据';
    } else if (age !== null && age > 90) {
      cls += ' src-latest--old';
      note = '来源栏目已 ' + age + ' 天未发布新文件（不是本站未抓取）';
    }
    var html =
      '<span class="src-latest-hd">最近更新 · ' + escapeHtml(lt.date || '') + '</span>' +
      '<span class="src-latest-title">' + escapeHtml(lt.title || '') + '</span>' +
      (lt.source ? '<span class="src-latest-src">' + escapeHtml(lt.source) + '</span>' : '') +
      (note ? '<span class="src-latest-note">' + note + '</span>' : '');

    if (!box) {
      box = document.createElement('div');
      var urlEl = card.querySelector('.src-url');
      if (urlEl) card.insertBefore(box, urlEl); else card.appendChild(box);
    }
    box.className = cls;
    box.innerHTML = html;
  });
}

// ============================================================
// Chart management: render charts only when visible
// ============================================================
const chartRenderers = {
  macro: () => { renderMacroChart(); },
  gov: () => { renderTimeline(); renderAnnualTimeline(); },
  source: () => { renderSources(); },
  compare: () => { renderCompareFilter(); renderCompareTable(); },
  monthly: () => { renderMonthlyDocs(currentMonthlyPeriod); },
  csrc: () => { renderCsrc(); },
  flow: () => {}  // 资金流向页已改为纯列表形式，无需渲染图表
};

function renderChartsForPanel(panelKey) {
  if (chartRenderers[panelKey]) chartRenderers[panelKey]();
}

// ============================================================
// Window resize handler for charts
// ============================================================
window.addEventListener('resize', () => {
  if (macroChart) macroChart.resize();
});

// 渲染 L5 证监会动态顶部的实时列表（证监会/央行/交易所，来自最新一次抓取）
function renderLatestBlocks() {
  var list = document.getElementById('csrcLiveList');
  var wrap = document.getElementById('csrcLiveFeed');
  var dateEl = document.getElementById('csrcLiveDate');
  if (!list || !wrap || !latestRawData) return;

  var want = ['证监会最新动态', '交易所最新公告', '央行最新动态'];
  var blocks = latestRawData.blocks || {};

  var html = '';
  var total = 0;
  want.forEach(function(src) {
    var items = blocks[src];
    if (!items || !items.length) return;
    total += items.length;
    // L5 的主角是「监管对账单 / 审核进度」，合并流默认折叠，点开再看，避免把页面撑得太长
    html += '<details class="lf-src">';
    html += '<summary class="lf-src-hd">';
    html += '<span class="lf-src-name">' + (SRC_ICONS[src] || '📡') + ' ' + escapeHtml(src) + '</span>';
    html += '<span class="lf-count">' + items.length + ' 条</span>';
    html += '</summary>';
    html += '<div class="lf-items">';
    items.slice(0, 8).forEach(function(item) {
      html += renderFeedItem(item, SRC_SHORT[src] || '');
    });
    html += '</div></details>';
  });

  if (!total) return;
  list.innerHTML = html;
  wrap.style.display = '';
  if (dateEl && latestRawData.lastUpdated) {
    dateEl.textContent = '抓取于 ' + latestRawData.lastUpdated;
  }
}


// ============================================================
// L5「证监会动态」—— data/csrc.json 驱动
//   数据由 scripts/update_csrc.py 每日抓取生成，四块内容：
//     ① 负面清单  证监会官网「监管动态」栏目（处罚 / 措施 / 禁入）—— 谁被罚了
//     ② 正面试点  注册批复 / 政策法规 —— 谁被放行了
//     ③ 审核进度  在审状态快照 + 审批周期趋势 —— 实时试点进度条
//     ④ 官媒定调  首例 / 首单 / 首个 —— 国家级试点信号
//   周期口径与 L1／L4 共用 filterByPeriod，保证各页数字一致。
// ============================================================
var csrcData = null;
var currentCsrcPeriod = 'day';
var CSRC_LIST_CAP = 60;

var CSRC_PERIOD_LABEL = { day: '近 3 天', week: '近 7 天', month: '近 30 天', year: '本年度' };

// 标签 → 视觉强度：heavy=重罚 / mid=一般监管 / light=轻
var CSRC_TAG_KIND = {
  '市场禁入': 'heavy', '行政处罚': 'heavy', '立案调查': 'heavy', '公开谴责': 'heavy',
  '监管措施': 'mid',
  '警示函': 'light', '监管谈话': 'light', '责令改正': 'light',
  'REITs·商业不动产': 'pilot', 'REITs·基础设施': 'pilot',
  'IPO注册': 'approve', '核准批复': 'approve', '并购重组': 'approve', '基金注册': 'approve',
  '政策法规': 'policy', '审核进度公示': 'policy',
  '境外投资者资格': 'qual', '做市资格': 'qual', '托管资格': 'qual',
  '业务资格': 'qual', '机构合并': 'qual'
};

function csrcTagKind(tag) { return CSRC_TAG_KIND[tag] || 'mid'; }

// 清单单条：日期 · 类型标签 · 标题 · 直达原文
function renderCsrcItem(it) {
  var kind = csrcTagKind(it.tag);
  var isNew = it.date && isWithinDays(it.date, 3);
  return '<a class="cl-item cl-item--' + kind + '" href="' + it.url + '" target="_blank" rel="noopener">'
    + '<span class="cl-item-date">' + (it.date ? it.date.slice(5) : '—') + '</span>'
    + '<span class="cl-tag cl-tag--' + kind + '">' + escapeHtml(it.tag) + '</span>'
    + '<span class="cl-item-title">' + (isNew ? '<span class="lf-new-dot"></span>' : '')
    + escapeHtml(it.title) + '</span>'
    + '<span class="cl-item-go">↗</span></a>';
}

// 统计条：本周期条数 + 按类型分布（只统计当前周期，干净反映这一期在罚什么）
function csrcStatHtml(rows) {
  if (!rows.length) return '<span class="cl-stat-empty">本周期无记录</span>';
  var counts = {}, order = [];
  rows.forEach(function(r) {
    if (!(r.tag in counts)) { counts[r.tag] = 0; order.push(r.tag); }
    counts[r.tag]++;
  });
  order.sort(function(a, b) { return counts[b] - counts[a]; });
  var chips = order.map(function(t) {
    return '<span class="cl-stat-chip cl-stat-chip--' + csrcTagKind(t) + '">'
      + escapeHtml(t) + ' <b>' + counts[t] + '</b></span>';
  }).join('');
  return '<span class="cl-stat-total">共 <b>' + rows.length + '</b> 条</span>' + chips;
}

function fillCsrcList(id, rows) {
  var el = document.getElementById(id);
  if (!el) return;
  if (!rows.length) {
    el.innerHTML = '<div class="cl-empty">本周期暂无记录 · 换一个周期看看</div>';
    return;
  }
  var shown = rows.slice(0, CSRC_LIST_CAP);
  var html = shown.map(renderCsrcItem).join('');
  if (rows.length > shown.length) {
    html += '<div class="cl-more">仅列最新 ' + shown.length + ' 条（本周期共 '
      + rows.length + ' 条）</div>';
  }
  el.innerHTML = html;
}

function renderCsrcLedger() {
  if (!csrcData) return;
  var period = currentCsrcPeriod;
  var pen = filterByPeriod(csrcData.penalty || [], period);
  var app = filterByPeriod(csrcData.approval || [], period);
  var label = CSRC_PERIOD_LABEL[period] || '';

  var el = document.getElementById('csrcPenaltyMeta');
  if (el) el.textContent = label;
  el = document.getElementById('csrcApprovalMeta');
  if (el) el.textContent = label;

  el = document.getElementById('csrcPenaltyStat');
  if (el) el.innerHTML = csrcStatHtml(pen);
  el = document.getElementById('csrcApprovalStat');
  if (el) el.innerHTML = csrcStatHtml(app);

  fillCsrcList('csrcPenaltyList', pen);
  fillCsrcList('csrcApprovalList', app);
}

function renderCsrcBars(id, rows, cls) {
  var el = document.getElementById(id);
  if (!el) return;
  rows = rows || [];
  if (!rows.length) { el.innerHTML = '<div class="cl-empty">暂无数据</div>'; return; }
  var max = 1;
  rows.forEach(function(x) { if (x.count > max) max = x.count; });
  el.innerHTML = rows.map(function(x) {
    var pct = Math.max(6, Math.round(x.count / max * 100));
    return '<div class="rv-bar-row">'
      + '<span class="rv-bar-name" title="' + escapeHtml(x.name) + '">' + escapeHtml(x.name) + '</span>'
      + '<span class="rv-bar-track"><i class="' + cls + '" style="width:' + pct + '%"></i></span>'
      + '<span class="rv-bar-val">' + x.count + '</span></div>';
  }).join('');
}

// 审批周期趋势：内联 SVG 柱状图（近 12 个自然月「受理→注册生效」平均天数，越矮越快）
function csrcCycleSvg(byMonth) {
  if (!byMonth || byMonth.length < 2) {
    return '<div class="cl-empty">样本不足，暂不绘制趋势</div>';
  }
  var W = 560, H = 165, L = 26, R = 6, T = 20, B = 26;
  var n = byMonth.length;
  var vals = byMonth.map(function(m) { return m.avg; });
  var hi = Math.max.apply(null, vals), lo = Math.min.apply(null, vals);
  var pad = Math.max(28, (hi - lo) * 0.35);
  var top = hi + pad, bot = Math.max(0, lo - pad);
  var span = Math.max(1, top - bot);
  var iw = (W - L - R) / n;
  var bw = Math.max(5, iw * 0.5);

  var out = '<svg class="rv-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img">';
  out += '<line x1="' + L + '" y1="' + (H - B) + '" x2="' + (W - R) + '" y2="' + (H - B) + '" class="rv-axis"/>';
  byMonth.forEach(function(m, i) {
    var x = L + iw * i + (iw - bw) / 2;
    var hh = Math.max(2, (m.avg - bot) / span * (H - T - B));
    var y = H - B - hh;
    out += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1)
      + '" height="' + hh.toFixed(1) + '" rx="2" class="rv-bar"/>';
    out += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (y - 4).toFixed(1)
      + '" text-anchor="middle" class="rv-bar-val">' + m.avg + '</text>';
    out += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (H - B + 14).toFixed(1)
      + '" text-anchor="middle" class="rv-bar-x">' + m.month + '</text>';
  });
  out += '</svg>';
  out += '<div class="rv-chart-note">柱高＝当月「受理→注册生效」平均天数 · 越矮提速越明显 · 单位：天</div>';
  return out;
}

function renderCsrcReview() {
  if (!csrcData || !csrcData.review) return;
  var r = csrcData.review;
  var cy = r.cycle || {};

  var meta = document.getElementById('csrcReviewMeta');
  if (meta) meta.textContent = '数据截至 ' + (r.asOf || '—') + ' · 近两年在审口径';

  // KPI 条：审批周期变快算「好」
  var faster = cy.deltaPct != null && cy.deltaPct < 0;
  var kpis = [
    { k: '在审企业', v: r.activeTotal, u: ' 家', n: '受理 / 问询 / 过会 / 提交注册' },
    { k: '已注册生效', v: r.successTotal, u: ' 家', n: '近两年累计放行' },
    { k: '已终止撤回', v: r.failTotal, u: ' 家', n: '近两年出局' },
    { k: '审批周期', v: cy.recentAvg, u: ' 天',
      n: '近 90 天均值 · ' + (cy.verdict || ''), cls: cy.deltaPct == null ? '' : (faster ? 'good' : 'warn') }
  ];
  var kpiEl = document.getElementById('csrcReviewKpis');
  if (kpiEl) {
    kpiEl.innerHTML = kpis.map(function(x) {
      return '<div class="rv-kpi' + (x.cls ? ' rv-kpi--' + x.cls : '') + '">'
        + '<div class="rv-kpi-k">' + x.k + '</div>'
        + '<div class="rv-kpi-v">' + (x.v == null ? '—' : x.v)
        + '<span class="rv-kpi-u">' + x.u + '</span></div>'
        + '<div class="rv-kpi-n">' + escapeHtml(x.n) + '</div></div>';
    }).join('');
  }

  // 在审状态漏斗
  var stEl = document.getElementById('csrcReviewStages');
  if (stEl) {
    var stages = r.stages || [];
    var max = 1;
    stages.forEach(function(s) { if (s.count > max) max = s.count; });
    stEl.innerHTML = stages.map(function(s) {
      var pct = Math.max(3, Math.round(s.count / max * 100));
      return '<div class="rv-stage rv-stage--' + s.kind + '">'
        + '<div class="rv-stage-name">' + escapeHtml(s.name) + '</div>'
        + '<div class="rv-stage-bar"><i style="width:' + pct + '%"></i></div>'
        + '<div class="rv-stage-num">' + s.count + '</div></div>';
    }).join('');
  }

  renderCsrcBars('csrcReviewMarkets', r.markets, 'bar-cyan');
  renderCsrcBars('csrcReviewIndustries', r.industries, 'bar-sand');

  var chEl = document.getElementById('csrcReviewCycle');
  if (chEl) chEl.innerHTML = csrcCycleSvg(cy.byMonth);

  // 最近放行（注册生效）
  var apEl = document.getElementById('csrcReviewApproved');
  if (apEl) {
    var rows = (r.recentApproved || []).slice(0, 12);
    if (!rows.length) {
      apEl.innerHTML = '<div class="cl-empty">暂无记录</div>';
    } else {
      apEl.innerHTML =
        '<div class="rv-tbl-head"><span>日期</span><span>企业</span><span>板块</span>'
        + '<span>行业</span><span>周期</span></div>'
        + rows.map(function(x) {
            var fast = x.days != null && x.days <= 300;
            return '<div class="rv-tbl-row">'
              + '<span class="rv-td-date">' + (x.date || '').slice(5) + '</span>'
              + '<span class="rv-td-name">' + escapeHtml(x.company) + '</span>'
              + '<span class="rv-td-market">' + escapeHtml(x.market || '—') + '</span>'
              + '<span class="rv-td-ind" title="' + escapeHtml(x.industry) + '">'
              + escapeHtml((x.industry || '—').slice(0, 14)) + '</span>'
              + '<span class="rv-td-days' + (fast ? ' rv-td-days--fast' : '') + '">'
              + (x.days == null ? '—' : x.days + '天') + '</span></div>';
          }).join('');
    }
  }
}

function renderCsrcMedia() {
  if (!csrcData) return;
  var el = document.getElementById('csrcMediaList');
  if (!el) return;
  var rows = filterByPeriod(csrcData.media || [], currentCsrcPeriod);
  // 数据来源溯源：CI（境外 IP）抓不到官媒时，脚本会沿用上一版，这里如实标注
  var stale = (csrcData.mediaStale && csrcData.mediaFetchedAt)
    ? '<div class="media-stale">本次抓取未命中官媒（境外网络受限）· 以下为 '
      + escapeHtml(csrcData.mediaFetchedAt) + ' 抓取的数据</div>'
    : '';
  if (!rows.length) {
    el.innerHTML = stale + '<div class="cl-empty">本周期暂无官媒定调报道 · 换一个周期看看</div>';
    return;
  }
  el.innerHTML = stale + rows.slice(0, 40).map(function(m) {
    var topics = (m.topics || []).map(function(t) {
      return '<span class="media-topic">' + escapeHtml(t) + '</span>';
    }).join('');
    return '<a class="media-item' + (m.strong ? ' media-item--strong' : '')
      + '" href="' + m.url + '" target="_blank" rel="noopener">'
      + '<span class="media-date">' + (m.date || '').slice(5) + '</span>'
      + '<span class="media-src">' + escapeHtml(m.media) + '</span>'
      + '<span class="media-kw">' + escapeHtml(m.keyword) + '</span>'
      + '<span class="media-title">' + escapeHtml(m.title) + '</span>'
      + topics + '</a>';
  }).join('');
}

function renderCsrc() {
  renderCsrcLedger();
  renderCsrcReview();
  renderCsrcMedia();
}

// L5 周期切换（日 / 周 / 月 / 年）—— 只影响清单与官媒列表，
// 「发行上市审核」是当前快照，不随周期变化。
document.querySelectorAll('[data-cperiod]').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('[data-cperiod]').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    currentCsrcPeriod = btn.dataset.cperiod;
    renderCsrcLedger();
    renderCsrcMedia();
  });
});

// ============================================================
// Auto-update: fetch latest data from data/latest.json
// ============================================================
var latestRawData = null; // 全局：latest.json 原始数据

// 判断日期是否在最近 N 天内（用于「新」标记）
function isWithinDays(dateStr, days) {
  if (!dateStr) return false;
  var t = Date.parse(dateStr + 'T00:00:00');
  if (isNaN(t)) return false;
  var today = new Date();
  today.setHours(0, 0, 0, 0);
  var diff = (today.getTime() - t) / 86400000;
  return diff >= 0 && diff <= days;
}

// HTML 转义，避免标题里的 <br/> 等标签破坏布局
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/<[^>]*>/g, '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// 表头日期：先立刻填上北京时间，等 latest.json 到达后再换成真实数据日期
function setHeaderClock() {
  var clockEl = document.getElementById('clockDisplay');
  if (!clockEl) return;
  function tick() {
    var d = new Date();
    var p = function(n) { return String(n).padStart(2, '0'); };
    clockEl.textContent = p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }
  tick();
  setInterval(tick, 1000);
}

function loadLatestData() {
  // 加时间戳参数，绕过 GitHub Pages 默认 10 分钟的 CDN 缓存
  return fetch('data/latest.json?t=' + Date.now())
    .then(function(r) { return r.ok ? r.json() : null; })
    .catch(function() { return null; });
}

function applyLatestData(data) {
  if (!data) return;
  // 保存原始数据供 renderTimeline 使用
  latestRawData = data;
  // Update header "last updated" text
  if (data.lastUpdated) {
    var el = document.getElementById('headerUpdatedDate');
    if (el) el.textContent = data.lastUpdated;
    var item = el ? el.closest('.status-item') : null;
    if (item) item.title = '抓取任务最近一次成功运行日期';
  }
  // 新鲜度：抓取时间 + 最新政策日期与条数 + 评论最新日期
  freshnessState.fetched = data.fetchedAt || data.lastUpdated || '';
  freshnessState.latestDate = data.lastUpdated || '';
  var tl = (data.timeline || []).filter(function(x) { return x.date; });
  if (tl.length) {
    var ds = tl.map(function(x) { return x.date; }).sort();
    var newest = ds[ds.length - 1];
    var n = tl.filter(function(x) { return x.date === newest; }).length;
    freshnessState.newestPolicy = newest + '（' + n + ' 条）';
  }
  var com = (data.commentary || []).filter(function(x) { return x.date; });
  if (com.length) {
    var cds = com.map(function(x) { return x.date; }).sort();
    freshnessState.commentary = cds[cds.length - 1];
  }
  // 单源零命中兜底：后端在某个来源本轮 0 条时会沿用上一版，这里如实标注
  var carried = data.carriedSources || {};
  var ckeys = Object.keys(carried);
  freshnessState.carried = ckeys.length
    ? ckeys.map(function(k) { return k.replace(/(最新动态|最新政策文件|最新数据发布)$/, '') + ' ' + carried[k] + ' 条'; }).join('、')
    : '';
  renderFreshness();
}

// ============================================================
// 数据新鲜度状态条：聚合各板块生成时间，让「今天更新没有」一目了然
// ============================================================
var freshnessState = {
  fetched: '', latestDate: '', newestPolicy: '',
  macro: '', commentary: '', csrc: '', compare: '', carried: ''
};

function setFreshText(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val || '--';
}

function renderFreshness() {
  var bar = document.getElementById('freshnessBar');
  if (!bar) return;
  var f = freshnessState;

  // 主状态：抓取时间是否为今天
  var now = new Date();
  var pad = function(n) { return String(n).padStart(2, '0'); };
  var todayStr = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate());
  var fetchedDay = (f.fetched || '').slice(0, 10);
  var isToday = fetchedDay === todayStr;

  var dot = document.getElementById('freshDot');
  var main = document.getElementById('freshMain');
  if (main) {
    if (!f.fetched) {
      main.textContent = '数据加载中…';
      bar.classList.remove('is-stale');
      if (dot) dot.className = 'fresh-dot';
    } else if (isToday) {
      main.textContent = '今日已更新 · ' + f.fetched.slice(5);
      bar.classList.remove('is-stale');
      if (dot) dot.className = 'fresh-dot ok';
    } else {
      main.textContent = '今日尚未更新 · 上次 ' + (f.fetched || f.latestDate);
      bar.classList.add('is-stale');
      if (dot) dot.className = 'fresh-dot stale';
    }
  }
  setFreshText('freshLatestPolicy', f.newestPolicy);
  // 沿用标注：有兜底才显示，并给出「哪些来源、各几条」的明细
  var cItem = document.getElementById('freshCarriedItem');
  if (cItem) {
    if (f.carried) {
      cItem.classList.remove('is-hidden');
      cItem.title = '本轮未抓到这些来源（境外 CI 常见），已沿用上一版数据：' + f.carried;
      setFreshText('freshCarried', f.carried);
    } else {
      cItem.classList.add('is-hidden');
    }
  }
  // 各板块生成时间统一显示 MM-DD HH:MM
  var mm = function(v) {
    if (!v) return '--';
    return v.length >= 16 ? v.slice(5, 16) : v;
  };
  setFreshText('freshMacro', mm(f.macro));
  setFreshText('freshCommentary', f.commentary || '--');
  setFreshText('freshCsrc', mm(f.csrc));
  setFreshText('freshCompare', mm(f.compare));
}

// ============================================================
// Initial render
// ============================================================
setHeaderClock();
renderMacroCards('year');
renderTimeline();          // 旧timeline（若容器存在则渲染）
renderAnnualTimeline();    // 新年度政策时间线（官网与会议tab右侧）
renderMacroChart();
renderMonthlyDocs('day');

// Async: load latest data and re-render all data-driven sections.
// L4「本月文件」的评论与政策也都来自 latest.json，必须在这里重渲染，
// 否则首次同步渲染时 latestRawData 还是 null，页面会是空的。
loadLatestData().then(function(data) {
  if (data) {
    applyLatestData(data);
    renderTimeline();
    renderAnnualTimeline();
    renderLatestBlocks();
    renderMonthlyDocs(currentMonthlyPeriod);
  }
});

// Async: L0 宏观指标（data/macro.json，每日随抓取任务更新）
fetch('data/macro.json?t=' + Date.now())
  .then(function(r) { return r.ok ? r.json() : null; })
  .catch(function() { return null; })
  .then(function(m) {
    if (m && m.cards && m.cards.length) {
      macroAuto = m;
      renderMacroCards(currentMacroPeriod);
      renderMacroChart();
      freshnessState.macro = m.generatedAt || m.lastUpdated || '';
      renderFreshness();
    }
  });

// Async: L5 证监会动态（data/csrc.json，每日随抓取任务更新）
// 四块内容：负面清单 / 正面试点 / 发行上市审核进度 / 官媒定调
fetch('data/csrc.json?t=' + Date.now())
  .then(function(r) { return r.ok ? r.json() : null; })
  .catch(function() { return null; })
  .then(function(d) {
    if (d && (d.penalty || d.approval || d.review || d.media)) {
      csrcData = d;
      renderCsrc();
      freshnessState.csrc = d.generatedAt || '';
      renderFreshness();
    }
  });

// Async: L3 历年政策对比（data/compare.json，每日随抓取任务更新）
// 自动检索近三年「同一主题×同一部门」文件并生成力度/性质/节奏差异说明；
// 抓不到时回退到内置 compareData 硬编码兜底
fetch('data/compare.json?t=' + Date.now())
  .then(function(r) { return r.ok ? r.json() : null; })
  .catch(function() { return null; })
  .then(function(c) {
    if (c && c.topics && c.topics.length) {
      compareAuto = c;
      currentCompareFilter = 'all';
      renderCompareFilter();
      renderCompareTable();
      freshnessState.compare = c.generatedAt || '';
      renderFreshness();
    }
  });

// Async: L1 年度政策时间线（data/timeline.json，每日随抓取任务更新）
// 覆盖节点 status（按北京时间判定）与本周期自动收录条目
fetch('data/timeline.json?t=' + Date.now())
  .then(function(r) { return r.ok ? r.json() : null; })
  .catch(function() { return null; })
  .then(function(t) {
    if (t && t.nodes) {
      timelineAuto = t;
      renderAnnualTimeline();
    }
  });

// Async: L2 政策信息源卡片（data/sources.json，每日随抓取任务更新）
// 四张卡片各自的「最近更新」文件与直达链接
fetch('data/sources.json?t=' + Date.now())
  .then(function(r) { return r.ok ? r.json() : null; })
  .catch(function() { return null; })
  .then(function(s) {
    if (s && s.cards && s.cards.length) {
      sourcesAuto = s;
      renderSources();
    }
  });

// ============================================================
// LAYER 6: 资金流向（data/flow.json，每日随抓取任务更新）
// 口径：官方「资金类文件」条数作为资金节奏指标（每条附原文可核验），
// 标题/摘要里抽到金额时一并展示；按行业聚合，月 / 季 / 年与上周期对比。
// ============================================================
var flowAuto = null;
var currentFlowPeriod = 'month';
var FLOW_PERIOD_LABEL = { month: '月度', quarter: '季度', year: '年度' };

// 按周期把 ISO 日期折算成周期 key，与后端 key_of() 保持一致
function flowKey(kind, iso) {
  if (!iso || iso.length < 7) return '';
  var y = parseInt(iso.slice(0, 4), 10);
  var m = parseInt(iso.slice(5, 7), 10);
  if (kind === 'month') return iso.slice(0, 7);
  if (kind === 'quarter') return y + 'Q' + (Math.floor((m - 1) / 3) + 1);
  return String(y);
}

// 环比标签：涨用红、跌用绿（国内惯例）；上期为 0 时单独措辞
function flowDeltaChip(pct, cur, prev) {
  if (!cur && !prev) return '<span class="flow-chip flow-chip--flat">持平 · 均为 0</span>';
  if (prev === 0 && cur > 0) return '<span class="flow-chip flow-chip--up">上期为 0 · 本期新增</span>';
  if (!cur && prev > 0) return '<span class="flow-chip flow-chip--down">本期为 0</span>';
  if (pct === null || pct === undefined) return '<span class="flow-chip flow-chip--flat">—</span>';
  var cls = pct > 0 ? 'flow-chip--up' : (pct < 0 ? 'flow-chip--down' : 'flow-chip--flat');
  var sign = pct > 0 ? '+' : '';
  return '<span class="flow-chip ' + cls + '">环比 ' + sign + pct + '%</span>';
}

function flowDocsHtml(items, limit) {
  if (!items || !items.length) return '<div class="cl-empty">该周期无新条目</div>';
  var html = '';
  items.slice(0, limit || 20).forEach(function(it) {
    html += '<div class="cl-item">'
      + '<div class="cl-item-title"><a href="' + escapeHtml(it.url) + '" target="_blank" rel="noopener">'
      + escapeHtml(it.title) + '</a></div>'
      + '<div class="cl-item-meta">' + escapeHtml(it.date || '')
      + (it.org ? ' · ' + escapeHtml(it.org) : '')
      + (it.industry ? ' · ' + escapeHtml(it.industry) : '')
      + (it.amountYi ? ' · <b>' + it.amountYi + ' 亿元</b>' : '')
      + (it.src ? ' · ' + escapeHtml(it.src) : '')
      + '</div></div>';
  });
  return html;
}

function renderFlow() {
  var f = flowAuto;
  if (!f || !f.channels) return;
  var kind = currentFlowPeriod;

  // —— 摘要行：生成时间 + 口径 + 累积库规模 ——
  var noteEl = document.getElementById('flowNote');
  if (noteEl) {
    noteEl.innerHTML = '📅 数据抓取于 <b>' + escapeHtml(f.generatedAt || '--')
      + '</b> · 口径：' + escapeHtml(f.note || '')
      + ' · 累积库 ' + (f.archiveTotal || 0) + ' 条（本轮新增 ' + (f.archiveAdded || 0) + ' 条）';
  }

  // —— 跨通道合计 ——
  var totCur = 0, totPrev = 0, totAmt = 0, curLabel = '', prevLabel = '';
  f.channels.forEach(function(ch) {
    var p = (ch.period || {})[kind];
    if (!p) return;
    totCur += p.cur.n || 0;
    totPrev += p.prev.n || 0;
    totAmt += p.cur.amountYi || 0;
    curLabel = p.cur.label || curLabel;
    prevLabel = p.prev.label || prevLabel;
  });
  var kpiEl = document.getElementById('flowKpis');
  if (kpiEl) {
    var totalPct = totPrev ? Math.round((totCur - totPrev) * 1000 / totPrev) / 10 : null;
    kpiEl.innerHTML = ''
      + '<div class="data-card flow-kpi"><div class="card-title">本周期合计</div>'
      + '<div class="flow-kpi-val">' + totCur + ' <span class="flow-kpi-unit">件</span></div>'
      + '<div class="card-sub">' + escapeHtml(curLabel) + '（' + FLOW_PERIOD_LABEL[kind] + '）</div></div>'
      + '<div class="data-card flow-kpi"><div class="card-title">上周期合计</div>'
      + '<div class="flow-kpi-val">' + totPrev + ' <span class="flow-kpi-unit">件</span></div>'
      + '<div class="card-sub">' + escapeHtml(prevLabel) + '</div></div>'
      + '<div class="data-card flow-kpi"><div class="card-title">环比变化</div>'
      + '<div class="flow-kpi-val">' + (totalPct === null ? '—' : (totalPct > 0 ? '+' : '') + totalPct + '%')
      + '</div><div class="card-sub">' + flowDeltaChip(totalPct, totCur, totPrev).replace(/<[^>]+>/g, '') + '</div></div>'
      + '<div class="data-card flow-kpi"><div class="card-title">抽到金额</div>'
      + '<div class="flow-kpi-val">' + (totAmt ? totAmt : '—') + '<span class="flow-kpi-unit">亿元</span></div>'
      + '<div class="card-sub">仅统计原文中明示金额的条目</div></div>';
  }

  // —— 四个通道 ——
  var chEl = document.getElementById('flowChannels');
  if (chEl) {
    var html = '';
    f.channels.forEach(function(ch) {
      var p = (ch.period || {})[kind];
      if (!p) return;
      var inds = (ch.industries || {})[kind] || [];
      var maxN = 1;
      inds.forEach(function(r) { if (r.cur > maxN) maxN = r.cur; });
      var bars = '';
      if (!inds.length) {
        bars = '<div class="cl-empty">该周期官方暂无新增文件</div>';
      } else {
        inds.slice(0, 5).forEach(function(r) {
          bars += '<div class="flow-ind-row">'
            + '<div class="flow-ind-name">' + escapeHtml(r.name) + '</div>'
            + '<div class="flow-bar"><div class="flow-bar-seg" style="width:'
            + Math.max(6, Math.round(r.cur * 100 / maxN)) + '%">' + r.cur + '</div></div>'
            + '<div class="flow-ind-prev">上期 ' + r.prev + ' · '
            + (r.deltaPct === null ? '—' : (r.deltaPct > 0 ? '+' : '') + r.deltaPct + '%') + '</div>'
            + '</div>';
        });
      }
      var items = [];
      inds.forEach(function(r) { (r.items || []).forEach(function(x) { items.push(x); }); });
      items.sort(function(a, b) { return (b.date || '').localeCompare(a.date || ''); });
      html += '<div class="flow-card">'
        + '<div class="flow-card-title">' + (ch.icon || '') + ' ' + escapeHtml(ch.label) + '</div>'
        + '<div class="flow-card-sub">' + escapeHtml(ch.sources || '')
        + (ch.dim === '类型' ? ' · 按审核类型归类' : ' · 按行业归类') + '</div>'
        + '<div class="flow-card-kpi"><b>' + p.cur.n + '</b> 件'
        + '<span class="flow-card-vs">vs 上期 ' + p.prev.n + ' 件</span>'
        + flowDeltaChip(p.deltaPct, p.cur.n, p.prev.n)
        + (p.cur.amountYi ? '<span class="flow-card-amt">金额 ' + p.cur.amountYi + ' 亿元</span>' : '')
        + '</div>'
        + '<div class="flow-card-desc">' + escapeHtml(ch.desc || '') + '</div>'
        + bars
        + '<div class="flow-doc-list">' + flowDocsHtml(items, 4) + '</div>'
        + '</div>';
    });
    chEl.innerHTML = html || '<div class="cl-empty">暂无数据</div>';
  }

  // —— 行业增减榜 ——
  var mv = (f.movers || {})[kind] || {};
  var mvHd = document.getElementById('flowMoverHd');
  if (mvHd) {
    mvHd.textContent = '▸ 行业增减榜（' + (FLOW_PERIOD_LABEL[kind] || '') + '对比上期，跨三个行业维度通道）';
  }
  var mvEl = document.getElementById('flowMovers');
  if (mvEl) {
    var row = function(r, cls, tag) {
      return '<div class="flow-mover ' + cls + '"><span class="flow-mover-tag">' + tag + '</span>'
        + '<span class="flow-mover-name">' + escapeHtml(r.name) + '</span>'
        + '<span class="flow-mover-num">' + r.cur + ' 件 <i>（上期 ' + r.prev + '）</i></span>'
        + '<span class="flow-mover-delta">' + (r.deltaPct === null ? '—' : (r.deltaPct > 0 ? '+' : '') + r.deltaPct + '%') + '</span>'
        + (r.url ? '<a class="doc-link" href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener">原文 ↗</a>' : '')
        + '</div>';
    };
    var h = '';
    (mv.up || []).forEach(function(r) { h += row(r, 'is-up', '📈 增加'); });
    (mv.down || []).forEach(function(r) { h += row(r, 'is-down', '📉 减少'); });
    (mv.flat || []).slice(0, 2).forEach(function(r) { h += row(r, 'is-flat', '➖ 持平'); });
    mvEl.innerHTML = h || '<div class="cl-empty">该周期行业分布无明显变化</div>';
  }

  // —— 本周期原文清单（全通道合并，按日期倒序）——
  var docEl = document.getElementById('flowDocs');
  if (docEl) {
    var curKey = '';
    var seen = {}, merged = [];
    f.channels.forEach(function(ch) {
      var p = (ch.period || {})[kind];
      if (p) curKey = p.cur.key;
      var inds = (ch.industries || {})[kind] || [];
      inds.forEach(function(r) {
        (r.items || []).forEach(function(x) {
          if (seen[x.url]) return;
          seen[x.url] = 1;
          x.channel = ch.label;
          merged.push(x);
        });
      });
    });
    (f.recent || []).forEach(function(x) {
      if (seen[x.url]) return;
      if (flowKey(kind, x.date) !== curKey) return;
      seen[x.url] = 1;
      x.channel = x.channel || '';
      merged.push(x);
    });
    merged.sort(function(a, b) { return (b.date || '').localeCompare(a.date || ''); });
    docEl.innerHTML = flowDocsHtml(merged, 24);
  }
}

// 周期切换（年度 / 季度 / 月度）
(function bindFlowSwitcher() {
  var wrap = document.getElementById('flowSwitcher');
  if (!wrap) return;
  wrap.querySelectorAll('.tier-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      if (btn.dataset.fperiod === currentFlowPeriod) return;
      wrap.querySelectorAll('.tier-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentFlowPeriod = btn.dataset.fperiod;
      renderFlow();
    });
  });
})();

// Async: L6 资金流向（data/flow.json，每日随抓取任务更新）
fetch('data/flow.json?t=' + Date.now())
  .then(function(r) { return r.ok ? r.json() : null; })
  .catch(function() { return null; })
  .then(function(f) {
    if (f && f.channels && f.channels.length) {
      flowAuto = f;
      renderFlow();
    }
  });
