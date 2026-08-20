/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        slate: {
          850: '#151f32',
          900: '#0f172a',
          950: '#080d1a',
        },
        quantum: {
          blue: '#0284c7',
          cyan: '#38bdf8',
          green: '#22c55e',
          red: '#ef4444',
          amber: '#f59e0b',
        }
      }
    },
  },
  plugins: [],
}
