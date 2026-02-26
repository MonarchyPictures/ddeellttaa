/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': '#3B82F6',
        'brand-secondary': '#1E40AF',
        'surface-primary': '#FFFFFF',
        'surface-secondary': '#F9FAFB',
        'surface-tertiary': '#F3F4F6',
        'text-primary': '#1F2937',
        'text-secondary': '#4B5563',
        'text-tertiary': '#9CA3AF',
        'success': '#10B981',
        'warning': '#F59E0B',
        'error': '#EF4444',
      }
    },
  },
  plugins: [],
}

