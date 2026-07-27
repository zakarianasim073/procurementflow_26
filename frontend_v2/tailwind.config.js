import { readFileSync } from 'node:fs'

/**
 * Generated from shared/styles/tokens.json (ADR-004, PFX-06). Do not add literal color,
 * radius, shadow, or duration values here — edit tokens.json and this file re-reads it.
 * @type {import('tailwindcss').Config}
 */
const tokens = JSON.parse(
  readFileSync(new URL('./src/shared/styles/tokens.json', import.meta.url), 'utf-8')
)

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        gray: tokens.color.gray,
        brand: tokens.color.brand,
        accent: tokens.color.accent,
        success: tokens.color.semantic.success,
        warning: tokens.color.semantic.warning,
        danger: tokens.color.semantic.danger,
        info: tokens.color.semantic.info,
        interactive: {
          DEFAULT: tokens.color.interactive.primary,
          hover: tokens.color.interactive.primaryHover,
          text: tokens.color.interactive.primaryText,
        },
      },
      backgroundImage: {
        'brand-gradient': tokens.color.decorativeGradient.brand,
      },
      fontFamily: {
        sans: tokens.typography.fontFamily.sans.split(', '),
      },
      fontSize: Object.fromEntries(
        Object.entries(tokens.typography.scale).map(([key, { size, lineHeight }]) => [
          key,
          [size, { lineHeight }],
        ])
      ),
      fontWeight: tokens.typography.weight,
      borderRadius: tokens.radius,
      boxShadow: {
        glass: tokens.elevation.glass.shadow,
        'glass-hover': tokens.elevation.glass.shadowHover,
        'glass-dark': tokens.elevation.glass.shadowDark,
      },
      transitionDuration: tokens.motion.duration,
      transitionTimingFunction: {
        standard: tokens.motion.easing.standard,
      },
    },
  },
  plugins: [],
}
