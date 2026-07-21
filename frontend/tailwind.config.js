/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Tailwind v4：theme token 全部在 globals.css 的 @theme inline 中定义。
  // 此处仅保留 content 检测与 typography 插件。
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
