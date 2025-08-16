# Admin Views Guide - Superuser Only

This guide explains the new superuser-only admin views for agent analytics and property rankings.

## Overview

Two new admin views have been added to provide comprehensive analytics and rankings for real estate agents and properties:

1. **Agent Analytics Dashboard** - Shows agent performance metrics and rankings
2. **Property Rankings** - Displays properties ranked by various criteria

## Access

These views are only accessible to superusers. They can be accessed through:

- **Navigation Menu**: When logged in as a superuser, you'll see additional menu items in the user dropdown
- **Direct URLs**: 
  - `/dashboard/agents/` - Agent Analytics
  - `/dashboard/rankings/` - Property Rankings

## Agent Analytics Dashboard

### Features

- **Agent Cards**: Display agents in neat cards (5 per row on large screens)
- **Ranking System**: Agents are ranked based on multiple factors:
  - Total listings (30% weight)
  - Average investment score (20% weight)
  - High-score listings (30% weight)
  - Completed analyses (20% weight)

### Metrics Displayed

Each agent card shows:
- **Rank**: Position in overall ranking (gold/silver/bronze for top 3)
- **Key Metrics**: Total listings, average investment score, average price, price per m²
- **Performance Metrics**: Premium listings, high-score listings, active listings
- **Difficulty Coefficient**: Calculated based on price consistency, response rate, and listing quality
- **Contact Information**: Email and phone (if available)

### Agent Details Modal

Click "Details" on any agent card to see:
- Detailed statistics
- Recommendation breakdown (Strong Buy, Buy, Hold, Avoid)
- Recent properties list

## Property Rankings

### Ranking Types

Properties can be ranked by:

1. **Best Price per m²** - Properties with lowest €/m² (best value)
2. **Highest Investment Score** - Properties with best AI recommendations
3. **Best Market Position** - Properties priced below market average
4. **Highest Opportunity Score** - Properties with best market timing

### Filtering Options

- **Location**: Filter by specific cities/areas
- **Property Type**: Filter by apartment, villa, commercial, etc.
- **Ranking Type**: Switch between different ranking criteria

### Property Cards

Each property card displays:
- **Rank**: Position in current ranking (gold/silver/bronze for top 3)
- **Property Details**: Title, location, neighborhood, property type
- **Key Metrics**: Price, area, ranking-specific metric
- **Recommendation**: AI recommendation badge
- **Agent Information**: Contact details for the listing agent
- **Analysis Link**: Direct link to full property analysis

## Technical Implementation

### Views

- `apps/property_ai/views/admin_views.py` - Contains all admin view logic
- `@user_passes_test(is_superuser)` - Ensures only superusers can access

### Templates

- `apps/property_ai/templates/property_ai/admin/agent_analytics.html`
- `apps/property_ai/templates/property_ai/admin/property_rankings.html`

### URLs

```python
# Admin-only views (superuser required)
path('dashboard/agents/', admin_views.agent_analytics, name='admin_agent_analytics'),
path('dashboard/rankings/', admin_views.property_rankings, name='admin_property_rankings'),
path('dashboard/api/agent/', admin_views.agent_api, name='admin_agent_api'),
```

### API Endpoint

- `GET /dashboard/api/agent/?agent_name=NAME` - Returns detailed agent statistics and recent properties

## Usage Examples

### Viewing Agent Performance

1. Log in as a superuser
2. Click your username in the top right
3. Select "Agent Analytics" from the dropdown
4. Browse agent cards to see performance metrics
5. Click "Details" on any agent for more information

### Finding Best Property Deals

1. Navigate to "Property Rankings"
2. Select "Best Price per m²" ranking type
3. Filter by location (e.g., "Tirana")
4. Browse top-ranked properties
5. Click "View Analysis" to see full AI analysis

### Analyzing Market Trends

1. Use different ranking types to understand market dynamics
2. Compare properties across different locations
3. Identify high-performing agents for potential partnerships
4. Track investment opportunities by market position

## Data Requirements

For these views to be useful, you need:

1. **Properties with Agent Data**: Properties must have `agent_name`, `agent_email`, and `agent_phone` fields populated
2. **Completed Analyses**: Properties should have `status='completed'` and investment scores
3. **Market Data**: Properties should have market position and opportunity scores for advanced rankings

## Testing

Run the test command to verify functionality:

```bash
python manage.py test_admin_views
```

This will:
- Check for superuser access
- Create test data if needed
- Verify both views work correctly
- Display agent and property counts

## Customization

### Adding New Ranking Types

To add new ranking criteria:

1. Add new ranking logic in `property_rankings` view
2. Update the template to display new metrics
3. Add filter options if needed

### Modifying Agent Metrics

To change agent ranking calculations:

1. Update the ranking formula in `agent_analytics` view
2. Modify difficulty coefficient calculation
3. Add new metrics to the agent cards

### Styling

The views use Bootstrap 5 with custom CSS for:
- Agent cards with hover effects
- Ranking badges with gold/silver/bronze styling
- Gradient backgrounds for stats cards
- Responsive design for mobile devices
