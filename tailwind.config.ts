import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/!(node_modules)/*.{js,ts,jsx,tsx,mdx}",
    "./app/(features)/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/shared/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-space-grotesk)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;




