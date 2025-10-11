def init_template_filters(app):
    @app.template_filter('recent_fixtures')
    def recent_fixtures_filter(fixtures, limit=5):
        return sorted(fixtures, key=lambda x: x.gameweek.number, reverse=True)[:limit]
        
    @app.template_filter('indexOf')
    def index_of_filter(lst, value):
        try:
            return lst.index(value)
        except ValueError:
            return -1 