/** @type {import('tailwindcss').Config} */

// 行程管家设计令牌：澄澈天蓝 + 奇幻粉。
// 中性色偏冷、偏亮，强调色只用于主操作与少量高光；
// 粉色只出现在 AI、品牌标记和需要被看见的时刻，避免整屏发腻。
const paper = {
  50: '#F7FBFF',
  100: '#EDF6FF',
  200: '#D9EAFB',
  300: '#BFD8F2',
  400: '#8FA9C6',
  500: '#5B7695',
  600: '#45627F',
  700: '#324E6C',
  800: '#233D59',
  900: '#142F4C',
  950: '#0A1E33',
}

const accent = {
  50: '#F0F9FF',
  100: '#E0F2FE',
  200: '#BAE6FD',
  300: '#7DD3FC',
  400: '#38BDF8',
  500: '#0EA5E9',
  600: '#0284C7',
  700: '#0369A1',
  800: '#075985',
  900: '#0C4A6E',
  950: '#082F49',
}

const blossom = {
  50: '#FFF5FA',
  100: '#FFE8F3',
  200: '#FCD0E5',
  300: '#F8A8D0',
  400: '#F472B6',
  500: '#EC4899',
  600: '#DB2777',
  700: '#BE185D',
  800: '#9D174D',
  900: '#831843',
  950: '#4A0E28',
}

const success = {
  50: '#ECFDF5',
  100: '#D1FAE5',
  200: '#A7F3D0',
  300: '#6EE7B7',
  400: '#34D399',
  500: '#10B981',
  600: '#047857',
  700: '#065F46',
  800: '#064E3B',
  900: '#022C22',
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
  50: '#FFF1F2',
  100: '#FFE4E6',
  200: '#FECDD3',
  300: '#FDA4AF',
  400: '#FB7185',
  500: '#F43F5E',
  600: '#BE123C',
  700: '#9F1239',
  800: '#881337',
  900: '#4C0519',
}

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper,
        accent,
        blossom,
        success,
        warning,
        danger,
        // 旧色板收敛：冷灰蓝统一为 paper
        slate: paper,
        gray: paper,
        zinc: paper,
        neutral: paper,
        stone: paper,
        // 蓝色系统一为天蓝强调色
        sky: accent,
        blue: accent,
        cyan: accent,
        teal: accent,
        // 粉色系统一为奇幻粉
        pink: blossom,
        fuchsia: blossom,
        rose: blossom,
        // 语义色
        green: success,
        emerald: success,
        lime: success,
        amber: warning,
        yellow: warning,
        orange: warning,
        red: danger,
        // 装饰性紫色系降为中性，避免残留 AI 紫
        purple: paper,
        violet: paper,
        indigo: paper,
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
        control: '10px',
        card: '14px',
        panel: '18px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(20, 47, 76, 0.04), 0 10px 28px -18px rgba(20, 47, 76, 0.18)',
        raised: '0 18px 46px -18px rgba(20, 47, 76, 0.22)',
        stat: '0 10px 28px -18px rgba(20, 47, 76, 0.18)',
        primary: '0 10px 22px -12px rgba(20, 47, 76, 0.25)',
      },
      backgroundImage: {
        'dreamy-wash':
          'radial-gradient(900px 480px at 8% -10%, #E0F2FE 0%, rgba(224,242,254,0) 60%), radial-gradient(800px 420px at 92% 0%, #FFE8F3 0%, rgba(255,232,243,0) 58%)',
        'dreamy-page':
          'radial-gradient(1100px 620px at 5% -8%, #DDF1FF 0%, rgba(221,241,255,0) 62%), radial-gradient(960px 560px at 100% 4%, #FFE3F1 0%, rgba(255,227,241,0) 58%), linear-gradient(165deg, #F7FCFF 0%, #EDF6FF 48%, #FFF8FC 100%)',
        'dreamy-hero':
          'linear-gradient(115deg, rgba(224,242,254,0.92) 0%, rgba(255,255,255,0.92) 44%, rgba(255,232,243,0.9) 100%)',
        'dreamy-card':
          'linear-gradient(155deg, #FFFFFF 0%, #F6FBFF 58%, #FFF7FB 100%)',
        'brand-line':
          'linear-gradient(90deg, #0EA5E9 0%, #38BDF8 34%, #F472B6 68%, #EC4899 100%)',
      },
    },
  },
  plugins: [],
}
