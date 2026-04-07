// ═══════════════════════════════════════════════════════════════
// gossip.js — TFP GossRoom interaction layer
// FX restored: particles (behind content, pointer-events:none),
//              gyroscope parallax, mousemove parallax.
// Kept removed: opacity:0 IntersectionObserver (was hiding cards),
//               checkbox/label nav (replaced in header.html).
// ═══════════════════════════════════════════════════════════════

// ── Tag filtering ────────────────────────────────────────────────
function filterPosts(tag) {
  const posts = document.querySelectorAll('.post-preview');
  const noResults = document.querySelector('.no-results') || createNoResultsMessage();
  let visibleCount = 0;
  posts.forEach(post => {
    const hasTag = Array.from(post.querySelectorAll('.tag'))
      .some(el => el.textContent.toLowerCase().includes(tag.toLowerCase()));
    post.style.display = hasTag ? 'block' : 'none';
    if (hasTag) visibleCount++;
  });
  noResults.style.display = visibleCount === 0 ? 'block' : 'none';
  const h1 = document.querySelector('h1');
  if (h1) h1.textContent = `🏷️ Posts tagged: ${tag}`;
}

function createNoResultsMessage() {
  const div = document.createElement('div');
  div.className = 'no-results';
  div.innerHTML = '<h3>No posts found for this tag</h3><p><a href="/">← Back to all posts</a></p>';
  const container = document.querySelector('.recent-posts');
  if (container) container.appendChild(div);
  return div;
}

// ── Particle system ───────────────────────────────────────────────
// Fixed vs original: z-index:-1 (behind content), pointer-events:none
// on the container so particles never intercept clicks or hover.
function initParticles() {
  const style = document.createElement('style');
  style.textContent = `
    .particle-system {
      position: fixed;
      inset: 0;
      pointer-events: none;   /* CRITICAL — never blocks clicks */
      z-index: 0;             /* behind page content */
      overflow: hidden;
    }
    .particle {
      position: absolute;
      pointer-events: none;
      border-radius: 50%;
      animation: particleFloat linear forwards;
      opacity: 0;
    }
    .particle-sparkle {
      width: 4px; height: 4px;
      background: radial-gradient(circle, #ffff00, rgba(255,213,0,0));
      box-shadow: 0 0 6px 2px rgba(255,215,0,0.6);
    }
    .particle-diamond {
      width: 5px; height: 5px;
      background: radial-gradient(circle, #ff2d6b, rgba(232,48,90,0));
      box-shadow: 0 0 6px 2px rgba(232,48,90,0.5);
      border-radius: 2px;
      transform: rotate(45deg);
    }
    .particle-star {
      width: 3px; height: 3px;
      background: radial-gradient(circle, #ffffff, rgba(255,255,255,0));
      box-shadow: 0 0 4px 1px rgba(255,255,255,0.4);
    }
    @keyframes particleFloat {
      0%   { transform: translateY(100vh) scale(0); opacity: 0; }
      10%  { opacity: 0.8; }
      90%  { opacity: 0.4; }
      100% { transform: translateY(-20px) scale(1.2);  opacity: 0; }
    }
  `;
  document.head.appendChild(style);

  const container = document.createElement('div');
  container.className = 'particle-system';
  document.body.appendChild(container);

  const types = ['sparkle', 'diamond', 'star'];

  function spawnParticle() {
    const particle = document.createElement('div');
    particle.className = `particle particle-${types[Math.floor(Math.random() * types.length)]}`;
    particle.style.left    = (Math.random() * 100) + '%';
    const dur = (Math.random() * 4 + 4).toFixed(1) + 's';
    particle.style.animationDuration = dur;
    particle.style.animationDelay    = '0s';
    container.appendChild(particle);
    setTimeout(() => particle.remove(), parseFloat(dur) * 1000 + 100);
  }

  // Spawn rate: one every 400ms — lighter than original 300ms
  setInterval(spawnParticle, 400);
}

// ── Gyroscope parallax (mobile) ───────────────────────────────────
function initGyroscope() {
  if (!window.DeviceOrientationEvent) return;
  window.addEventListener('deviceorientation', function(e) {
    const cards = document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview');
    const xTilt = ((e.gamma || 0) / 90) * 6;
    const yTilt = ((e.beta  || 0) / 90) * 6;
    cards.forEach((card, i) => {
      const m = (i % 4 + 1) * 0.2;
      card.style.transform = `rotateX(${yTilt * m}deg) rotateY(${xTilt * m}deg)`;
    });
  });
}

// ── Mouse parallax (desktop) ──────────────────────────────────────
// Reduced multipliers vs original (was 10x, now 5x) so it doesn't
// fight aggressively with CSS :hover transitions.
function initMouseParallax() {
  if (window.innerWidth <= 768) return;
  document.addEventListener('mousemove', function(e) {
    const cards = document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview');
    const cx = window.innerWidth  / 2;
    const cy = window.innerHeight / 2;
    const mx = (e.clientX - cx) / cx;
    const my = (e.clientY - cy) / cy;
    cards.forEach((card, i) => {
      // Skip if card is being hovered — let CSS :hover take over cleanly
      if (card.matches(':hover')) return;
      const m = (i % 3 + 1) * 0.08;
      card.style.transform = `translateX(${mx * 5 * m}px) translateY(${my * 5 * m}px)`;
    });
  });
}

// ── Click ripple ──────────────────────────────────────────────────
function initRipple() {
  const style = document.createElement('style');
  style.textContent = `@keyframes gossipRipple { to { transform:scale(2.5); opacity:0; } }`;
  document.head.appendChild(style);

  document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview')
    .forEach(el => {
      if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
      el.style.overflow = 'hidden';
      el.addEventListener('click', function(e) {
        const rect   = this.getBoundingClientRect();
        const size   = Math.max(rect.width, rect.height);
        const ripple = document.createElement('div');
        ripple.style.cssText = [
          'position:absolute',
          `width:${size}px`, `height:${size}px`,
          `left:${e.clientX - rect.left - size / 2}px`,
          `top:${e.clientY  - rect.top  - size / 2}px`,
          'background:radial-gradient(circle, rgba(232,48,90,0.28), transparent)',
          'border-radius:50%',
          'transform:scale(0)',
          'animation:gossipRipple 0.7s ease-out forwards',
          'pointer-events:none',
          'z-index:3',
        ].join(';');
        this.appendChild(ripple);
        setTimeout(() => ripple.remove(), 700);
      });
    });
}

// ── Tag micro-interactions ────────────────────────────────────────
function initTagInteractions() {
  document.querySelectorAll('.tag-display').forEach(tag => {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', function() {
      filterPosts(this.textContent.replace('#', '').split('(')[0].trim());
    });
  });
  document.querySelectorAll('.tag, .tag-display').forEach(tag => {
    tag.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-2px) scale(1.04)';
    });
    tag.addEventListener('mouseleave', function() {
      this.style.transform = '';
    });
  });
}

// ── Init ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  initParticles();
  initGyroscope();
  initMouseParallax();
  initRipple();
  initTagInteractions();
});
