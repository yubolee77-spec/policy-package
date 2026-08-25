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

function renderMacroCards(period) {
  const grid = document.getElementById('macroGrid');
  grid.innerHTML = '';
  macroData[period].forEach(item => {
    const card = document.createElement('a');
    card.href = item.url;
    card.target = '_blank';
    card.className = 'data-card';
    const arrow = item.dir === 'pos' ? '▲' : (item.dir === 'neg' ? '▼' : '→');
    card.innerHTML = `
      <div class="card-hd">
        <div>
          <div class="card-title">${item.name}</div>
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
  // 2026年1-7月真实月度数据（来源：国家统计局）
  const monthLabels = ['2026-01','2026-02','2026-03','2026-04','2026-05','2026-06','2026-07'];
  // CPI同比(%)：1月数据未单列(1-2月平均0.8%)，2-7月真实数据
  const cpiData = [null, 1.3, 1.0, 1.2, 1.2, 1.0, 0.5];
  // PPI同比(%)：仅6月4.1%、7月3.5%查证到具体数字
  const ppiData = [null, null, null, null, null, 4.1, 3.5];
  // PMI(%)：完整月度数据
  const pmiData = [49.3, 49.0, 50.4, 50.3, 50.0, 50.3, 49.2];
  const softAmber = '#c9a86a';
  const softRed  = '#c97878';
  const softGreen = '#7ab88c';
  const softSand = '#d4b07a';
  const option = {
    backgroundColor: 'transparent',
    title: {
      text: '核心宏观指标趋势（2026年1-7月）',
      subtext: '数据来源：国家统计局 · CPI/PPI 同比(%)、PMI · 缺失月份未查证到具体数字',
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
      { title: '专项债投向结构优化', desc: '新兴产业专项债与交通类占比待核实', url: 'https://www.mof.gov.cn/difaikuang/2799821.htm' }
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
      { label: '2024年中央经济工作会议通稿（参考模板）', url: 'https://www.gov.cn/xinwen/2024-12/12/content_6997648.htm' },
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
      { label: '历年政治局会议·新华社通稿专栏', url: 'http://www.news.cn/politics/zhongyang.htm' },
      { label: '中国政府网·中共中央政治局集体学习/会议', url: 'https://www.gov.cn/yaowen/liebiao/zhengzhi.htm' }
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
      { label: '人民日报·二十届三中全会专题（参考框架）', url: 'http://paper.people.com.cn/rmrb/html/' },
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

/**
 * 渲染年度政策时间线（竖线+圆点节点+details下拉展开）
 */
function renderAnnualTimeline() {
  const list = document.getElementById('annualTimeline');
  if (!list) return;
  list.innerHTML = '<div class="at-list"></div>';
  const wrap = list.querySelector('.at-list');

  annualTimelineNodes.forEach(node => {
    const wrapEl = document.createElement('div');
    wrapEl.className = 'at-node at-' + node.status;

    // 关键词 chip 拼接
    const kpHtml = (node.keypoints || []).map(kp => {
      const kw = (kp.keywords || []).map(x => `<span class="kw-tag kw-${x.t}" style="margin-right:3px">${x.v}</span>`).join('');
      return `<div class="at-kp">${kp.text}${kw ? '<span class="at-kw">' + kw + '</span>' : ''}</div>`;
    }).join('');

    // 原文链接卡片
    const docHtml = (node.docs || []).map(d => {
      return `<a href="${d.url}" target="_blank" class="at-doc">${d.label}</a>`;
    }).join('');

    // 未来阶段提示
    const futureNote = node.status === 'future'
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
    if (node.status === 'hot') detailsEl.open = true;

    detailsEl.innerHTML = `
      <summary class="at-summary">
        <div class="at-sum-left">
          <span class="at-period">${node.period}</span>
          <span class="at-slogan">${node.slogan}</span>
        </div>
        <span class="at-meta">${metaMap[node.status] || ''}</span>
      </summary>
      <div class="at-body">
        ${futureNote}
        <div class="at-section-hd">▸ 周期定调总结</div>
        <div class="at-body-summary">${node.summary}</div>
        <div class="at-section-hd">▸ 关键政策要点（关键词定调标注）</div>
        <div class="at-kp-list">${kpHtml || '<div style="padding:8px 12px;font-size:11px;color:var(--text-muted)">暂无要点</div>'}</div>
        <div class="at-section-hd">▸ 政策原文件 / 权威解读原文链接</div>
        <div class="at-doc-list">${docHtml || '<div style="padding:8px 12px;font-size:11px;color:var(--text-muted)">暂无链接</div>'}</div>
      </div>
    `;

    wrapEl.appendChild(detailsEl);
    wrap.appendChild(wrapEl);
  });
}

// 兼容保留：旧的 timelineData 列表（供 data/latest.json 自动更新时内部复用）渲染
function renderTimeline() {
  const list = document.getElementById('timelineList');
  if (list) {
    list.innerHTML = '';
    timelineData.forEach(group => {
      group.items.forEach((item, idx) => {
        const tlItem = document.createElement('div');
        tlItem.className = 'tl-item';
        tlItem.innerHTML = `
          <div class="tl-month">${idx === 0 ? group.month : ''}</div>
          <div class="tl-body">
            <div class="tl-title">${item.title}</div>
            <div class="tl-desc">${item.desc}</div>
            <div class="tl-docs">
              <a href="${item.url}" target="_blank" class="tl-doc">📄 原文件: ${item.url}</a>
            </div>
          </div>
        `;
        list.appendChild(tlItem);
      });
    });
  }
}

// ============================================================
// LAYER 4: Monthly documents data & rendering
// ============================================================
const monthlyData = {
  commentary: [
    { date: '2026-08-25', source: '人民日报', title: '钟才文：推动高质量发展行稳致远', summary: '7月30日政治局会议部署下半年经济工作，明确宏观政策发力提效、扩大内需、产业体系建设、市场竞争环境、国际经贸、民生保障六大方向。关键词：', url: 'http://paper.people.com.cn/rmrb/pc/content/202608/25/content_30177036.html', keywords: [{type:'ding', text:'着力'}, {type:'verb', text:'推动'}] },
    { date: '2026-08-24', source: '人民日报', title: '钟才文：上半年经济增长4.7%说明了什么？', summary: '解读上半年GDP 4.7%增速：符合预期目标、有含金量（新动能贡献超四成）、有强劲韧性、富有后劲。关键词：', url: 'http://paper.people.com.cn/rmrb/pc/content/202608/24/content_30176629.html', keywords: [{type:'deg', text:'持续'}] },
    { date: '2026-08-23', source: '人民日报', title: '钟才文：中国是世界经济增长的积极贡献者和强大稳定锚', summary: '中国经济顶压前行向新向优：对世界增长贡献率30%左右、上半年增长4.7%、外贸出口强劲、创新成果加速走向世界。关键词：', url: 'http://paper.people.com.cn/rmrb/pc/content/202608/23/content_30176537.html', keywords: [{type:'ding', text:'大力'}] },
    { date: '2026-08-23', source: '经济日报', title: '金观平：企业应成为科技创新"出题人"', summary: '推动科技创新和产业创新深度融合，企业应从技术应用者成长为创新组织者、科研"出题人"。关键词：', url: 'http://adimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260823_3164440.shtml', keywords: [{type:'verb', text:'推动'}] },
    { date: '2026-08-22', source: '经济日报', title: '金观平：驾驭好人工智能这匹"千里马"', summary: '统筹人工智能发展与安全，核心产业规模超1.2万亿元、企业超6200家、重点行业渗透率突破80%。关键词：', url: 'http://adimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260822_3162960.shtml', keywords: [{type:'deg', text:'进一步'}] },
    { date: '2026-08-21', source: '经济日报', title: '金观平：治理账款拖欠重在常态化', summary: '中央政治局会议提出常态化解决企业账款拖欠问题。关键词：', url: 'http://adimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260821_3159304.shtml', keywords: [{type:'deg', text:'持续'}] },
    { date: '2026-08-17', source: '经济日报', title: '金观平：把握好货币政策的力度与节奏', summary: '政治局会议强调实施好更加积极的财政政策和适度宽松的货币政策，把握力度与节奏，兼顾稳增长、调结构与防风险。关键词：', url: 'http://www.ce.cn/xwzx/gnsz/gdxw/202608/t20260817_3150160.shtml', keywords: [{type:'ding', text:'着力'}] },
    { date: '2026-08-02', source: '经济日报', title: '金观平：深化资本市场投融资综合改革', summary: '中央政治局会议提出深化资本市场投融资综合改革，提升韧性和信心。关键词：', url: 'http://bgimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260802_3122358.shtml', keywords: [{type:'deg', text:'进一步'}] },
    { date: '2026-07-01', source: '人民日报', title: '任仲平：把握历史主动 实现伟大复兴', summary: '建党105周年之际，任仲平万字长文解读党的百年奋斗历程、习近平党建思想、全面从严治党、四个全面战略布局。关键词：', url: 'http://opinion.people.com.cn/n1/2026/0701/c461529-40751143.html', keywords: [{type:'ding', text:'大力'}] },
    { date: '2026-05-22', source: '求是网', title: '求是网评论员：如何提升产业链供应链韧性和安全水平', summary: '补链、强链、建链——统筹推进产业链供应链安全。', url: 'http://www.qstheory.cn/20260522/13b85573bc924de2946ad7cacc741004/c.html', keywords: [] },
    { date: '2026-05-18', source: '人民日报', title: '任仲平：立党为公、为民造福、科学决策、真抓实干', summary: '任仲平文章阐释正确政绩观四大支柱：立党为公是根本立场、为民造福是核心要求、科学决策是关键方法、真抓实干是必由之路。关键词：', url: 'http://opinion.people.com.cn/n1/2026/0518/c461529-40721407.html', keywords: [{type:'ding', text:'着力'}] },
    { date: '2026-04-18', source: '经济日报', title: '金观平：刺破"开票经济"的数字泡沫', summary: '最新发票数据显示，截至3月25日，废弃资源综合利用等六类行业开票金额同比下降4.7%，防治"开票经济"取得阶段性成效。关键词：', url: 'http://www.ce.cn/xwzx/gnsz/gdxw/202604/t20260418_2912361.shtml', keywords: [{type:'verb', text:'推动'}] },
    { date: '2026-03-30', source: '人民日报', title: '任仲平：从中国式现代化理论领悟为什么中国一定能成功', summary: '系统解读中国式现代化理论：新发展理念、新质生产力理论、新型举国体制、构建新发展格局四个维度的战略创新。关键词：', url: 'http://opinion.people.com.cn/n1/2026/0330/c461529-40691063.html', keywords: [{type:'ding', text:'大力'}] },
    { date: '2026-03-15', source: '求是网', title: '求是杂志评论员：凝心聚力奋进中国式现代化', summary: '解读全国两会精神，部署"十五五"规划纲要落地落实。', url: 'http://www.qstheory.cn/20260314/70a1bcaa409e4cb3bfb7c6f72c73694c/c.html', keywords: [] },
    { date: '2026-02-12', source: '人民日报', title: '金轩：以有效投资为高质量发展提供坚实支撑', summary: '人民日报2月连续10天刊发"金轩"系列评论之十：贯通供给需求推动经济良性循环、优化供给结构塑造长期增长动能、发挥综合效益增强综合国力。关键词：', url: 'http://www.ce.cn/xwzx/gnsz/gdxw/202602/t20260212_2769406.shtml', keywords: [{type:'ding', text:'着力'}] },
    { date: '2026-02-11', source: '人民日报', title: '金轩：以更开放的姿态为全球发展带来广阔机遇', summary: '金轩系列评论之九：扩大市场机遇、稳定产业链供应链、推进制度型开放、高质量共建"一带一路"四方面展现对外开放决心。关键词：', url: 'http://finance.people.com.cn/n1/2026/0211/c1004-40663843.html', keywords: [{type:'deg', text:'进一步'}] },
    { date: '2026-02-04', source: '人民日报', title: '金轩：人均预期寿命提升一岁的含金量', summary: '金轩系列评论之二：2025年我国人均预期寿命达79岁，连续3个五年规划均提高一岁以上，解读医疗卫生、社会保障、"一老一小"支撑体系。关键词：', url: 'http://finance.people.com.cn/n1/2026/0206/c1004-40660946.html', keywords: [{type:'deg', text:'持续'}] },
    { date: '2026-02-03', source: '人民日报', title: '金轩：如何看待中国经济发展的成色', summary: '金轩系列评论之首篇：从物质基础、新动能、含绿量、发展成果惠及全体人民四个维度，解读中国经济"十四五"含金量。关键词：', url: 'http://finance.people.com.cn/n1/2026/0203/c1004-40658584.html', keywords: [{type:'ding', text:'大力'}] },
    { date: '2026-02-03', source: '经济日报', title: '金观平："投资于人"是破解供强需弱关键', summary: '供给强需求弱是当前最突出矛盾，"投资于人"是关键。关键词：', url: 'http://www.ce.cn/xwzx/gnsz/gdxw/202602/t20260203_2745939.shtml', keywords: [{type:'deg', text:'进一步'}] },
    { date: '2026-01-30', source: '经济日报', title: '金观平：推动物价合理回升', summary: 'CPI连续4个月回升，2025年12月同比上涨0.8%创近34个月新高。关键词：', url: 'http://views.ce.cn/view/ent/202601/t20260130_2737865.shtml', keywords: [{type:'verb', text:'推动'}] },
    { date: '2026-01-13', source: '人民日报', title: '钟才文：深刻把握"五个必须" 推动"十五五"良好开局', summary: '解读中央经济工作会议"五个必须"：充分挖掘经济潜能、政策支持和改革创新并举、既"放得活"又"管得好"、投资于物和投资于人紧密结合、以苦练内功应对外部挑战。关键词：', url: 'http://paper.people.com.cn/rmrb/pc/content/202601/13/content_30131926.html', keywords: [{type:'ding', text:'着力'}] },
    { date: '2026-01-12', source: '人民日报', title: '钟才平：持续扩大开放，为世界提供新机遇', summary: '坚持对外开放，为世界提供新机遇。关键词：', url: 'http://finance.people.com.cn/n1/2026/0112/c1004-40643305.html', keywords: [{type:'deg', text:'持续'}] },
    { date: '2026-01-11', source: '人民日报', title: '钟才平：以惠民生为牵引，打开发展新空间', summary: '以惠民生为牵引，打开发展新空间。关键词：', url: 'http://finance.people.com.cn/n1/2026/0111/c1004-40642822.html', keywords: [{type:'verb', text:'推动'}] },
    { date: '2026-01-10', source: '人民日报', title: '钟才平：统筹促消费和扩投资，建设强大国内市场', summary: '强大国内市场是中国式现代化的战略依托。坚持内需主导，建设强大国内市场。关键词：', url: 'http://finance.people.com.cn/n1/2026/0110/c1004-40642697.html', keywords: [{type:'ding', text:'大力'}] },
    { date: '2026-01-09', source: '人民日报', title: '钟才平：发挥政策集成效应，提升宏观经济治理效能', summary: '发挥政策集成效应，提升宏观经济治理效能。关键词：', url: 'http://finance.people.com.cn/n1/2026/0109/c1004-40642071.html', keywords: [{type:'ding', text:'着力'}] },
    { date: '2026-01-08', source: '人民日报', title: '钟才平：向新向优发展，中国经济向好', summary: '中国经济向新向优发展，向好态势持续。关键词：', url: 'http://finance.people.com.cn/n1/2026/0108/c1004-40641557.html', keywords: [{type:'ding', text:'着力'}] },
    { date: '2026-01-07', source: '人民日报', title: '钟才平：因地制宜做好经济工作', summary: '习近平总书记强调"因地制宜，本质是实事求是"。这是"钟才平"首次出现在人民日报头版。关键词：', url: 'http://finance.people.com.cn/n1/2026/0107/c1004-40640698.html', keywords: [{type:'verb', text:'推动'}] }
  ],
  policy: [
    { date: '2026-01-23', source: '发改委', title: '《中央预算内投资计划管理办法》(发改投资规〔2025〕1728号)', summary: '发改委印发，规范中央预算内投资计划管理，提升投资效益。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260123_1403428.html', keywords: [{type:'ding', text:'着力'}] },
    { date: '2026-01-23', source: '发改委', title: '《国家产业技术工程化中心管理办法》(发改高技规〔2025〕1747号)', summary: '发改委发布，规范国家产业技术工程化中心管理。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260123_1403416.html', keywords: [{type:'verb', text:'推动'}] },
    { date: '2026-01-23', source: '发改委', title: '《国家新兴产业创新中心管理办法》(发改高技规〔2025〕1748号)', summary: '发改委发布，规范国家新兴产业创新中心管理。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260123_1403415.html', keywords: [{type:'verb', text:'推动'}] },
    { date: '2026-01-12', source: '发改委', title: '《政府投资基金投向评价管理办法(试行)》(发改财金规〔2025〕1753号)', summary: '发改委发布，规范政府投资基金投向评价管理。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/202601/t20260112_1403195.html', keywords: [{type:'deg', text:'进一步'}] },
    { date: '2025-12-31', source: '发改委', title: '《再生材料应用推广行动方案》(发改环资〔2025〕1681号)', summary: '发改委发布，推动再生材料应用推广。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251231_1402965.html', keywords: [{type:'verb', text:'推动'}] },
    { date: '2025-12-31', source: '发改委', title: '《关于促进电网高质量发展的指导意见》(发改能源〔2025〕1710号)', summary: '发改委发布，促进电网高质量发展。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251231_1402949.html', keywords: [{type:'ding', text:'大力'}] },
    { date: '2025-12-30', source: '发改委', title: '《关于2026年实施大规模设备更新和消费品以旧换新政策的通知》(发改环资〔2025〕1745号)', summary: '大力实施"两新"政策，持续扩大覆盖面。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251230_1402851.html', keywords: [{type:'ding', text:'大力'}, {type:'deg', text:'持续'}] },
    { date: '2025-12-26', source: '发改委', title: '《低空经济及其核心产业统计分类(试行)》(发改低空〔2025〕1676号)', summary: '发改委印发，着力培育低空经济为新兴支柱产业，加速空域改革。关键词：', url: 'https://www.ndrc.gov.cn/xxgk/zcfb/tz/202512/t20251226_1402669.html', keywords: [{type:'ding', text:'着力'}, {type:'deg', text:'加速'}] },
    { date: '2025-12-10', source: '工信部', title: '《产业技术基础公共服务平台管理办法》(工信部科〔2025〕261号)', summary: '工信部发布，规范产业技术基础公共服务平台管理。关键词：', url: 'https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/art/2025/art_8d58788c9ccc448fb8428812a1734b86.html', keywords: [{type:'verb', text:'推动'}] },
    { date: '2025-11-11', source: '工信部', title: '《关于进一步加快制造业中试平台体系化布局和高水平建设的通知》(工信厅科函〔2025〕456号)', summary: '工信部发布，加快制造业中试平台体系化布局和高水平建设。关键词：', url: 'https://www.miit.gov.cn/zwgk/zcwj/wjfb/tz/art/2025/art_69551d935e654671a8816123f1b6ec4f.html', keywords: [{type:'deg', text:'进一步'}] },
    { date: '2025-10-13', source: '工信部', title: '《深入推动服务型制造创新发展实施方案(2025—2028年)》(工信部联政法〔2025〕202号)', summary: '工信部发布，深入推动服务型制造创新发展。关键词：', url: 'https://fjca.miit.gov.cn/xwdt/bsyw/art/2025/art_b213568d30e5402685b01eae3f8c1c52.html', keywords: [{type:'ding', text:'着力'}] },
    { date: '2025-08-27', source: '工信部', title: '《关于优化业务准入促进卫星通信产业发展的指导意见》(工信部信管〔2025〕180号)', summary: '工信部发布，大力推动手机直连卫星应用，进一步扩大向民营企业开放。关键词：', url: 'https://www.miit.gov.cn/zwgk/zcwj/wjfb/yj/art/2025/art_84617e8497d84a3d8b8b3ef847f648d2.html', keywords: [{type:'ding', text:'大力'}, {type:'deg', text:'进一步'}] }
  ]
};

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

function renderDocItem(item) {
  const dateStr = item.date.slice(5);
  const kwHtml = (item.keywords || []).map(k => `<span class="kw-tag kw-${k.type}">${k.text}</span>`).join('');
  return `
    <div class="doc-item">
      <div class="doc-meta">
        <div class="doc-date">${dateStr}</div>
        <div class="doc-source">${item.source}</div>
      </div>
      <div class="doc-body">
        <div class="doc-title">${item.title}</div>
        <div class="doc-summary">${item.summary}${kwHtml}</div>
        <div class="doc-keywords">
          <a href="${item.url}" target="_blank" class="doc-link">阅读原文</a>
        </div>
      </div>
    </div>
  `;
}

let currentMonthlyPeriod = 'day';

function renderMonthlyDocs(period) {
  const commentaryList = document.getElementById('monthlyDocListCommentary');
  const policyList = document.getElementById('monthlyDocListPolicy');
  if (!commentaryList || !policyList) return;

  const commentaryFiltered = filterByPeriod(monthlyData.commentary, period);
  const policyFiltered = filterByPeriod(monthlyData.policy, period);

  const emptyHtml = '<div style="color:var(--text-muted);font-size:12px;padding:14px">该周期内无文章，请切换其他周期查看</div>';

  commentaryList.innerHTML = commentaryFiltered.length ? commentaryFiltered.map(renderDocItem).join('') : emptyHtml;
  policyList.innerHTML = policyFiltered.length ? policyFiltered.map(renderDocItem).join('') : emptyHtml;
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
// Chart management: render charts only when visible
// ============================================================
const chartRenderers = {
  macro: () => { renderMacroChart(); },
  gov: () => { renderAnnualTimeline(); },
  source: () => {},
  compare: () => {},
  monthly: () => { renderMonthlyDocs(currentMonthlyPeriod); },
  csrc: () => {},
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

// ============================================================
// Auto-update: fetch latest data from data/latest.json
// ============================================================
function loadLatestData() {
  return fetch('data/latest.json')
    .then(function(r) { return r.ok ? r.json() : null; })
    .catch(function() { return null; });
}

function applyLatestData(data) {
  if (!data) return;
  // Prepend new timeline entries (skip duplicates)
  if (data.timeline && data.timeline.length > 0) {
    var existing = new Set();
    timelineData.forEach(function(g) { g.items.forEach(function(i) { existing.add(i.title); }); });
    var fresh = data.timeline.filter(function(item) { return !existing.has(item.title); });
    if (fresh.length > 0) {
      timelineData.unshift({
        month: data.monthLabel || '',
        items: fresh
      });
    }
  }
  // Update header "last updated" text
  if (data.lastUpdated) {
    var el = document.querySelector('.header-right .status-item:nth-child(2)');
    if (el) el.innerHTML = '<span class="status-dot"></span>更新:' + data.lastUpdated;
  }
}

// ============================================================
// Initial render
// ============================================================
renderMacroCards('year');
renderTimeline();          // 旧timeline（若容器存在则渲染）
renderAnnualTimeline();    // 新年度政策时间线（官网与会议tab右侧）
renderMacroChart();
renderMonthlyDocs('day');

// Async: load latest data and re-render timeline if available
loadLatestData().then(function(data) {
  if (data) {
    applyLatestData(data);
    renderTimeline();
    renderAnnualTimeline();
  }
});
