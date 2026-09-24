/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{svelte,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Design tokens. Prefer these over raw hex values in components.
      colors: {
        // Aubergine brand scale; 600 is the historical #772953.
        brand: {
          50: '#faf2f6',
          100: '#f3e2eb',
          200: '#e6c3d6',
          300: '#d197b7',
          400: '#b4668f',
          500: '#934170',
          600: '#772953',
          700: '#5e1f42',
          800: '#4a1934',
          900: '#361226',
          DEFAULT: '#772953',
        },
        link: {
          DEFAULT: '#0066cc',
          hover: '#004f9e',
        },
        // Visibility semantics, shared by badges and icons.
        public: { DEFAULT: '#217db1', bg: '#e2f2fd' },
        private: { DEFAULT: '#76306c', bg: '#fce3eb' },
      },
      fontFamily: {
        sans: ['Ubuntu', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"Ubuntu Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        // Smallest size allowed for readable text.
        '2xs': ['11px', '16px'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
