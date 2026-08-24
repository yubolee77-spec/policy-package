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

function renderTimeline() {
  const list = document.getElementById('timelineList');
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

// ============================================================
// LAYER 4: Monthly documents data & rendering
// ============================================================
const monthlyData = {
  commentary: [
    { date: '2026-08-21', source: '经济日报', title: '金观平：治理账款拖欠重在常态化', summary: '中央政治局会议提出常态化解决企业账款拖欠问题。关键词：', url: 'http://adimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260821_3159304.shtml', keywords: [{type:'deg', text:'持续'}] },
    { date: '2026-08-02', source: '经济日报', title: '金观平：深化资本市场投融资综合改革', summary: '中央政治局会议提出深化资本市场投融资综合改革，提升韧性和信心。关键词：', url: 'http://bgimg.ce.cn/xwzx/gnsz/gdxw/202608/t20260802_3122358.shtml', keywords: [{type:'deg', text:'进一步'}] },
    { date: '2026-05-22', source: '求是网', title: '求是网评论员：如何提升产业链供应链韧性和安全水平', summary: '补链、强链、建链——统筹推进产业链供应链安全。', url: 'http://www.qstheory.cn/20260522/13b85573bc924de2946ad7cacc741004/c.html', keywords: [] },
    { date: '2026-03-15', source: '求是网', title: '求是杂志评论员：凝心聚力奋进中国式现代化', summary: '解读全国两会精神，部署"十五五"规划纲要落地落实。', url: 'http://www.qstheory.cn/20260314/70a1bcaa409e4cb3bfb7c6f72c73694c/c.html', keywords: [] },
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

// Reference date for period filtering (统计截止日期: 2026-08-21)
const MONTHLY_REF_DATE = new Date('2026-08-21T00:00:00');

function filterByPeriod(articles, period) {
  const now = MONTHLY_REF_DATE;
  return articles.filter(a => {
    const d = new Date(a.date + 'T00:00:00');
    if (period === 'year') return d.getFullYear() === now.getFullYear();
    const diffMs = now - d;
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    if (period === 'day') return diffDays <= 3 && diffDays >= 0;
    if (period === 'week') return diffDays <= 7 && diffDays >= 0;
    if (period === 'month') return diffDays <= 30 && diffDays >= 0;
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
  gov: () => {},
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
renderTimeline();
renderMacroChart();
renderMonthlyDocs('day');

// Async: load latest data and re-render timeline if available
loadLatestData().then(function(data) {
  if (data) {
    applyLatestData(data);
    renderTimeline();
  }
});
