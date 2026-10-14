/**
 * StudyMindAI Native High-Fidelity Canvas Charting
 * Renders custom animated Mastery Radar and Trajectory Line charts
 * optimized for clean off-white studio aesthetic and crystal-clear contrast.
 */

export function renderRadarChart(canvasId, topicStats) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const centerX = w / 2;
  const centerY = h / 2;
  const radius = Math.min(centerX, centerY) - 45;

  ctx.clearRect(0, 0, w, h);

  if (!topicStats || topicStats.length < 3) {
    ctx.fillStyle = '#64748b';
    ctx.font = '14px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('Complete practice questions to view skill mastery', centerX, centerY);
    return;
  }

  const numAxes = topicStats.length;
  const angleStep = (Math.PI * 2) / numAxes;

  // 1. Concentric Guide Circles
  const levels = [0.25, 0.5, 0.75, 1.0];
  levels.forEach((lvl) => {
    ctx.beginPath();
    for (let i = 0; i <= numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + Math.cos(angle) * (radius * lvl);
      const y = centerY + Math.sin(angle) * (radius * lvl);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = lvl === 0.75 ? 'rgba(5, 150, 105, 0.45)' : 'rgba(15, 23, 42, 0.08)';
    ctx.lineWidth = lvl === 0.75 ? 1.5 : 1;
    if (lvl === 0.75) ctx.setLineDash([4, 4]);
    else ctx.setLineDash([]);
    ctx.stroke();
  });
  ctx.setLineDash([]);

  // 2. Spokes & Axis Labels
  ctx.font = '500 11px Inter';
  ctx.fillStyle = '#334155';
  topicStats.forEach((t, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const endX = centerX + Math.cos(angle) * radius;
    const endY = centerY + Math.sin(angle) * radius;

    // Spoke line
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(endX, endY);
    ctx.strokeStyle = 'rgba(15, 23, 42, 0.08)';
    ctx.stroke();

    // Text Label
    const labelX = centerX + Math.cos(angle) * (radius + 24);
    const labelY = centerY + Math.sin(angle) * (radius + 24);
    ctx.textAlign = Math.abs(Math.cos(angle)) < 0.2 ? 'center' : Math.cos(angle) > 0 ? 'left' : 'right';
    ctx.textBaseline = 'middle';

    const shortName = t.topic_name.length > 18 ? t.topic_name.substring(0, 16) + '...' : t.topic_name;
    ctx.fillText(`${shortName} (${Math.round(t.accuracy)}%)`, labelX, labelY);
  });

  // 3. Student Mastery Polygon
  ctx.beginPath();
  topicStats.forEach((t, i) => {
    const val = Math.max(0.08, Math.min(1.0, t.accuracy / 100));
    const angle = i * angleStep - Math.PI / 2;
    const x = centerX + Math.cos(angle) * (radius * val);
    const y = centerY + Math.sin(angle) * (radius * val);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();

  // Clean studio gradient fill
  const grad = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, radius);
  grad.addColorStop(0, 'rgba(79, 70, 229, 0.25)');
  grad.addColorStop(1, 'rgba(2, 132, 199, 0.12)');
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.strokeStyle = '#4f46e5';
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Dots at vertices
  topicStats.forEach((t, i) => {
    const val = Math.max(0.08, Math.min(1.0, t.accuracy / 100));
    const angle = i * angleStep - Math.PI / 2;
    const x = centerX + Math.cos(angle) * (radius * val);
    const y = centerY + Math.sin(angle) * (radius * val);

    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = '#4f46e5';
    ctx.lineWidth = 2;
    ctx.stroke();
  });
}

export function renderTimelineChart(canvasId, history) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const padLeft = 45;
  const padRight = 25;
  const padTop = 25;
  const padBottom = 35;

  ctx.clearRect(0, 0, w, h);

  if (!history || history.length === 0) {
    ctx.fillStyle = '#64748b';
    ctx.font = '14px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('Complete quizzes to view score trajectory', w / 2, h / 2);
    return;
  }

  // Draw Background Grid
  ctx.strokeStyle = 'rgba(15, 23, 42, 0.08)';
  ctx.lineWidth = 1;
  for (let pct = 0; pct <= 100; pct += 25) {
    const y = padTop + (1 - pct / 100) * (h - padTop - padBottom);
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(w - padRight, y);
    ctx.stroke();

    ctx.fillStyle = '#64748b';
    ctx.font = '10px JetBrains Mono';
    ctx.textAlign = 'right';
    ctx.fillText(`${pct}%`, padLeft - 8, y + 3);
  }

  // Benchmark line (70% Target)
  const y70 = padTop + (1 - 0.70) * (h - padTop - padBottom);
  ctx.beginPath();
  ctx.setLineDash([4, 4]);
  ctx.strokeStyle = 'rgba(5, 150, 105, 0.55)';
  ctx.lineWidth = 1.5;
  ctx.moveTo(padLeft, y70);
  ctx.lineTo(w - padRight, y70);
  ctx.stroke();
  ctx.setLineDash([]);

  // Calculate points
  const items = history.slice(-12);
  const stepX = (w - padLeft - padRight) / Math.max(1, items.length - 1);

  const points = items.map((item, idx) => {
    const accuracy = item.total_questions > 0 ? item.score / item.total_questions : 0;
    const x = items.length === 1 ? (w - padLeft - padRight) / 2 + padLeft : padLeft + idx * stepX;
    const y = padTop + (1 - accuracy) * (h - padTop - padBottom);
    return { x, y, accuracy: Math.round(accuracy * 100), label: `#${item.id}` };
  });

  // Area fill under curve
  if (points.length > 1) {
    ctx.beginPath();
    ctx.moveTo(points[0].x, h - padBottom);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, h - padBottom);
    ctx.closePath();

    const areaGrad = ctx.createLinearGradient(0, padTop, 0, h - padBottom);
    areaGrad.addColorStop(0, 'rgba(79, 70, 229, 0.16)');
    areaGrad.addColorStop(1, 'rgba(79, 70, 229, 0.01)');
    ctx.fillStyle = areaGrad;
    ctx.fill();
  }

  // Connecting line
  ctx.beginPath();
  points.forEach((p, i) => {
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.strokeStyle = '#4f46e5';
  ctx.lineWidth = 2.8;
  ctx.stroke();

  // Data point markers
  points.forEach((p) => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = p.accuracy >= 70 ? '#059669' : '#d97706';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    ctx.fillStyle = '#0f172a';
    ctx.font = '600 10px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText(`${p.accuracy}%`, p.x, p.y - 10);
  });
}
