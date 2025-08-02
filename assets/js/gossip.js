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

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
  // Make tags clickable
  document.querySelectorAll('.tag-display').forEach(tag => {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', function() {
      const tagText = this.textContent.replace('#', '').split('(')[0].trim();
      filterPosts(tagText);
    });
  });
});
