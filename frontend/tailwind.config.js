/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#aa3bff',
        'primary-bg': 'rgba(170, 59, 255, 0.1)',
        'primary-border': 'rgba(170, 59, 255, 0.5)',
        accent: '#aa3bff',
        'accent-bg': 'rgba(170, 59, 255, 0.1)',
        'accent-border': 'rgba(170, 59, 255, 0.5)',
      },
    },
  },
  plugins: [],
}
