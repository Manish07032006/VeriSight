const POSITIVE_VERDICTS = new Set(["real", "human", "authentic"]);
const NEGATIVE_VERDICTS = new Set(["fake", "ai_generated", "synthetic", "manipulated"]);

export default function VerdictBadge({ label, verdict, confidence, color }) {
  if (!verdict || verdict === "not_yet_available") {
    return null;
  }

  // Respect the explicit color property sent from the backend, or fallback to keyword matching
  const isForcedGreen = color === "green";
  const isForcedRed = color === "red";

  const isPositive = isForcedGreen || POSITIVE_VERDICTS.has(verdict.toLowerCase().replace(/\s+/g, "_"));
  const isNegative = isForcedRed || NEGATIVE_VERDICTS.has(verdict.toLowerCase().replace(/\s+/g, "_"));

  const colorClasses = isPositive
    ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30"
    : isNegative
    ? "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/30"
    : "bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700";

  const displayVerdict = verdict.replace(/_/g, " ");

  return (
    <div
      className={`rounded-xl border px-3 py-2.5 transition-all duration-300
                  hover:shadow-md hover:-translate-y-0.5 ${colorClasses}`}
    >
      <p className="text-xs opacity-80 mb-0.5">{label}</p>
      <p className="font-semibold capitalize">{displayVerdict}</p>
      {typeof confidence === "number" && confidence > 0 && (
        <div className="mt-1.5">
          <div className="w-full h-1.5 rounded-full bg-black/5 dark:bg-white/10 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${
                isPositive ? "bg-emerald-500" : isNegative ? "bg-rose-500" : "bg-gray-400"
              }`}
              style={{ width: `${confidence}%` }}
            />
          </div>
          <p className="text-xs opacity-70 mt-1">{confidence.toFixed(1)}% confidence</p>
        </div>
      )}
    </div>
  );
}