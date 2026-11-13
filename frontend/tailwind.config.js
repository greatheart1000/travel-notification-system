/** @type {import('tailwindcss').Config} */

// 行程管家设计令牌：暖纸灰中性色 + 单一航线蓝强调色。
// 旧页面里的 slate/gray/blue/cyan/purple/indigo 等色板统一收敛到这里，
// 避免同屏出现多套强调色。
const paper = {
  50: '#FBFAF8',
  100: '#F7F6F3',
  200: '#F0EEE9',
  300: '#E4E1DA',
  400: '#C9C4BA',
  500: '#A8A29A',
  600: '#8A857D',
  700: '#57534E',
  800: '#35322E',
  900: '#1C1B19',
  950: '#12110F',
}

const accent = {
  50: '#EFF8FD',
  100: '#DFF1FB',
  200: '#B9E3F7',
  300: '#7CCCEF',
  400: '#38B0E3',
  500: '#0E93CC',
  600: '#027CB0',
  700: '#0369A1',
  800: '#075985',
  900: '#0C4A6E',
  950: '#082F49',
}

const success = {
  50: '#ECFDF3',
  100: '#D1FADF',
  200: '#A6F4C5',
  300: '#6CE9A6',
  400: '#32D583',
  500: '#12B76A',
  600: '#067647',
  700: '#05603A',
  800: '#054F31',
  900: '#053321',
}

const warning = {
  50: '#FFFAEB',
  100: '#FEF0C7',
  200: '#FEDF89',
  300: '#FEC84B',
  400: '#FDB022',
  500: '#F79009',
  600: '#B54708',
  700: '#93370D',
  800: '#7A2E0E',
  900: '#4E1D09',
}

const danger = {
  50: '#FEF3F2',
  100: '#FEE4E2',
  200: '#FECDCA',
  300: '#FDA29B',
  400: '#F97066',
  500: '#F04438',
  600: '#B42318',
  700: '#912018',
  800: '#7A271A',
  900: '#55160C',
}

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper,
        accent,
        success,
        warning,
        danger,
        // 旧色板收敛：中性色统一为暖纸灰
        slate: paper,
        gray: paper,
        zinc: paper,
        neutral: paper,
        stone: paper,
        // 蓝色系统一为单一强调色
        sky: accent,
        blue: accent,
        cyan: accent,
        teal: accent,
        // 语义色统一为低饱和版本
        green: success,
        emerald: success,
        lime: success,
        amber: warning,
        yellow: warning,
        orange: warning,
        red: danger,
        rose: danger,
        // 装饰性紫色系降为中性，避免残留 AI 紫
        purple: paper,
        violet: paper,
        indigo: paper,
        fuchsia: paper,
        pink: paper,
        primary: accent[600],
        secondary: paper[500],
      },
      fontFamily: {
        sans: [
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          '"Noto Sans CJK SC"',
          'sans-serif',
        ],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      maxWidth: {
        page: '1440px',
      },
      borderRadius: {
        control: '8px',
        card: '12px',
        panel: '16px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(28, 27, 25, 0.04)',
        raised: '0 8px 24px rgba(28, 27, 25, 0.06)',
      },
    },
  },
  plugins: [],
}
