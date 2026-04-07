# _plugins/slug_index.rb
# Generates /slugs.json at build time — a lightweight index of all post
# URLs and their slugs, consumed by 404.html for fuzzy redirect matching.
#
# Format: [{"url": "/2025/08/02/some-post/", "slug": "some-post"}, ...]

Jekyll::Hooks.register :site, :post_write do |site|
  entries = site.posts.docs.map do |post|
    slug = post.data['slug'] || post.url.split('/').last.chomp('/')
    { 'url' => post.url, 'slug' => slug, 'title' => post.data['title'].to_s }
  end

  output_path = File.join(site.dest, 'slugs.json')
  File.write(output_path, JSON.generate(entries))
  Jekyll.logger.info "SlugIndex:", "Wrote #{entries.size} entries to /slugs.json"
end
