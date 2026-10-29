import { useEffect, useState } from "react";
import type { FootageStatus } from "./types";

// Footage stages are ordered (planned -> delivered), so they use one blue hue stepped
// light -> dark rather than four unrelated colors. Both ramps pass an ordinal
// colour-accessibility check against their background. In dark mode the ramp flips
// so "delivered" is still the step that stands out most.
const LIGHT = {
  stages: { planned: "#86b6ef", shot: "#3987e5", edited: "#1c5cab", delivered: "#0d366b" },
  surface: "#fcfcfb",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  textSecondary: "#52514e",
  textMuted: "#898781",
  hover: "rgba(11, 11, 11, 0.04)",
};

const DARK: typeof LIGHT = {
  stages: { planned: "#184f95", shot: "#2a78d6", edited: "#6da7ec", delivered: "#b7d3f6" },
  surface: "#1a1a19",
  grid: "#2c2c2a",
  axis: "#383835",
  textSecondary: "#c3c2b7",
  textMuted: "#898781",
  hover: "rgba(255, 255, 255, 0.05)",
};

export type Palette = typeof LIGHT;
export type StageColors = Record<FootageStatus, string>;

const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

/** The palette for the current light/dark setting; updates if the OS setting changes. */
export function usePalette(): Palette {
  const [isDark, setIsDark] = useState(darkQuery.matches);
  useEffect(() => {
    const onChange = (e: MediaQueryListEvent) => setIsDark(e.matches);
    darkQuery.addEventListener("change", onChange);
    return () => darkQuery.removeEventListener("change", onChange);
  }, []);
  return isDark ? DARK : LIGHT;
}
