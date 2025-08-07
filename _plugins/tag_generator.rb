module Jekyll
  class TagPageGenerator < Generator
    safe true

    def generate(site)
      site.tags.each do |tag, posts|
        # Skip empty or nil tags
        next if tag.nil? || tag.empty?

        site.pages << TagPage.new(site, site.source, tag, posts)
      end
    end
  end

  class TagPage < Page
    def initialize(site, base, tag, posts)
      @site = site
      @base = base
      @dir = "tag/#{Jekyll::Utils.slugify(tag)}"  # This handles special chars
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(base, '_layouts'), 'tag.html')
      self.data['tag'] = tag
      self.data['posts'] = posts
      self.data['title'] = "Posts tagged '#{tag}'"
    end
  end
end
