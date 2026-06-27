import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const outputDir = path.join(root, "outputs", "home-deal-insight-agent");
const previewDir = path.join(outputDir, "previews");
await fs.mkdir(previewDir, { recursive: true });

function mulberry32(seed) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const random = mulberry32(20260627);
const pick = (items) => items[Math.floor(random() * items.length)];
const round100 = (value) => Math.round(value / 100) * 100;
const pad = (value) => String(value).padStart(2, "0");

const cityConfig = {
  上海: { factor: 1.18, stores: ["徐汇旗舰店", "浦东体验店"] },
  杭州: { factor: 1.08, stores: ["滨江店", "城西店"] },
  苏州: { factor: 1.02, stores: ["园区店", "姑苏店"] },
  南京: { factor: 1.0, stores: ["河西店", "新街口店"] },
  宁波: { factor: 0.96, stores: ["鄞州店", "海曙店"] },
};

const styles = [
  { name: "现代简约", factor: 1.0, weight: 22 },
  { name: "奶油风", factor: 1.06, weight: 17 },
  { name: "新中式", factor: 1.22, weight: 13 },
  { name: "原木风", factor: 1.04, weight: 15 },
  { name: "轻奢", factor: 1.25, weight: 12 },
  { name: "北欧", factor: 0.98, weight: 10 },
  { name: "法式", factor: 1.3, weight: 7 },
  { name: "工业风", factor: 1.08, weight: 4 },
];

function weightedPick(items) {
  const total = items.reduce((sum, item) => sum + item.weight, 0);
  let cursor = random() * total;
  for (const item of items) {
    cursor -= item.weight;
    if (cursor <= 0) return item;
  }
  return items.at(-1);
}

const managers = ["陈思远", "周雨桐", "林浩", "许佳宁", "王嘉禾", "赵子墨", "沈安然", "唐一帆"];
const designers = ["顾清", "陆遥", "宋知夏", "叶川", "江晚", "程野", "苏禾", "白露", "温言", "景行"];
const channels = [
  { name: "老客转介绍", weight: 24 },
  { name: "小红书", weight: 20 },
  { name: "抖音", weight: 17 },
  { name: "自然到店", weight: 14 },
  { name: "大众点评", weight: 10 },
  { name: "合作楼盘", weight: 9 },
  { name: "搜索广告", weight: 6 },
];
const houseTypes = [
  { name: "两居室", area: [70, 95], weight: 25 },
  { name: "三居室", area: [95, 135], weight: 38 },
  { name: "四居室", area: [130, 180], weight: 21 },
  { name: "复式", area: [150, 230], weight: 9 },
  { name: "别墅", area: [220, 380], weight: 7 },
];

const headers = [
  "项目编号",
  "签约日期",
  "城市",
  "门店",
  "客户经理",
  "设计师",
  "房屋类型",
  "面积㎡",
  "设计风格",
  "获客渠道",
  "签约额",
  "设计费",
  "预计成本",
  "毛利额",
  "合同状态",
  "交付状态",
  "出图日期",
  "出图时长(天)",
  "客户评分",
  "是否按时出图",
];

const rows = [];
let serial = 1;
for (let year = 2024; year <= 2025; year += 1) {
  for (let month = 1; month <= 12; month += 1) {
    const seasonFactor = [1.02, 0.88, 0.97, 1.06, 1.12, 1.08, 0.94, 0.96, 1.1, 1.2, 1.16, 1.04][month - 1];
    for (let i = 0; i < 30; i += 1) {
      const city = pick(Object.keys(cityConfig));
      const cityItem = cityConfig[city];
      const style = weightedPick(styles);
      const house = weightedPick(houseTypes);
      const channel = weightedPick(channels).name;
      const area = Math.round(house.area[0] + random() * (house.area[1] - house.area[0]));
      const day = 1 + Math.floor(random() * 27);
      const signedAt = new Date(year, month - 1, day);
      const basePerSqm = 1450 + random() * 1450;
      const growth = year === 2025 ? 1.055 : 1;
      const amount = round100(area * basePerSqm * cityItem.factor * style.factor * seasonFactor * growth);
      const designFee = round100(amount * (0.035 + random() * 0.035));
      const costRatio = 0.59 + random() * 0.17;
      const estimatedCost = round100(amount * costRatio);

      const cancelProbability = channel === "搜索广告" ? 0.1 : 0.045;
      const isCancelled = random() < cancelProbability;
      let contractStatus = "已完工";
      let deliveryStatus = "已交付";
      if (isCancelled) {
        contractStatus = "已取消";
        deliveryStatus = "已终止";
      } else if (year === 2025 && month >= 9 && random() < 0.58) {
        contractStatus = "履约中";
        deliveryStatus = pick(["设计中", "施工中", "待交付"]);
      }

      let drawingDate = null;
      let drawingDays = null;
      if (!isCancelled && !(deliveryStatus === "设计中" && random() < 0.2)) {
        drawingDays = 6 + Math.floor(random() * 17);
        drawingDate = new Date(year, month - 1, day + drawingDays);
      }
      const rating =
        isCancelled || deliveryStatus === "设计中"
          ? null
          : Math.round((4.0 + random() * 1.0) * 10) / 10;

      rows.push([
        `HD-${year}${pad(month)}-${pad(serial)}`,
        signedAt,
        city,
        pick(cityItem.stores),
        pick(managers),
        pick(designers),
        house.name,
        area,
        style.name,
        channel,
        amount,
        designFee,
        estimatedCost,
        null,
        contractStatus,
        deliveryStatus,
        drawingDate,
        null,
        rating,
        drawingDays === null ? null : drawingDays <= 14 ? "是" : "否",
      ]);
      serial += 1;
    }
  }
}

const workbook = Workbook.create();
const detail = workbook.worksheets.add("签约明细");
const overview = workbook.worksheets.add("经营概览");
const dictionary = workbook.worksheets.add("字段说明");

detail.showGridLines = false;
detail.getRange(`A1:T${rows.length + 1}`).values = [headers, ...rows];
detail.getRange("N2").formulas = [["=K2-M2"]];
detail.getRange(`N2:N${rows.length + 1}`).fillDown();
detail.getRange("R2").formulas = [["=IF(Q2=\"\",\"\",Q2-B2)"]];
detail.getRange(`R2:R${rows.length + 1}`).fillDown();

detail.getRange("A1:T1").format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  rowHeight: 30,
};
detail.getRange(`A2:T${rows.length + 1}`).format = {
  font: { color: "#22312B", size: 10 },
  verticalAlignment: "center",
};
detail.getRange(`B2:B${rows.length + 1}`).format.numberFormat = "yyyy-mm-dd";
detail.getRange(`Q2:Q${rows.length + 1}`).format.numberFormat = "yyyy-mm-dd";
detail.getRange(`H2:H${rows.length + 1}`).format.numberFormat = "0";
detail.getRange(`K2:N${rows.length + 1}`).format.numberFormat = '"¥"#,##0';
detail.getRange(`R2:R${rows.length + 1}`).format.numberFormat = "0";
detail.getRange(`S2:S${rows.length + 1}`).format.numberFormat = "0.0";

const widths = {
  A: 17, B: 12, C: 9, D: 14, E: 11, F: 10, G: 11, H: 9, I: 12, J: 14,
  K: 14, L: 12, M: 14, N: 13, O: 11, P: 11, Q: 12, R: 14, S: 11, T: 14,
};
for (const [column, width] of Object.entries(widths)) {
  detail.getRange(`${column}:${column}`).format.columnWidth = width;
}
detail.freezePanes.freezeRows(1);
detail.freezePanes.freezeColumns(2);
const dataTable = detail.tables.add(`A1:T${rows.length + 1}`, true, "HomeDealTable");
dataTable.style = "TableStyleMedium2";
dataTable.showBandedRows = true;
dataTable.showFilterButton = true;
detail.getRange(`O2:O${rows.length + 1}`).dataValidation = {
  rule: { type: "list", values: ["已完工", "履约中", "已取消"] },
};
detail.getRange(`T2:T${rows.length + 1}`).dataValidation = {
  rule: { type: "list", values: ["是", "否"] },
};
detail.getRange(`K2:K${rows.length + 1}`).conditionalFormats.add("dataBar", {
  color: "#14B8A6",
  gradient: true,
});

overview.showGridLines = false;
overview.getRange("A1:H2").merge();
overview.getRange("A1").values = [["家装业务经营概览"]];
overview.getRange("A1:H2").format = {
  fill: "#0B4F48",
  font: { bold: true, color: "#FFFFFF", size: 22 },
  horizontalAlignment: "left",
  verticalAlignment: "center",
};
overview.getRange("A3:H3").merge();
overview.getRange("A3").values = [["数据范围：2024-01 至 2025-12｜口径：排除“已取消”合同｜可直接用于产品演示与准确率评测"]];
overview.getRange("A3:H3").format = {
  fill: "#DDF3EC",
  font: { color: "#24564B", italic: true },
  verticalAlignment: "center",
};

overview.getRange("A5:B5").values = [["核心指标", "结果"]];
overview.getRange("A6:A10").values = [
  ["有效签约单数"],
  ["有效签约额"],
  ["平均客单价"],
  ["平均毛利率"],
  ["按时出图率"],
];
overview.getRange("B6").formulas = [[`=COUNTIF('签约明细'!$O$2:$O$${rows.length + 1},"<>已取消")`]];
overview.getRange("B7").formulas = [[`=SUMIFS('签约明细'!$K$2:$K$${rows.length + 1},'签约明细'!$O$2:$O$${rows.length + 1},"<>已取消")`]];
overview.getRange("B8").formulas = [["=B7/B6"]];
overview.getRange("B9").formulas = [[`=SUMIFS('签约明细'!$N$2:$N$${rows.length + 1},'签约明细'!$O$2:$O$${rows.length + 1},"<>已取消")/B7`]];
overview.getRange("B10").formulas = [[`=COUNTIFS('签约明细'!$T$2:$T$${rows.length + 1},"是",'签约明细'!$O$2:$O$${rows.length + 1},"<>已取消")/COUNTIFS('签约明细'!$T$2:$T$${rows.length + 1},"<>",'签约明细'!$O$2:$O$${rows.length + 1},"<>已取消")`]];
overview.getRange("A5:B5").format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
};
overview.getRange("A6:B10").format = {
  fill: "#FFFFFF",
  font: { color: "#22312B" },
  borders: { preset: "inside", style: "thin", color: "#D9E4DF" },
};
overview.getRange("B6").format.numberFormat = "#,##0";
overview.getRange("B7:B8").format.numberFormat = '"¥"#,##0';
overview.getRange("B9:B10").format.numberFormat = "0.0%";

overview.getRange("A12:B12").values = [["月份", "有效签约额"]];
const monthRows = [];
for (let year = 2024; year <= 2025; year += 1) {
  for (let month = 1; month <= 12; month += 1) {
    monthRows.push([`${year}-${pad(month)}`, null]);
  }
}
overview.getRange("A13:B36").values = monthRows;
for (let index = 0; index < monthRows.length; index += 1) {
  const row = 13 + index;
  const year = index < 12 ? 2024 : 2025;
  const month = (index % 12) + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const nextMonth = month === 12 ? 1 : month + 1;
  overview.getRange(`B${row}`).formulas = [[
    `=SUMIFS('签约明细'!$K$2:$K$${rows.length + 1},'签约明细'!$B$2:$B$${rows.length + 1},">="&DATE(${year},${month},1),'签约明细'!$B$2:$B$${rows.length + 1},"<"&DATE(${nextYear},${nextMonth},1),'签约明细'!$O$2:$O$${rows.length + 1},"<>已取消")`,
  ]];
}
overview.getRange("A12:B12").format = {
  fill: "#DAEDE7",
  font: { bold: true, color: "#0B4F48" },
};
overview.getRange("B13:B36").format.numberFormat = '"¥"#,##0';
overview.getRange("A12:B36").format.borders = {
  insideHorizontal: { style: "thin", color: "#E4ECE8" },
  bottom: { style: "thin", color: "#B9CDC5" },
};
overview.getRange("A:A").format.columnWidth = 20;
overview.getRange("B:B").format.columnWidth = 18;
overview.getRange("C:C").format.columnWidth = 3;
overview.getRange("D:H").format.columnWidth = 14;
overview.freezePanes.freezeRows(3);

const trendChart = overview.charts.add("line", overview.getRange("A12:B36"));
trendChart.title = "每月有效签约额趋势";
trendChart.hasLegend = false;
trendChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 }, tickLabelInterval: 3 };
trendChart.yAxis = { numberFormatCode: '"¥"#,##0', textStyle: { fontSize: 9 } };
trendChart.setPosition("D5", "L20");

const fields = [
  ["字段", "含义", "类型", "示例", "分析口径"],
  ["项目编号", "每个家装项目的唯一编号", "文本", "HD-202501-0361", "不可重复"],
  ["签约日期", "合同正式签署日期", "日期", "2025-01-08", "用于年/月/季度筛选"],
  ["城市", "项目所在城市", "分类", "上海", "可按城市分组"],
  ["门店", "负责项目的经营门店", "分类", "徐汇旗舰店", "可按门店分组"],
  ["客户经理", "负责签单的销售顾问", "分类", "陈思远", "可按人员排名"],
  ["设计师", "负责方案设计的设计师", "分类", "顾清", "可按人员排名"],
  ["房屋类型", "住宅户型类别", "分类", "三居室", "可按户型分组"],
  ["面积㎡", "房屋建筑面积", "数值", "118", "单位：平方米"],
  ["设计风格", "客户选择的主设计风格", "分类", "现代简约", "可按风格分组"],
  ["获客渠道", "客户首次有效来源", "分类", "小红书", "可衡量渠道产出"],
  ["签约额", "合同约定的装修总金额", "金额", "286,000", "默认只统计有效合同"],
  ["设计费", "合同内设计服务费用", "金额", "15,800", "可求和或平均"],
  ["预计成本", "项目预计发生的直接成本", "金额", "182,000", "用于计算毛利"],
  ["毛利额", "签约额减预计成本", "公式", "'=签约额-预计成本", "逐行公式计算"],
  ["合同状态", "合同当前是否有效", "分类", "已完工", "默认排除已取消"],
  ["交付状态", "项目当前履约阶段", "分类", "施工中", "用于进度分析"],
  ["出图日期", "整套方案首次完成日期", "日期", "2025-01-20", "取消或未出图可为空"],
  ["出图时长(天)", "签约到首次出图的自然日", "公式", "'=出图日期-签约日期", "逐行公式计算"],
  ["客户评分", "交付阶段客户满意度", "数值", "4.7", "1~5 分"],
  ["是否按时出图", "出图时长是否不超过14天", "分类", "是", "按时率=是/有效已出图"],
];
dictionary.showGridLines = false;
dictionary.getRange(`A1:E${fields.length}`).values = fields;
dictionary.getRange("A1:E1").format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
  rowHeight: 30,
};
dictionary.getRange(`A2:E${fields.length}`).format = {
  font: { color: "#22312B" },
  verticalAlignment: "top",
  wrapText: true,
};
dictionary.getRange(`A1:E${fields.length}`).format.borders = {
  insideHorizontal: { style: "thin", color: "#E4ECE8" },
};
dictionary.getRange("A:A").format.columnWidth = 18;
dictionary.getRange("B:B").format.columnWidth = 34;
dictionary.getRange("C:C").format.columnWidth = 12;
dictionary.getRange("D:D").format.columnWidth = 22;
dictionary.getRange("E:E").format.columnWidth = 32;
dictionary.freezePanes.freezeRows(1);

const keyInspect = await workbook.inspect({
  kind: "table",
  range: "经营概览!A1:H20",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
  maxChars: 5000,
});
console.log(keyInspect.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

for (const [sheetName, range] of [
  ["经营概览", "A1:L36"],
  ["签约明细", "A1:T22"],
  ["字段说明", `A1:E${fields.length}`],
]) {
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, `${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = path.join(outputDir, "家装业务演示数据.xlsx");
await output.save(outputPath);
console.log(`Created ${outputPath} with ${rows.length} rows.`);
process.exitCode = 0;
