// Tag filtering functionality
function filterPosts(tag) {
  const posts = document.querySelectorAll('.post-preview');
  const noResults = document.querySelector('.no-results') || createNoResultsMessage();

  let visibleCount = 0;

  posts.forEach(post => {
    const postTags = post.querySelectorAll('.tag');
    const hasTag = Array.from(postTags).some(tagEl => 
      tagEl.textContent.toLowerCase().includes(tag.toLowerCase())
    );

    if (hasTag) {
      post.style.display = 'block';
      visibleCount++;
    } else {
      post.style.display = 'none';
    }
  });

  // Show/hide no results message
  noResults.style.display = visibleCount === 0 ? 'block' : 'none';

  // Update page title
  const title = document.querySelector('h1');
  if (title) title.textContent = `🏷️ Posts tagged: ${tag}`;
}

function createNoResultsMessage() {
  const div = document.createElement('div');
  div.className = 'no-results';
  div.innerHTML = '<h3>No posts found for this tag</h3><p><a href="/">← Back to all posts</a></p>';
  document.querySelector('.recent-posts').appendChild(div);
  return div;
}

// LUXURY EFFECTS SYSTEM
function initLuxuryEffects() {
  // Create particle system
  const particleSystem = document.createElement('div');
  particleSystem.className = 'particle-system';
  document.body.appendChild(particleSystem);

  // Particle types
  const particleTypes = ['sparkle', 'diamond', 'star'];

  // Generate luxury particles
  function createParticle() {
    const particle = document.createElement('div');
    const type = particleTypes[Math.floor(Math.random() * particleTypes.length)];
    particle.className = `particle particle-${type}`;
    particle.style.left = Math.random() * 100 + '%';
    particle.style.animationDelay = Math.random() * 2 + 's';
    particle.style.animationDuration = (Math.random() * 3 + 4) + 's';
    particleSystem.appendChild(particle);

    setTimeout(() => particle.remove(), 8000);
  }

  // Create particles continuously
  setInterval(createParticle, 300);

  // Luxury gyroscope parallax
  if (window.DeviceOrientationEvent) {
    window.addEventListener('deviceorientation', function(e) {
      const cards = document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview');
      const beta = e.beta || 0;
      const gamma = e.gamma || 0;
      const xTilt = (gamma / 90) * 8;
      const yTilt = (beta / 90) * 8;

      cards.forEach((card, index) => {
        const multiplier = (index % 4 + 1) * 0.25;
        const x = xTilt * multiplier;
        const y = yTilt * multiplier;

        card.style.transform = `
          translateY(-4px) 
          rotateX(${y}deg) 
          rotateY(${x}deg)
          scale(1.01)
        `;
      });
    });
  }

  // Luxury mouse parallax for desktop
  document.addEventListener('mousemove', function(e) {
    if (window.innerWidth > 768) {
      const cards = document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview');
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      const mouseX = (e.clientX - centerX) / centerX;
      const mouseY = (e.clientY - centerY) / centerY;

      cards.forEach((card, index) => {
        const multiplier = (index % 3 + 1) * 0.1;
        const x = mouseX * 10 * multiplier;
        const y = mouseY * 10 * multiplier;

        card.style.transform = `
          translateY(-4px) 
          translateX(${x}px) 
          translateY(${y}px)
          rotateY(${mouseX * 5}deg)
          rotateX(${-mouseY * 5}deg)
        `;
      });
    }
  });

  // Luxury click effects
  document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview').forEach(element => {
    element.addEventListener('click', function(e) {
      const ripple = document.createElement('div');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        background: radial-gradient(circle, rgba(255,105,180,0.3), transparent);
        border-radius: 50%;
        transform: scale(0);
        animation: luxuryRipple 0.8s ease-out;
        pointer-events: none;
        z-index: 1000;
      `;

      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 800);
    });
  });

  // Add luxury ripple animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes luxuryRipple {
      to {
        transform: scale(2);
        opacity: 0;
      }
    }
  `;
  document.head.appendChild(style);

  // Intersection Observer for luxury reveals
  const luxuryObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0) scale(1)';
      }
    });
  }, { threshold: 0.1 });

  // Apply luxury reveal effects
  document.querySelectorAll('.celebrity-temp-card, .post-card, .post-preview').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px) scale(0.95)';
    card.style.transition = 'all 0.8s cubic-bezier(0.23, 1, 0.32, 1)';
    luxuryObserver.observe(card);
  });
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
  // Initialize luxury effects
  initLuxuryEffects();

  // Make tags clickable
  document.querySelectorAll('.tag-display').forEach(tag => {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', function() {
      const tagText = this.textContent.replace('#', '').split('(')[0].trim();
      filterPosts(tagText);
    });
  });

  // Enhanced tag hover effects
  document.querySelectorAll('.tag, .tag-display').forEach(tag => {
    tag.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-3px) scale(1.05)';
      this.style.boxShadow = '0 8px 20px rgba(255, 105, 180, 0.4)';
    });

    tag.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
      this.style.boxShadow = '';
    });
  });
});
