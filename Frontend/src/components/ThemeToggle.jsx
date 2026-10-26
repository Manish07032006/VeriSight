import { useTheme } from "../context/ThemeContext";

export default function ThemeToggle({ className = "" }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label="Toggle dark mode"
      className={`relative w-10 h-10 rounded-full flex items-center justify-center
                  bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm
                  border border-gray-200 dark:border-gray-700
                  text-gray-600 dark:text-gray-300
                  hover:scale-110 active:scale-95
                  transition-all duration-300 shadow-sm ${className}`}
    >
      <span className="text-lg transition-transform duration-500" style={{ transform: theme === "dark" ? "rotate(0deg)" : "rotate(180deg)" }}>
        {theme === "dark" ? "🌙" : "☀️"}
      </span>
    </button>
  );
}