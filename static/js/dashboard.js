// IvekBot Real-Time Weather Station Dashboard Engine

let timeChart = null;
let capeGaugeChart = null;
let ensembleChart = null;
let socket = null;

// Colores del Sistema
const THEME = {
  cyan: '#38bdf8',
  emerald: '#10b981',
  amber: '#f59e0b',
  rose: '#f43f5e',
  purple: '#818cf8',
  textSecondary: '#94a3b8',
  borderColor: '#1e293b'
};

document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  loadInitialData();
  connectWebSocket();
  setupGraphifySearch();
});

function initCharts() {
  // 1. Gráfica de Series Temporales (24h)
  const timeElem = document.getElementById('timeSeriesChart');
  if (timeElem) {
    timeChart = echarts.init(timeElem);
    const timeOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(19, 27, 46, 0.95)',
        borderColor: THEME.borderColor,
        textStyle: { color: '#f8fafc' }
      },
      legend: {
        data: ['Temperatura (°C)', 'Humedad (%)', 'Presión (hPa)'],
        textStyle: { color: THEME.textSecondary },
        top: 0
      },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
      xAxis: {
        type: 'category',
        data: [],
        axisLine: { lineStyle: { color: THEME.borderColor } },
        axisLabel: { color: THEME.textSecondary }
      },
      yAxis: [
        {
          type: 'value',
          name: 'Temp (°C)',
          position: 'left',
          axisLabel: { color: THEME.textSecondary },
          splitLine: { lineStyle: { color: 'rgba(30, 41, 59, 0.5)' } }
        },
        {
          type: 'value',
          name: 'Humedad (%)',
          position: 'right',
          axisLabel: { color: THEME.textSecondary },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: 'Temperatura (°C)',
          type: 'line',
          smooth: true,
          yAxisIndex: 0,
          data: [],
          itemStyle: { color: THEME.cyan },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(56, 189, 248, 0.35)' },
              { offset: 1, color: 'rgba(56, 189, 248, 0.0)' }
            ])
          }
        },
        {
          name: 'Humedad (%)',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: [],
          itemStyle: { color: THEME.emerald }
        }
      ]
    };
    timeChart.setOption(timeOption);
  }

  // 2. Gauge de Inestabilidad CAPE
  const gaugeElem = document.getElementById('capeGaugeChart');
  if (gaugeElem) {
    capeGaugeChart = echarts.init(gaugeElem);
    const gaugeOption = {
      backgroundColor: 'transparent',
      series: [{
        type: 'gauge',
        min: 0,
        max: 3500,
        radius: '95%',
        axisLine: {
          lineStyle: {
            width: 12,
            color: [
              [0.3, THEME.emerald],
              [0.6, THEME.amber],
              [1, THEME.rose]
            ]
          }
        },
        pointer: { itemStyle: { color: THEME.cyan } },
        axisTick: { distance: -12, length: 5, lineStyle: { color: '#fff', width: 1 } },
        splitLine: { distance: -12, length: 12, lineStyle: { color: '#fff', width: 2 } },
        axisLabel: { color: THEME.textSecondary, distance: 18, fontSize: 10 },
        detail: {
          valueAnimation: true,
          formatter: '{value} J/kg',
          color: '#f8fafc',
          fontSize: 16,
          offsetCenter: [0, '70%']
        },
        title: {
          offsetCenter: [0, '95%'],
          fontSize: 11,
          color: THEME.textSecondary
        },
        data: [{ value: 0, name: 'CAPE (Inestabilidad)' }]
      }]
    };
    capeGaugeChart.setOption(gaugeOption);
  }

  // 3. Gráfica de Ensamble 14 Días (Abanicos de Precipitación p10-p50-p90)
  const ensembleElem = document.getElementById('ensembleChart');
  if (ensembleElem) {
    ensembleChart = echarts.init(ensembleElem);
    const ensembleOption = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', textStyle: { color: '#f8fafc' }, backgroundColor: 'rgba(19, 27, 46, 0.95)', borderColor: THEME.borderColor },
      legend: { data: ['Lluvia Mediana (p50)', 'Lluvia Extrema (p90)'], textStyle: { color: THEME.textSecondary }, top: 0 },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
      xAxis: { type: 'category', data: [], axisLabel: { color: THEME.textSecondary } },
      yAxis: { type: 'value', name: 'Precipitación (mm)', splitLine: { lineStyle: { color: 'rgba(30, 41, 59, 0.5)' } }, axisLabel: { color: THEME.textSecondary } },
      series: [
        { name: 'Lluvia Mediana (p50)', type: 'bar', data: [], itemStyle: { color: THEME.cyan } },
        { name: 'Lluvia Extrema (p90)', type: 'line', smooth: true, data: [], itemStyle: { color: THEME.amber } }
      ]
    };
    ensembleChart.setOption(ensembleOption);
  }

  window.addEventListener('resize', () => {
    timeChart && timeChart.resize();
    capeGaugeChart && capeGaugeChart.resize();
    ensembleChart && ensembleChart.resize();
  });
}

async function loadInitialData() {
  try {
    const res = await fetch('/api/v1/dashboard/overview');
    if (!res.ok) return;
    const data = await res.json();

    updateTelemetryUI(data.current_telemetry, data.thermodynamics, data.risk);
    document.getElementById('exec-summary').innerText = data.executive_summary || '';

    // Cargar historial en gráfica
    if (data.recent_history && timeChart) {
      const times = data.recent_history.map(h => h.time);
      const temps = data.recent_history.map(h => h.temperature_c);
      const hums = data.recent_history.map(h => h.humidity_pct);

      timeChart.setOption({
        xAxis: { data: times },
        series: [
          { name: 'Temperatura (°C)', data: temps },
          { name: 'Humedad (%)', data: hums }
        ]
      });
    }

    // Cargar reporte completo para el ensamble
    loadForecastReport();
  } catch (err) {
    console.error("Error cargando dashboard inicial:", err);
  }
}

async function loadForecastReport() {
  try {
    const res = await fetch('/api/v1/forecast/report');
    if (!res.ok) return;
    const report = await res.json();

    document.getElementById('public-bulletin').innerText = report.public_bulletin || '';

    if (report.ensemble_14d && ensembleChart) {
      const dates = report.ensemble_14d.map(d => d.date.substring(5));
      const p50 = report.ensemble_14d.map(d => d.rain_p50_mm);
      const p90 = report.ensemble_14d.map(d => d.rain_p90_mm);

      ensembleChart.setOption({
        xAxis: { data: dates },
        series: [
          { name: 'Lluvia Mediana (p50)', data: p50 },
          { name: 'Lluvia Extrema (p90)', data: p90 }
        ]
      });
    }
  } catch (e) {
    console.error("Error cargando reporte:", e);
  }
}

function updateTelemetryUI(t, th, r) {
  if (t) {
    document.getElementById('val-temp').innerHTML = `${t.temperature_c} <span class="card-unit">°C</span>`;
    document.getElementById('val-humidity').innerHTML = `${t.humidity_pct} <span class="card-unit">%</span>`;
    document.getElementById('val-pressure').innerHTML = `${t.pressure_hpa} <span class="card-unit">hPa</span>`;
    document.getElementById('val-wind').innerHTML = `${t.wind_speed_kmh} <span class="card-unit">km/h</span>`;
    document.getElementById('val-wind-gust').innerText = `Racha máx: ${t.wind_gust_kmh || t.wind_speed_kmh} km/h`;
    document.getElementById('val-rain').innerHTML = `${t.rain_accum_24h_mm} <span class="card-unit">mm</span>`;
    document.getElementById('val-rain-rate').innerText = `Tasa: ${t.rain_rate_mmh} mm/h`;
  }

  if (th) {
    document.getElementById('val-dewpoint').innerText = `${th.dewpoint_c} °C`;
    document.getElementById('val-pwat').innerText = `${th.pwat_mm} mm`;
    document.getElementById('val-lcl').innerText = `${th.lcl_hpa} hPa`;
    document.getElementById('val-anomaly').innerText = `${th.thermal_anomaly_c > 0 ? '+' : ''}${th.thermal_anomaly_c} °C`;

    if (capeGaugeChart) {
      capeGaugeChart.setOption({
        series: [{ data: [{ value: Math.round(th.cape_jkg), name: 'CAPE (Inestabilidad)' }] }]
      });
    }
  }

  if (r) {
    const badge = document.getElementById('alert-badge');
    badge.innerText = `ALERTA: ${r.alert_level}`;
    const colorMap = {
      'VERDE': 'rgba(16, 185, 129, 0.2)',
      'AMARILLO': 'rgba(234, 179, 8, 0.2)',
      'NARANJA': 'rgba(249, 115, 22, 0.25)',
      'ROJO': 'rgba(239, 68, 68, 0.3)'
    };
    const textMap = {
      'VERDE': '#10b981',
      'AMARILLO': '#eab308',
      'NARANJA': '#f97316',
      'ROJO': '#ef4444'
    };
    badge.style.background = colorMap[r.alert_level] || colorMap['VERDE'];
    badge.style.color = textMap[r.alert_level] || textMap['VERDE'];
    badge.style.borderColor = textMap[r.alert_level] || textMap['VERDE'];
  }
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host || 'localhost:8000';
  const wsUrl = `${protocol}//${host}/ws/telemetry/live`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    const ind = document.getElementById('live-status-text');
    if (ind) ind.innerText = 'EN VIVO (WS ACTIVO)';
  };

  socket.onmessage = (event) => {
    try {
      const packet = JSON.parse(event.data);
      if (packet.telemetry) {
        updateTelemetryUI(packet.telemetry, packet.thermodynamics, packet.risk);
      }
    } catch (e) {
      console.error("Error parseando WebSocket:", e);
    }
  };

  socket.onclose = () => {
    const ind = document.getElementById('live-status-text');
    if (ind) ind.innerText = 'RECONECTANDO...';
    setTimeout(connectWebSocket, 3000);
  };
}

function setupGraphifySearch() {
  const btn = document.getElementById('btn-graph-query');
  const input = document.getElementById('graph-query-input');
  const out = document.getElementById('graph-query-output');

  if (btn && input && out) {
    btn.addEventListener('click', async () => {
      const q = input.value.trim();
      if (!q) return;
      out.style.display = 'block';
      out.innerText = 'Consultando Grafo de Conocimiento Graphify (GraphRAG)...';
      try {
        const res = await fetch('/api/v1/knowledge/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q, budget_tokens: 1200 })
        });
        const json = await res.json();
        out.innerText = json.result || 'Sin respuesta';
      } catch (err) {
        out.innerText = `Error: ${err.message}`;
      }
    });
  }
}
