/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0B0F19', // Main app background
          sidebar: '#111827', // Sidebar background
          card: '#151C2C', // Table/card background
          border: '#1E293B', // Borders
          hover: '#1E293B', // Hover states
        },
        primary: {
          DEFAULT: '#6366F1', // Indigo blue for active items / buttons
          hover: '#4F46E5',
        },
        stock: {
          green: '#10B981', // Emerald green
          greenBg: 'rgba(16, 185, 129, 0.1)',
          red: '#EF4444', // Red
          redBg: 'rgba(239, 68, 68, 0.1)',
        },
        text: {
          primary: '#F8FAFC', // Slate 50
          secondary: '#94A3B8', // Slate 400
          muted: '#64748B', // Slate 500
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
