// src/components/PM25Chart.js
import React, { useRef } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  TimeScale,
} from "chart.js";
import { Line } from "react-chartjs-2";
import zoomPlugin from "chartjs-plugin-zoom";
import annotationPlugin from "chartjs-plugin-annotation";
import "chartjs-adapter-date-fns";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  TimeScale,
  zoomPlugin,
  annotationPlugin
);

export default function PM25Chart({ data = [], latest }) {
  const chartRef = useRef(null);
  if (!data.length) return null;

  // Thresholds (up to Unhealthy)
  const thresholds = [
    { label: "Good", max: 12, color: "green" },
    { label: "Moderate", max: 35.4, color: "goldenrod" },
    { label: "Unhealthy", max: 150.4, color: "orange" },
  ];

  // Determine active level; if above last threshold, mark as Hazardous
  const activeLevel =
    thresholds.find((t) => latest <= t.max) || { label: "Hazardous", color: "red" };

  const chartData = {
    labels: data.map((d) => new Date(d.timestamp)),
    datasets: [
      {
        label: "PM2.5 (µg/m³)",
        data: data.map((d) => d.value),
        borderColor: activeLevel.color,
        backgroundColor: `${activeLevel.color}50`,
        pointRadius: 4,
        tension: 0.3,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: "nearest",
        intersect: false,
        callbacks: {
          label: (ctx) => `PM2.5: ${ctx.parsed.y} µg/m³`,
        },
      },
      annotation: {
        // Only draw lines for thresholds, exclude Hazardous
        annotations: thresholds.map((t) => ({
          type: "line",
          yMin: t.max,
          yMax: t.max,
          borderColor: t.color,
          borderWidth: 2,
          borderDash: [6, 6],
          label: {
            content: t.label,
            enabled: true,
            position: "end",
            backgroundColor: `${t.color}20`,
            color: t.color,
          },
        })),
      },
      zoom: {
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: "xy",
        },
        pan: { enabled: true, mode: "xy" },
      },
    },
    scales: {
      x: {
        type: "time",
        time: { unit: "minute", tooltipFormat: "p" },
        title: { display: true, text: "Time" },
        grid: { display: false },
      },
      y: {
        title: { display: true, text: "PM2.5 (µg/m³)" },
        beginAtZero: true,
      },
    },
  };

  const lastUpdated = new Date(data[data.length - 1].timestamp).toLocaleTimeString();

  const handleResetZoom = () => {
    if (chartRef.current) chartRef.current.resetZoom();
  };

  return (
    <div
      style={{
        backgroundColor: "white",
        borderRadius: 12,
        padding: 20,
        marginBottom: 40,
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
      }}
    >
      <h3 style={{ marginBottom: 10 }}>
        PM2.5 Levels — <span style={{ color: activeLevel.color }}>{activeLevel.label}</span>
      </h3>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 20,
          marginBottom: 12,
          flexWrap: "wrap",
        }}
      >
        {thresholds.concat({ label: "Hazardous", color: "red" }).map((t) => (
          <div key={t.label}>
            <span style={{ color: t.color, fontWeight: "bold" }}>●</span> {t.label}
          </div>
        ))}
      </div>

      {/* Reset Zoom Button */}
      <div style={{ textAlign: "right", marginBottom: 8 }}>
        <button onClick={handleResetZoom}>Reset Zoom</button>
      </div>

      {/* Chart wrapper */}
      <div style={{ height: 400 }}>
        <Line ref={chartRef} data={chartData} options={chartOptions} />
      </div>

      <p style={{ fontSize: 12, color: "#666", marginTop: 8 }}>
        Last updated: {lastUpdated}
      </p>
    </div>
  );
}




