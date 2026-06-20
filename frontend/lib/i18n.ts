// Minimal bilingual (EN/AR) dictionary. One implementation used everywhere; the
// active language also drives text direction (RTL for Arabic).
import type { Language } from "./types";

type Dict = Record<string, { en: string; ar: string }>;

const STRINGS: Dict = {
  appName: { en: "Contract Intelligence", ar: "ذكاء العقود" },
  login: { en: "Log in", ar: "تسجيل الدخول" },
  register: { en: "Create account", ar: "إنشاء حساب" },
  logout: { en: "Log out", ar: "تسجيل الخروج" },
  username: { en: "Username", ar: "اسم المستخدم" },
  email: { en: "Email", ar: "البريد الإلكتروني" },
  password: { en: "Password", ar: "كلمة المرور" },
  fullName: { en: "Full name", ar: "الاسم الكامل" },
  forgotPassword: { en: "Forgot password?", ar: "نسيت كلمة المرور؟" },
  resetPassword: { en: "Reset password", ar: "إعادة تعيين كلمة المرور" },
  newPassword: { en: "New password", ar: "كلمة مرور جديدة" },
  noAccount: { en: "No account yet?", ar: "ليس لديك حساب؟" },
  haveAccount: { en: "Already have an account?", ar: "لديك حساب بالفعل؟" },
  contracts: { en: "Contracts", ar: "العقود" },
  clients: { en: "Clients", ar: "العملاء" },
  search: { en: "Search", ar: "بحث" },
  upload: { en: "Upload", ar: "رفع" },
  newContract: { en: "New contract", ar: "عقد جديد" },
  pasteText: { en: "Paste text", ar: "لصق النص" },
  title: { en: "Title", ar: "العنوان" },
  type: { en: "Type", ar: "النوع" },
  region: { en: "Region", ar: "المنطقة" },
  language: { en: "Language", ar: "اللغة" },
  content: { en: "Content", ar: "المحتوى" },
  create: { en: "Create", ar: "إنشاء" },
  cancel: { en: "Cancel", ar: "إلغاء" },
  analyze: { en: "Analyze", ar: "تحليل" },
  reAnalyze: { en: "Re-analyze", ar: "إعادة التحليل" },
  analyzing: { en: "Analyzing…", ar: "جاري التحليل…" },
  healthScore: { en: "Health score", ar: "درجة الصحة" },
  findings: { en: "Clause findings", ar: "نتائج البنود" },
  chat: { en: "Chat", ar: "المحادثة" },
  benchmark: { en: "Benchmark", ar: "المقارنة المرجعية" },
  runBenchmark: { en: "Run benchmark", ar: "تشغيل المقارنة" },
  askQuestion: { en: "Ask about this contract…", ar: "اسأل عن هذا العقد…" },
  send: { en: "Send", ar: "إرسال" },
  confidence: { en: "Confidence", ar: "الثقة" },
  evidence: { en: "Evidence", ar: "الدليل" },
  explanation: { en: "Plain-language explanation", ar: "شرح مبسّط" },
  export: { en: "Export", ar: "تصدير" },
  exportPdf: { en: "Export PDF", ar: "تصدير PDF" },
  exportCsv: { en: "Export CSV", ar: "تصدير CSV" },
  exportJson: { en: "Export JSON", ar: "تصدير JSON" },
  settings: { en: "Settings", ar: "الإعدادات" },
  theme: { en: "Theme", ar: "السمة" },
  light: { en: "Light", ar: "فاتح" },
  dark: { en: "Dark", ar: "داكن" },
  degradedTitle: { en: "AI unavailable — degraded results", ar: "الذكاء الاصطناعي غير متاح — نتائج محدودة" },
  degradedBody: {
    en: "The local AI model could not be reached. These results were produced by keyword matching and need human review.",
    ar: "تعذر الوصول إلى نموذج الذكاء الاصطناعي المحلي. هذه النتائج ناتجة عن مطابقة الكلمات المفتاحية وتحتاج إلى مراجعة بشرية.",
  },
  selectContract: { en: "Select a contract to begin", ar: "اختر عقداً للبدء" },
  noContracts: { en: "No contracts yet. Upload or paste one to start.", ar: "لا توجد عقود بعد. ارفع أو الصق عقداً للبدء." },
  overview: { en: "Workspace overview", ar: "نظرة عامة" },
  highRisk: { en: "High-risk contracts", ar: "عقود عالية المخاطر" },
  recentFindings: { en: "Recent findings", ar: "أحدث النتائج" },
  outstandingReviews: { en: "Outstanding reviews", ar: "مراجعات معلقة" },
  avgHealth: { en: "Average health", ar: "متوسط الصحة" },
  gaps: { en: "Gaps vs. benchmark", ar: "الفجوات مقابل المعيار" },
  recommendation: { en: "Recommendation", ar: "التوصية" },
  status_found: { en: "Found", ar: "موجود" },
  status_partially_found: { en: "Partial", ar: "جزئي" },
  status_needs_review: { en: "Needs review", ar: "يحتاج مراجعة" },
  status_not_found: { en: "Not found", ar: "غير موجود" },
  delete: { en: "Delete", ar: "حذف" },
  loading: { en: "Loading…", ar: "جاري التحميل…" },
  emailSentIfExists: { en: "If that email exists, a reset token was issued.", ar: "إذا كان البريد موجوداً، تم إصدار رمز إعادة التعيين." },
  backToLogin: { en: "Back to login", ar: "العودة لتسجيل الدخول" },
};

export function translator(language: Language) {
  return (key: keyof typeof STRINGS): string => {
    const entry = STRINGS[key as string];
    if (!entry) return key as string;
    return entry[language] ?? entry.en;
  };
}

export type TranslateKey = keyof typeof STRINGS;
export function isRtl(language: Language): boolean {
  return language === "ar";
}
