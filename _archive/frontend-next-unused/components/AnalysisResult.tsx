import type { AnalysisSection, GroundedAnalysis } from "@/lib/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

const SECTION_ORDER = ["summary", "risks", "health"];
const SECTION_LABELS: Record<string, string> = {
  summary: "Summary",
  risks: "Risks & red flags",
  health: "Contract health",
};

function Section({ section }: { section: AnalysisSection }) {
  const answer = section.answer?.trim() || "No answer was produced for this section.";
  const notFound = answer.toLowerCase().startsWith("not found");
  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">
          {SECTION_LABELS[section.section] ?? section.section}
        </span>
        <ConfidenceBadge value={section.confidence ?? 0} />
      </div>
      <div className="section-body">
        <p style={{ marginTop: 0 }}>{answer}</p>

        {section.missing_information?.length > 0 && (
          <p className="subtle" style={{ fontSize: "0.85rem" }}>
            Not addressed by the contract: {section.missing_information.join(", ")}
          </p>
        )}

        {!notFound &&
          section.evidence?.map((ev, i) => (
            <blockquote className="evidence" key={i}>
              “{ev.quote}”
              <cite>{ev.location || "Contract evidence"}</cite>
            </blockquote>
          ))}

        {!notFound && (section.evidence?.length ?? 0) === 0 && (
          <p className="subtle" style={{ fontSize: "0.8rem" }}>
            No direct citation was retrieved for this section.
          </p>
        )}
      </div>
    </div>
  );
}

export function AnalysisResult({ data }: { data: GroundedAnalysis }) {
  const sections = SECTION_ORDER.map((key) => data.sections[key]).filter(
    (s): s is AnalysisSection => Boolean(s)
  );

  return (
    <div>
      {data.degraded_mode && (
        <div className="banner degraded">
          ⚠️ The AI model was unreachable, so these results are keyword-derived
          (degraded mode), not a model judgement. Start Ollama for grounded analysis.
        </div>
      )}
      <div className="row spread" style={{ marginBottom: "1rem" }}>
        <span className="subtle">
          Source: {data.evaluation_source === "llm" ? "Grounded model" : "Rule-based fallback"}
        </span>
        <span className="subtle">
          Overall confidence: {Math.round((data.overall_confidence ?? 0) * 100)}%
        </span>
      </div>
      {sections.map((s) => (
        <Section key={s.section} section={s} />
      ))}
    </div>
  );
}
