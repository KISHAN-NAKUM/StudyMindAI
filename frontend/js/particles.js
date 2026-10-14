/**
 * StudyMindAI Ambient Background Neural Network Particle System
 * Creates high-performance animated glowing constellation and floating neural nodes
 * tailored for clean, modern off-white surfaces.
 */

export function initAmbientParticles(canvasId = 'ambient-canvas') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  const particles = [];
  const particleCount = Math.min(50, Math.floor((width * height) / 22000));

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  const colors = ['#6366f1', '#8b5cf6', '#0284c7', '#a855f7'];

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      radius: Math.random() * 2 + 1.2,
      color: colors[Math.floor(Math.random() * colors.length)],
      baseAlpha: Math.random() * 0.35 + 0.15
    });
  }

  function render() {
    ctx.clearRect(0, 0, width, height);

    // Update & draw particles
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0) p.x = width;
      if (p.x > width) p.x = 0;
      if (p.y < 0) p.y = height;
      if (p.y > height) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.baseAlpha;
      ctx.fill();

      // Connect nearby particles with subtle synaptic lines
      for (let j = i + 1; j < particles.length; j++) {
        const p2 = particles[j];
        const dx = p.x - p2.x;
        const dy = p.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = p.color;
          ctx.globalAlpha = (1 - dist / 120) * 0.12;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }

    ctx.globalAlpha = 1.0;
    requestAnimationFrame(render);
  }

  render();
}
