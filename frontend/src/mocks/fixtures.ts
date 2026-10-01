/**
 * SYNTHETIC demo corpus — every company, INN, record and URL below is invented (BR-20).
 * The UI always shows the demo-data notice while this corpus is active. Links point to example.com.
 */
import type { ConfidenceComponent, Evidence, EvidenceType, LegalStatus, RankingFeature, RiskFlag, SupplierType } from "@/lib/api/types";

export type Topic = "panels" | "laptops" | "furniture";

export type MockOffering = { id: string; title: string; category: string; attributes: Record<string, string | number>; source: string; topic: Topic };
export type MockHistory = { id: string; title: string; date: string; role: "winner" | "participant"; amount: number | null; region: string; customer: string; topic: Topic | null };
export type MockEvidence = Evidence & { topic: Topic | null };

export type MockSupplier = {
  id: string;
  legal_name: string;
  inn: string | null;
  ogrn: string | null;
  kpp: string | null;
  legal_status: LegalStatus;
  region: string;
  city: string | null;
  website: string | null;
  okved: { code: string; name: string }[];
  type: SupplierType;
  type_verified: boolean;
  type_basis: { source_name: string; source_url: string | null; observed_at: string } | null;
  known: boolean;
  first_seen: string | null;
  confidence: Record<ConfidenceComponent, number | null>;
  risk_flags: RiskFlag[];
  offerings: MockOffering[];
  history: MockHistory[];
  evidence: MockEvidence[];
  sources: { source_name: string; source_type: string; observed_at: string }[];
  data_quality_flags: string[];
  /** Pre-computed relevance signals per topic (stand-in for the retrieval branches). */
  signals: Partial<Record<Topic, Partial<Record<Exclude<RankingFeature, "experience" | "geography" | "supplier_type">, number>>>>;
};

export const SPB = "Санкт-Петербург";
export const LO = "Ленинградская область";
/** Regions treated as adjacent for GeographicFit = 0.5 (stand-in for the federal-district mapping). */
export const ADJACENT: Record<string, string[]> = { [SPB]: [LO], [LO]: [SPB] };

export const REGIONS = [SPB, LO, "Москва", "Республика Татарстан", "Новосибирская область", "Свердловская область", "Псковская область"];

const URL = "https://example.com/demo";
const ORG = "Данные организатора (демо)";
const GISP = "ГИСП (демо)";
const EGRUL = "ЕГРЮЛ (демо)";

let seq = 0;
const evid = (topic: Topic | null, evidence_type: EvidenceType, claim: string, source_name: string, observed_at: string, confidence: number, path: string | null): MockEvidence => ({
  evidence_id: `ev-${++seq}`,
  topic,
  evidence_type,
  claim,
  source_name,
  source_url: path ? `${URL}/${path}` : null,
  observed_at,
  confidence,
});

const CUSTOMERS = ["ГБОУ СОШ № 112", "ГБОУ Лицей № 64", "ГБОУ Гимназия № 3", "СПб ГБУ «Центр образования»", "ГБДОУ Детский сад № 41", "ГБОУ СОШ № 507"];
const TOPIC_TITLES: Record<Topic, string> = {
  panels: "Поставка интерактивных панелей",
  laptops: "Поставка ноутбуков для учителей",
  furniture: "Поставка ученической мебели",
};

/** Deterministic procurement history: `n` records on `topic` + `other` unrelated ones. */
function hist(sid: string, topic: Topic | null, n: number, region: string, winsEvery = 2, other = 0): MockHistory[] {
  const out: MockHistory[] = [];
  for (let i = 0; i < n + other; i++) {
    const t = i < n ? topic : null;
    const month = String(12 - (i % 12)).padStart(2, "0");
    const year = 2026 - Math.floor(i / 12);
    out.push({
      id: `${sid}-h${i + 1}`,
      title: t ? `${TOPIC_TITLES[t]} (лот ${i + 1})` : `Поставка расходных материалов (лот ${i + 1})`,
      date: `${year}-${month}-${String(5 + ((i * 7) % 20)).padStart(2, "0")}`,
      role: i % winsEvery === 0 ? "winner" : "participant",
      amount: i % 5 === 4 ? null : 350_000 + ((i * 137_000) % 2_400_000),
      region,
      customer: CUSTOMERS[i % CUSTOMERS.length],
      topic: t,
    });
  }
  return out;
}

const OKVED_IT = { code: "46.51", name: "Торговля оптовая компьютерами и периферийными устройствами" };
const OKVED_MFG = { code: "26.40", name: "Производство бытовой электроники" };
const OKVED_PC = { code: "26.20", name: "Производство компьютеров и периферийного оборудования" };
const OKVED_FURN = { code: "31.01", name: "Производство мебели для офисов и предприятий торговли" };
const OKVED_RETAIL = { code: "47.41", name: "Торговля розничная компьютерами в специализированных магазинах" };

const panel = (id: string, size: number, extra: Record<string, string | number> = {}): MockOffering => ({
  id,
  title: `Интерактивная панель ${size} дюймов`,
  category: "Интерактивные панели",
  attributes: { screen_size_inches: size, ...extra },
  source: ORG,
  topic: "panels",
});
const laptop = (id: string, ram: number, screen = 15.6): MockOffering => ({
  id,
  title: `Ноутбук ${screen}" ${ram} ГБ ОЗУ`,
  category: "Ноутбуки",
  attributes: { screen_size_inches: screen, ram_gb: ram },
  source: ORG,
  topic: "laptops",
});
const desk = (id: string, adjustable: boolean): MockOffering => ({
  id,
  title: adjustable ? "Парта ученическая регулируемая по высоте" : "Парта ученическая двухместная",
  category: "Школьная мебель",
  attributes: { adjustable: adjustable ? "да" : "нет" },
  source: ORG,
  topic: "furniture",
});

export const SUPPLIERS: MockSupplier[] = [
  {
    id: "s01",
    legal_name: "ООО «ТехноПанель»",
    inn: "7801000001",
    ogrn: "1027800000011",
    kpp: "780101001",
    legal_status: "active",
    region: SPB,
    city: "Санкт-Петербург",
    website: `${URL}/technopanel`,
    okved: [OKVED_MFG, OKVED_IT],
    type: "manufacturer",
    type_verified: true,
    type_basis: { source_name: GISP, source_url: `${URL}/gisp/7801000001`, observed_at: "2026-09-12" },
    known: true,
    first_seen: "2021-03-15",
    confidence: { product_evidence: 1, legal_identity: 1, recency: 0.9, multi_source: 1, completeness: 1 },
    risk_flags: [],
    offerings: [panel("o01a", 75, { touch_points: 20 }), panel("o01b", 86, { touch_points: 40 }), panel("o01c", 65)],
    history: hist("s01", "panels", 14, SPB, 2, 3),
    evidence: [
      evid("panels", "MANUFACTURER_REGISTRY", "Производитель интерактивных панелей внесён в реестр промышленной продукции", GISP, "2026-09-12", 1, "gisp/7801000001"),
      evid("panels", "PRODUCT_CATALOG", "Каталог: интерактивная панель 75\", 20 касаний, 4K", "Сайт компании (демо)", "2026-08-30", 0.9, "technopanel/catalog/75"),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее, ИНН и ОГРН подтверждены", EGRUL, "2026-09-20", 1, "egrul/7801000001"),
      evid("panels", "PROCUREMENT_HISTORY", "14 контрактов на поставку интерактивных панелей за 2 года", ORG, "2026-09-01", 0.8, null),
      evid("panels", "DELIVERY_REGION", "Доставка и монтаж по Санкт-Петербургу и Ленинградской области", "Сайт компании (демо)", "2026-08-30", 0.7, "technopanel/delivery"),
    ],
    sources: [
      { source_name: ORG, source_type: "organizer", observed_at: "2026-09-01" },
      { source_name: GISP, source_type: "manufacturer_registry", observed_at: "2026-09-12" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: [],
    signals: { panels: { semantic: 0.93, lexical: 0.88, category: 1, attributes: 1, delivery: 1 } },
  },
  {
    id: "s02",
    legal_name: "АО «ЭдуТех Системы»",
    inn: "7702000002",
    ogrn: "1027700000022",
    kpp: "770201001",
    legal_status: "active",
    region: "Москва",
    city: "Москва",
    website: `${URL}/edutech`,
    okved: [OKVED_IT],
    type: "distributor",
    type_verified: true,
    type_basis: { source_name: "Сайт компании (демо)", source_url: `${URL}/edutech/about`, observed_at: "2026-07-10" },
    known: true,
    first_seen: "2019-11-02",
    confidence: { product_evidence: 0.7, legal_identity: 1, recency: 0.7, multi_source: 0.7, completeness: 1 },
    risk_flags: [],
    offerings: [panel("o02a", 75), panel("o02b", 65), laptop("o02c", 16), laptop("o02d", 8, 14)],
    history: [...hist("s02", "panels", 9, "Москва", 3), ...hist("s02x", "laptops", 6, "Москва", 2)],
    evidence: [
      evid("panels", "PRODUCT_CATALOG", "Каталог дистрибьютора: панели 65–86\" нескольких брендов", "Сайт компании (демо)", "2026-07-10", 0.7, "edutech/catalog"),
      evid("laptops", "PRODUCT_CATALOG", "Ноутбуки 14–15.6\" с 8–16 ГБ ОЗУ", "Сайт компании (демо)", "2026-07-10", 0.7, "edutech/laptops"),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/7702000002"),
      evid("panels", "PROCUREMENT_HISTORY", "9 контрактов на интерактивное оборудование", ORG, "2026-09-01", 0.8, null),
    ],
    sources: [
      { source_name: ORG, source_type: "organizer", observed_at: "2026-09-01" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: [],
    signals: { panels: { semantic: 0.86, lexical: 0.8, category: 1, attributes: 1, delivery: 0 }, laptops: { semantic: 0.84, lexical: 0.78, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s03",
    legal_name: "ООО «Интерактив Лаб»",
    inn: "7814000003",
    ogrn: "1167800000033",
    kpp: "781401001",
    legal_status: "active",
    region: SPB,
    city: "Санкт-Петербург",
    website: `${URL}/interactivelab`,
    okved: [OKVED_MFG],
    type: "manufacturer",
    type_verified: true,
    type_basis: { source_name: GISP, source_url: `${URL}/gisp/7814000003`, observed_at: "2026-09-05" },
    known: false,
    first_seen: null,
    confidence: { product_evidence: 1, legal_identity: 1, recency: 1, multi_source: 0.7, completeness: 0.83 },
    risk_flags: ["NO_PROCUREMENT_HISTORY"],
    offerings: [panel("o03a", 75, { touch_points: 40 }), panel("o03b", 98)],
    history: [],
    evidence: [
      evid("panels", "MANUFACTURER_REGISTRY", "Продукция внесена в реестр российской промышленной продукции", GISP, "2026-09-05", 1, "gisp/7814000003"),
      evid("panels", "PRODUCT_CATALOG", "Интерактивная панель 75\", 40 касаний, ОС Android", "Сайт компании (демо)", "2026-09-18", 0.8, "interactivelab/75"),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/7814000003"),
    ],
    sources: [
      { source_name: GISP, source_type: "manufacturer_registry", observed_at: "2026-09-05" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: [],
    signals: { panels: { semantic: 0.91, lexical: 0.84, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s04",
    legal_name: "ООО «СевЗапОборудование»",
    inn: "4703000004",
    ogrn: "1094700000044",
    kpp: "470301001",
    legal_status: "active",
    region: LO,
    city: "Всеволожск",
    website: null,
    okved: [OKVED_IT, OKVED_RETAIL],
    type: "supplier",
    type_verified: false,
    type_basis: null,
    known: true,
    first_seen: "2022-06-20",
    confidence: { product_evidence: 0.6, legal_identity: 1, recency: 0.6, multi_source: 0.7, completeness: 0.67 },
    risk_flags: [],
    offerings: [panel("o04a", 75), laptop("o04b", 16)],
    history: [...hist("s04", "panels", 5, LO, 2, 2), ...hist("s04x", "laptops", 3, LO, 3)],
    evidence: [
      evid("panels", "PROCUREMENT_HISTORY", "5 контрактов на интерактивные панели", ORG, "2026-09-01", 0.6, null),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/4703000004"),
    ],
    sources: [
      { source_name: ORG, source_type: "organizer", observed_at: "2026-09-01" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: ["MISSING_WEBSITE"],
    signals: { panels: { semantic: 0.78, lexical: 0.74, category: 1, attributes: 1, delivery: 1 }, laptops: { semantic: 0.7, lexical: 0.66, category: 1, attributes: 0.5, delivery: 1 } },
  },
  {
    id: "s05",
    legal_name: "ООО «Визуал Про»",
    inn: "1655000005",
    ogrn: "1181600000055",
    kpp: "165501001",
    legal_status: "active",
    region: "Республика Татарстан",
    city: "Казань",
    website: `${URL}/visualpro`,
    okved: [OKVED_MFG],
    type: "manufacturer",
    type_verified: false,
    type_basis: null,
    known: false,
    first_seen: null,
    confidence: { product_evidence: 0.7, legal_identity: 0.6, recency: 0.8, multi_source: 0.3, completeness: 0.83 },
    risk_flags: ["UNVERIFIED_MANUFACTURER", "NO_PROCUREMENT_HISTORY"],
    offerings: [panel("o05a", 75), panel("o05b", 86)],
    history: [],
    evidence: [evid("panels", "COMPANY_WEBSITE", "На сайте заявлено собственное производство панелей", "Сайт компании (демо)", "2026-08-14", 0.5, "visualpro/about")],
    sources: [{ source_name: "Открытые источники (демо)", source_type: "open_web", observed_at: "2026-08-14" }],
    data_quality_flags: [],
    signals: { panels: { semantic: 0.88, lexical: 0.8, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s06",
    legal_name: "ИП Карпов Алексей Викторович",
    inn: "781200000006",
    ogrn: "320780000000066",
    kpp: null,
    legal_status: "active",
    region: SPB,
    city: "Санкт-Петербург",
    website: null,
    okved: [OKVED_RETAIL],
    type: "supplier",
    type_verified: false,
    type_basis: null,
    known: false,
    first_seen: null,
    confidence: { product_evidence: 0.3, legal_identity: 0.6, recency: 0.5, multi_source: 0.3, completeness: 0.5 },
    risk_flags: ["LOW_EVIDENCE", "NO_PROCUREMENT_HISTORY"],
    offerings: [panel("o06a", 65)],
    history: [],
    evidence: [evid("panels", "OPEN_WEB_MENTION", "Объявление о продаже интерактивных панелей", "Открытые источники (демо)", "2026-05-02", 0.3, "board/karpov")],
    sources: [{ source_name: "Открытые источники (демо)", source_type: "open_web", observed_at: "2026-05-02" }],
    data_quality_flags: ["MISSING_WEBSITE", "MISSING_KPP"],
    signals: { panels: { semantic: 0.72, lexical: 0.7, category: 1, attributes: 0, delivery: 0 } },
  },
  {
    id: "s07",
    legal_name: "ООО «Школьные Технологии»",
    inn: "5406000007",
    ogrn: "1125400000077",
    kpp: "540601001",
    legal_status: "active",
    region: "Новосибирская область",
    city: "Новосибирск",
    website: `${URL}/schooltech`,
    okved: [OKVED_IT],
    type: "distributor",
    type_verified: true,
    type_basis: { source_name: "Сайт компании (демо)", source_url: `${URL}/schooltech/dealers`, observed_at: "2026-06-01" },
    known: true,
    first_seen: "2020-02-11",
    confidence: { product_evidence: 0.7, legal_identity: 1, recency: 0.5, multi_source: 0.7, completeness: 1 },
    risk_flags: [],
    offerings: [panel("o07a", 75), panel("o07b", 55)],
    history: hist("s07", "panels", 7, "Новосибирская область", 2),
    evidence: [
      evid("panels", "PRODUCT_CATALOG", "Дилерский каталог интерактивного оборудования", "Сайт компании (демо)", "2026-06-01", 0.7, "schooltech/catalog"),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/5406000007"),
    ],
    sources: [
      { source_name: ORG, source_type: "organizer", observed_at: "2026-09-01" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: [],
    signals: { panels: { semantic: 0.83, lexical: 0.79, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s08",
    legal_name: "ООО «Нева Компьютерс»",
    inn: "7810000008",
    ogrn: "1077800000088",
    kpp: "781001001",
    legal_status: "active",
    region: SPB,
    city: "Санкт-Петербург",
    website: `${URL}/nevacomp`,
    okved: [OKVED_IT, OKVED_RETAIL],
    type: "distributor",
    type_verified: true,
    type_basis: { source_name: "Сайт компании (демо)", source_url: `${URL}/nevacomp/partners`, observed_at: "2026-09-02" },
    known: true,
    first_seen: "2018-09-01",
    confidence: { product_evidence: 0.7, legal_identity: 1, recency: 1, multi_source: 1, completeness: 1 },
    risk_flags: [],
    offerings: [laptop("o08a", 16), laptop("o08b", 32), laptop("o08c", 8, 14)],
    history: hist("s08", "laptops", 11, SPB, 2, 4),
    evidence: [
      evid("laptops", "PRODUCT_CATALOG", "Ноутбуки 15.6\" 16 ГБ ОЗУ, наличие на складе в СПб", "Сайт компании (демо)", "2026-09-02", 0.7, "nevacomp/laptops"),
      evid("laptops", "PROCUREMENT_HISTORY", "11 контрактов на поставку ноутбуков", ORG, "2026-09-01", 0.8, null),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/7810000008"),
      evid("laptops", "DELIVERY_REGION", "Доставка по Санкт-Петербургу собственным транспортом", "Сайт компании (демо)", "2026-09-02", 0.7, "nevacomp/delivery"),
    ],
    sources: [
      { source_name: ORG, source_type: "organizer", observed_at: "2026-09-01" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
      { source_name: "Сайт компании (демо)", source_type: "company_website", observed_at: "2026-09-02" },
    ],
    data_quality_flags: [],
    signals: { laptops: { semantic: 0.92, lexical: 0.9, category: 1, attributes: 1, delivery: 1 } },
  },
  {
    id: "s09",
    legal_name: "АО «РусБук Производство»",
    inn: "7703000009",
    ogrn: "1157700000099",
    kpp: "770301001",
    legal_status: "active",
    region: "Москва",
    city: "Зеленоград",
    website: `${URL}/rusbook`,
    okved: [OKVED_PC],
    type: "manufacturer",
    type_verified: true,
    type_basis: { source_name: GISP, source_url: `${URL}/gisp/7703000009`, observed_at: "2026-08-21" },
    known: false,
    first_seen: null,
    confidence: { product_evidence: 1, legal_identity: 1, recency: 0.9, multi_source: 1, completeness: 1 },
    risk_flags: [],
    offerings: [laptop("o09a", 16), laptop("o09b", 16, 14)],
    history: hist("s09", "laptops", 2, "Москва", 1),
    evidence: [
      evid("laptops", "MANUFACTURER_REGISTRY", "Ноутбуки внесены в реестр российской промышленной продукции", GISP, "2026-08-21", 1, "gisp/7703000009"),
      evid("laptops", "PRODUCT_CATALOG", "Ноутбук 15.6\", 16 ГБ, российская сборка", "Сайт компании (демо)", "2026-09-10", 0.8, "rusbook/catalog"),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/7703000009"),
    ],
    sources: [
      { source_name: GISP, source_type: "manufacturer_registry", observed_at: "2026-08-21" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: [],
    signals: { laptops: { semantic: 0.9, lexical: 0.82, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s10",
    legal_name: "ООО «ДатаЛайн»",
    inn: "6670000010",
    ogrn: "1146600000100",
    kpp: "667001001",
    legal_status: "active",
    region: "Свердловская область",
    city: "Екатеринбург",
    website: `${URL}/dataline`,
    okved: [OKVED_RETAIL],
    type: "supplier",
    type_verified: false,
    type_basis: null,
    known: false,
    first_seen: null,
    confidence: { product_evidence: 0.7, legal_identity: 0.6, recency: 0.1, multi_source: 0.3, completeness: 0.83 },
    risk_flags: ["STALE_INFORMATION", "NO_PROCUREMENT_HISTORY"],
    offerings: [laptop("o10a", 16)],
    history: [],
    evidence: [evid("laptops", "PRODUCT_CATALOG", "Прайс-лист с ноутбуками 15.6\" 16 ГБ", "Сайт компании (демо)", "2024-11-03", 0.6, "dataline/price")],
    sources: [{ source_name: "Сайт компании (демо)", source_type: "company_website", observed_at: "2024-11-03" }],
    data_quality_flags: [],
    signals: { laptops: { semantic: 0.82, lexical: 0.77, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s11",
    legal_name: "ООО «Мебель для школ»",
    inn: "6027000011",
    ogrn: "1196000000111",
    kpp: "602701001",
    legal_status: "active",
    region: "Псковская область",
    city: "Псков",
    website: `${URL}/schoolfurniture`,
    okved: [OKVED_FURN],
    type: "manufacturer",
    type_verified: false,
    type_basis: null,
    known: false,
    first_seen: null,
    confidence: { product_evidence: 0.3, legal_identity: 0.3, recency: 0.3, multi_source: 0.3, completeness: 0.67 },
    risk_flags: ["UNVERIFIED_MANUFACTURER", "LOW_EVIDENCE", "NO_PROCUREMENT_HISTORY"],
    offerings: [desk("o11a", true), desk("o11b", false)],
    history: [],
    evidence: [evid("furniture", "OPEN_WEB_MENTION", "Упоминание в каталоге производителей мебели", "Открытые источники (демо)", "2025-12-12", 0.3, "dir/furniture")],
    sources: [{ source_name: "Открытые источники (демо)", source_type: "open_web", observed_at: "2025-12-12" }],
    data_quality_flags: [],
    signals: { furniture: { semantic: 0.86, lexical: 0.8, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s12",
    legal_name: "ООО «ПартаСтрой»",
    inn: "4704000012",
    ogrn: "1104700000122",
    kpp: "470401001",
    legal_status: "active",
    region: LO,
    city: "Гатчина",
    website: null,
    okved: [OKVED_FURN],
    type: "manufacturer",
    type_verified: false,
    type_basis: null,
    known: true,
    first_seen: "2017-04-09",
    confidence: { product_evidence: 0.3, legal_identity: 0.6, recency: 0.1, multi_source: 0.3, completeness: 0.5 },
    risk_flags: ["UNVERIFIED_MANUFACTURER", "STALE_INFORMATION", "LOW_EVIDENCE"],
    offerings: [desk("o12a", true)],
    history: hist("s12", "furniture", 3, LO, 2),
    evidence: [
      evid("furniture", "PROCUREMENT_HISTORY", "3 контракта на ученическую мебель (2023–2024)", ORG, "2024-08-15", 0.6, null),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/4704000012"),
    ],
    sources: [
      { source_name: ORG, source_type: "organizer", observed_at: "2024-08-15" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: ["MISSING_WEBSITE"],
    signals: { furniture: { semantic: 0.8, lexical: 0.83, category: 1, attributes: 1, delivery: 0 } },
  },
  {
    id: "s13",
    legal_name: "ООО «Учебный Мир»",
    inn: null,
    ogrn: null,
    kpp: null,
    legal_status: "unknown",
    region: SPB,
    city: null,
    website: `${URL}/uchmir`,
    okved: [],
    type: "unknown",
    type_verified: false,
    type_basis: null,
    known: false,
    first_seen: null,
    confidence: { product_evidence: 0.3, legal_identity: 0, recency: 0.6, multi_source: 0.3, completeness: 0.33 },
    risk_flags: ["UNKNOWN_LEGAL_STATUS", "AMBIGUOUS_ENTITY", "LOW_EVIDENCE", "NO_PROCUREMENT_HISTORY"],
    offerings: [desk("o13a", false)],
    history: [],
    evidence: [evid("furniture", "OPEN_WEB_MENTION", "Интернет-магазин школьной мебели", "Открытые источники (демо)", "2026-04-20", 0.3, "uchmir")],
    sources: [{ source_name: "Открытые источники (демо)", source_type: "open_web", observed_at: "2026-04-20" }],
    data_quality_flags: ["MISSING_INN", "POSSIBLE_MATCH_OPEN"],
    signals: { furniture: { semantic: 0.74, lexical: 0.71, category: 1, attributes: 0, delivery: 0 } },
  },
  {
    id: "s14",
    legal_name: "ООО «Смарт Дисплей»",
    inn: "7816000014",
    ogrn: "1207800000144",
    kpp: "781601001",
    legal_status: "active",
    region: SPB,
    city: "Санкт-Петербург",
    website: `${URL}/smartdisplay`,
    okved: [OKVED_IT],
    type: "distributor",
    type_verified: false,
    type_basis: null,
    known: false,
    first_seen: null,
    confidence: { product_evidence: 0.7, legal_identity: 1, recency: 0.9, multi_source: 0.3, completeness: 0.83 },
    risk_flags: ["AMBIGUOUS_ENTITY", "NO_PROCUREMENT_HISTORY"],
    offerings: [panel("o14a", 75), panel("o14b", 86)],
    history: [],
    evidence: [
      evid("panels", "PRODUCT_CATALOG", "Интерактивные панели 75–86\" в наличии", "Сайт компании (демо)", "2026-09-15", 0.7, "smartdisplay/catalog"),
      evid(null, "LEGAL_REGISTRY", "Юридическое лицо действующее", EGRUL, "2026-09-20", 1, "egrul/7816000014"),
    ],
    sources: [
      { source_name: "Сайт компании (демо)", source_type: "company_website", observed_at: "2026-09-15" },
      { source_name: EGRUL, source_type: "legal_registry", observed_at: "2026-09-20" },
    ],
    data_quality_flags: ["POSSIBLE_MATCH_OPEN"],
    signals: { panels: { semantic: 0.85, lexical: 0.83, category: 1, attributes: 1, delivery: 1 } },
  },
];

/** Merged supplier IDs (EC-22): old → surviving. */
export const REDIRECTS: Record<string, string> = { "s01-old": "s01" };

/** Frozen demo queries shown on S-01 (P8-004 will replace them with the frozen set). */
export const DEMO_QUERIES = [
  { key: "panels", query: "Интерактивная панель 75 дюймов для школы в Санкт-Петербурге" },
  { key: "laptops", query: "Ноутбук 15.6 дюйма 16 ГБ для учителей, 40 шт" },
  { key: "manufacturers", query: "Интерактивные панели только от производителя" },
  { key: "furniture", query: "Парты ученические регулируемые по высоте" },
  { key: "empty", query: "Ледокол атомный проекта 22220" },
] as const;
