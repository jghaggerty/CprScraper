# Compliance Monitoring Dashboard

A modern, responsive web interface for monitoring certified payroll compliance changes across government agencies.

## Features

### 🔍 Advanced Filtering & Search
- **Search**: Full-text search across forms, agencies, and change descriptions
- **State/Agency Type**: Filter by specific states or agency types
- **Agency**: Filter by specific government agencies
- **Form Type**: Filter by specific form types
- **Severity**: Filter by change severity (Critical, High, Medium, Low)
- **Date Range**: Filter by time periods (24h, 7d, 30d, 90d, 1y)
- **Status**: Filter by change status (New, Reviewed, Resolved, Ignored)

### 📊 Real-time Statistics
- Total agencies and active forms being monitored
- Change counts (total, last 24h, last week, last month)
- Critical changes requiring immediate attention
- System health status and coverage percentage

### 📋 Data Display
- **Table View**: Detailed tabular view with sortable columns
- **Card View**: Visual card-based layout for better overview
- **Pagination**: Navigate through large datasets efficiently
- **Sorting**: Sort by detection date, severity, agency, or form name

### 🚨 Active Alerts
- Real-time alerts for critical changes
- System health notifications
- Pending notification counts
- Failed monitoring run alerts

## Usage

### Accessing the Dashboard
1. Start the FastAPI server: `python main.py`
2. Navigate to: `http://localhost:8000/static/dashboard/`

### Using Filters
1. **Search**: Type in the search box to find specific forms, agencies, or changes
2. **Apply Filters**: Use the dropdown menus to filter by various criteria
3. **Clear Filters**: Click "Clear All" to reset all filters
4. **Applied Filters**: View and remove individual filters using the filter tags

### Viewing Results
1. **Switch Views**: Toggle between table and card views using the view buttons
2. **Sort Data**: Use the sort dropdown and order button to organize results
3. **Navigate Pages**: Use pagination controls to browse through results
4. **View Details**: Click "View" on any change to see detailed information

### Real-time Updates
- The dashboard automatically refreshes every 5 minutes
- Click the "Refresh" button for immediate updates
- System health is displayed in real-time in the header

## Technical Details

### API Endpoints Used
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/dashboard/filters` - Available filter options
- `POST /api/dashboard/search` - Search and filter changes
- `GET /api/dashboard/alerts` - Active alerts
- `GET /api/dashboard/health` - System health status

### Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile-responsive design
- Progressive enhancement for older browsers

### Performance Features
- Debounced search input (300ms delay)
- Lazy loading of results
- Efficient pagination
- Optimized API requests

## File Structure

```
static/dashboard/
├── index.html          # Main dashboard HTML
├── styles.css          # Dashboard styling
├── dashboard.js        # Dashboard functionality
├── dashboard.test.js   # Frontend tests
└── README.md          # This file
```

## Development

### Running Tests
```bash
# Run frontend tests
node static/dashboard/dashboard.test.js
```

### Customization
- Modify `styles.css` for visual changes
- Update `dashboard.js` for functionality changes
- Edit `index.html` for structural changes

### Adding New Features
1. Update the HTML structure in `index.html`
2. Add corresponding styles in `styles.css`
3. Implement functionality in `dashboard.js`
4. Add tests in `dashboard.test.js`

## Troubleshooting

### Common Issues
1. **Dashboard not loading**: Check if the FastAPI server is running
2. **No data displayed**: Verify database connection and API endpoints
3. **Filters not working**: Check browser console for JavaScript errors
4. **Mobile display issues**: Ensure responsive CSS is properly loaded

### Debug Mode
Open browser developer tools and check the console for detailed error messages and API request logs.

## Contributing

When adding new features:
1. Follow the existing code structure and naming conventions
2. Add appropriate error handling
3. Include tests for new functionality
4. Update this README with new features
5. Ensure mobile responsiveness is maintained 