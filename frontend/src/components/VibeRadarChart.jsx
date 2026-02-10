import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts'

/**
 * 五维情感雷达图
 *
 * Props:
 *   - scores: { energy: 0.8, sorrow: 0.3, healing: 0.6, nostalgic: 0.5, loneliness: 0.4 }
 */

const DIMENSION_MAP = {
  energy: '能量',
  sorrow: '忧伤',
  healing: '治愈',
  nostalgic: '怀旧',
  loneliness: '孤独',
}

export default function VibeRadarChart({ scores }) {
  if (!scores) return null

  const data = Object.entries(DIMENSION_MAP).map(([key, label]) => ({
    dimension: label,
    value: Math.round((scores[key] ?? 0) * 100),
    fullMark: 100,
  }))

  return (
    <div className="w-full max-w-xs mx-auto">
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid
            stroke="var(--border-subtle)"
            strokeOpacity={0.6}
          />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fill: 'var(--text-secondary)', fontSize: 12, fontFamily: 'var(--font-display)' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={false}
            axisLine={false}
          />
          <Radar
            name="Vibe"
            dataKey="value"
            stroke="var(--accent-pink)"
            fill="var(--accent-pink)"
            fillOpacity={0.2}
            strokeWidth={2}
            dot={{
              r: 3,
              fill: 'var(--accent-pink)',
              strokeWidth: 0,
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
