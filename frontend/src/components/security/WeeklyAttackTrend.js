import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { FaChartLine } from 'react-icons/fa';

const WeeklyAttackTrend = ({ data = [], height = 280, showTitle = true }) => {
  return (
    <div className="netshield-card" style={{ width: '100%' }}>
      {showTitle && (
        <div className="netshield-card-header">
          <div className="netshield-card-title">
            <FaChartLine style={{ color: 'var(--primary-green)' }} />
            <span>Weekly Attack Trend</span>
          </div>
          <span className="cyber-chip">Last 7 Days</span>
        </div>
      )}

      {data && data.length >= 2 ? (
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={data} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="attackGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22C55E" stopOpacity={0.45}/>
                <stop offset="95%" stopColor="#22C55E" stopOpacity={0.0}/>
              </linearGradient>
              <linearGradient id="critGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#EF4444" stopOpacity={0.5}/>
                <stop offset="95%" stopColor="#EF4444" stopOpacity={0.0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="short_day" stroke="#64748B" fontSize={11} tickLine={false} />
            <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0a1628',
                borderColor: 'rgba(34, 197, 94, 0.4)',
                borderRadius: 8,
                color: '#f8fafc',
                fontSize: '0.82rem'
              }}
              labelFormatter={(label, payload) => {
                const item = payload && payload[0]?.payload;
                return item ? `${item.day} (${item.display_date || item.date})` : label;
              }}
            />
            <Legend wrapperStyle={{ fontSize: '0.78rem', paddingTop: 10 }} />
            <Area
              type="monotone"
              dataKey="attacks"
              name="Total Attacks"
              stroke="#22C55E"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#attackGrad)"
              dot={{ r: 4, fill: '#22C55E' }}
              activeDot={{ r: 6 }}
            />
            <Area
              type="monotone"
              dataKey="critical_count"
              name="Critical Threats"
              stroke="#EF4444"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#critGrad)"
              dot={{ r: 4, fill: '#EF4444' }}
              activeDot={{ r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : data && data.length === 1 ? (
        <div style={{ padding: '36px 20px', textAlign: 'center', minHeight: height - 60, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 14px', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.35)', borderRadius: 20, color: '#f59e0b', fontSize: '0.8rem', fontWeight: 700, marginBottom: 14 }}>
            ● Insufficient trend data
          </div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>
            Single-Day Telemetry: {data[0].day} ({data[0].display_date || data[0].date})
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 12, marginBottom: 16 }}>
            <div style={{ padding: '10px 18px', background: '#0a1628', borderRadius: 6, border: '1px solid #1e3553' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Total Incursions</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#22C55E', marginTop: 2 }}>{data[0].attacks?.toLocaleString() || 0}</div>
            </div>
            <div style={{ padding: '10px 18px', background: '#0a1628', borderRadius: 6, border: '1px solid #1e3553' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Critical Threats</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#EF4444', marginTop: 2 }}>{data[0].critical_count?.toLocaleString() || 0}</div>
            </div>
          </div>
          <div style={{ fontSize: '0.82rem', color: '#64748b', maxWidth: 440 }}>
            Multi-day time-series trend curves will render automatically once traffic across 2 or more distinct days is ingested.
          </div>
        </div>
      ) : (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          <div style={{ fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>No data available</div>
          <div style={{ fontSize: '0.82rem' }}>No attack trend telemetry available for the past 7 days.</div>
        </div>
      )}
    </div>
  );
};

export default WeeklyAttackTrend;
