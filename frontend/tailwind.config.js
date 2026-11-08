/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paypal: {
          navy: '#001C64',
          blue: '#0070BA',
          cyan: '#009CDE',
          gold: '#FFC439',
        }
      }
    },
  },
  plugins: [],
}

