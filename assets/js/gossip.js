// ═══════════════════════════════════════════════════════════════
// gossip.js — TFP GossRoom interaction layer
// Removed: particle system (was a z:1000 overlay blocking the page),
//          opacity:0 IntersectionObserver (was hiding cards permanently),
//          mousemove parallax (was fighting CSS hover transforms).
// Kept: tag filtering, click ripple, tag hover micro-interactions.
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

// ── Click ripple — kept, it's harmless and satisfying ────────────
function initRipple() {
  // Inject the ripple keyframe once
  const style = document.createElement('style');
  style.textContent = `
    @keyframes gossipRipple {
      to { transform: scale(2.5); opacity: 0; }
    }`;
  document.head.appendChild(style);

  document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview')
    .forEach(el => {
      // Ensure position:relative so absolute ripple is contained
      if (getComputedStyle(el).position === 'static') {
        el.style.position = 'relative';
      }
      el.style.overflow = 'hidden';

      el.addEventListener('click', function(e) {
        const rect  = this.getBoundingClientRect();
        const size  = Math.max(rect.width, rect.height);
        const ripple = document.createElement('div');

        ripple.style.cssText = [
          'position:absolute',
          `width:${size}px`,
          `height:${size}px`,
          `left:${e.clientX - rect.left - size / 2}px`,
          `top:${e.clientY - rect.top  - size / 2}px`,
          'background:radial-gradient(circle, rgba(232,48,90,0.25), transparent)',
          'border-radius:50%',
          'transform:scale(0)',
          'animation:gossipRipple 0.7s ease-out forwards',
          'pointer-events:none',
          'z-index:2',
        ].join(';');

        this.appendChild(ripple);
        setTimeout(() => ripple.remove(), 700);
      });
    });
}

// ── Tag micro-interactions ────────────────────────────────────────
function initTagInteractions() {
  // Make tag-display elements filterable
  document.querySelectorAll('.tag-display').forEach(tag => {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', function() {
      const text = this.textContent.replace('#', '').split('(')[0].trim();
      filterPosts(text);
    });
  });

  // Subtle hover lift on all tags
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
  initRipple();
  initTagInteractions();
});
