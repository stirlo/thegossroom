module Jekyll
  class TagPageGenerator < Generator
    safe true

    def generate(site)
      # First pass - create pages for actual tags
      site.tags.each do |tag, posts|
        next if tag.nil? || tag.empty?
        site.pages << TagPage.new(site, site.source, tag, posts)
      end

      # Second pass - create alias pages for underscore/hyphen variants
      site.tags.each do |tag, posts|
        next if tag.nil? || tag.empty?

        if tag.include?('_')
          alias_tag = tag.gsub('_', '-')
          # Only create alias if it doesn't already exist as a real tag
          unless site.tags.key?(alias_tag)
            site.pages << TagPage.new(site, site.source, alias_tag, posts, tag)
          end
        elsif tag.include?('-') && tag.start_with?('source-')
          alias_tag = tag.gsub('-', '_')
          unless site.tags.key?(alias_tag)
            site.pages << TagPage.new(site, site.source, alias_tag, posts, tag)
          end
        end
      end
    end
  end

  class TagPage < Page
    def initialize(site, base, tag, posts, canonical_tag = nil)
      @site = site
      @base = base
      @dir = "tag/#{tag}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(base, '_layouts'), 'tag.html')

      # Use canonical tag for data lookup, display tag for URL
      display_tag = canonical_tag || tag
      self.data['tag'] = display_tag
      self.data['posts'] = posts
      self.data['title'] = "Posts tagged '#{display_tag}'"
      self.data['canonical_tag'] = canonical_tag
    end
  end
end
