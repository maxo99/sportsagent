# Report: Show me a chart of top 10 QB passing yards leaders for this season

**Date:** 2025-12-09 09:17:27

## Query
```text
Show me a chart of top 10 QB passing yards leaders for this season
```

## Response
To show a chart of the top 10 QB passing yards leaders for this season, I will generate a visualization using the available data.

## Visualization
![Chart](chart.png)

## Visualization Code
```python
def generate_plot(df):
    import plotly.express as px

    # Filter for only quarterback positions for the current season
    current_season = df['season'].max()
    qb_data = df[(df['position'] == 'QB') & (df['season'] == current_season)]

    # Aggregate passing yards by player
    qb_aggregated = qb_data.groupby(['player_name', 'team'], as_index=False)['passing_yards'].sum()

    # Get the top 10 quarterbacks by passing yards
    top_10_qbs = qb_aggregated.nlargest(10, 'passing_yards')

    # Create a bar chart with player names on the x-axis and passing yards on the y-axis
    fig = px.bar(top_10_qbs, x='player_name', y='passing_yards', 
                 color='team', color_discrete_map=TEAM_COLORS,
                 title="Top 10 QB Passing Yards Leaders for the Season",
                 labels={'passing_yards': 'Passing Yards', 'player_name': 'Player Name'})
    
    return fig
```

## Chat History
### Human
Show me a chart of top 10 QB passing yards leaders for this season
