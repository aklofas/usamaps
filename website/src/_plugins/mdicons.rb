# Embed Material Design icons directly in the HTML webpage
# Uses icons from repo https://github.com/Templarian/MaterialDesign
# Find icons using website https://materialdesignicons.com/
module Jekyll
    class MDIcon < Liquid::Tag
        def initialize(tag_name, settings, tokens)
            super
            cmds = settings.split(',').map { |c| c.strip }
            @name = cmds[0]
            @cls = cmds.select { |c| c[0] == '.' }.map { |c| " #{c[1..-1]}"}.join
            
            colorcode = cmds.select { |c| c[0] == '#' }.first
            @color = if not colorcode.nil?
                @cls << " mdicolor"
                " style=\"fill: #{colorcode};\""
            else
                ""
            end

            @embed = !cmds.select { |c| c == 'embed' }.first.nil? ? true : false
        end

        def render(context)
            path = File.join(Jekyll.sites.first.config['source'], "_includes", "mdicons", "svg", "#{@name}.svg")
            path = File.join(Jekyll.sites.first.config['source'], "_includes", "usericons", "#{@name}.svg") if not File.exists?(path)
            
            if not File.exists?(path)
                return ""
            end

            data = IO.read(path).gsub(/<\?xml .*svg11\.dtd">/, '').gsub(/ id="[^"]*"/, '')

            if not @embed
                "<span class=\"mdicon#{@cls}\"#{@color}>#{data}</span>"
            else
                data.gsub(/<\/?svg[^>]*>/, '')
            end
        end
    end
end

Liquid::Template.register_tag('mdicon', Jekyll::MDIcon)
