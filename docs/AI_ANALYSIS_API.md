# AI-Powered Change Detection API Documentation

## Overview

The AI Analysis API provides intelligent document change detection and classification for regulatory compliance monitoring. It uses advanced semantic similarity analysis and large language models to detect meaningful changes while filtering out cosmetic modifications.

## Base URL

```
http://localhost:8000/api/analysis
```

## Authentication

Currently, no authentication is required for the analysis endpoints. In production environments, appropriate authentication and rate limiting should be implemented.

## Endpoints

### 1. Document Comparison Analysis

**POST** `/compare`

Analyzes changes between two document versions using AI-powered semantic similarity and classification.

#### Request Body

```json
{
    "old_content": "string",
    "new_content": "string", 
    "form_name": "string (optional)",
    "agency_name": "string (optional)",
    "confidence_threshold": "integer (0-100, default: 70)",
    "use_llm_fallback": "boolean (default: true)"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `old_content` | string | Yes | Original document content |
| `new_content` | string | Yes | Updated document content |
| `form_name` | string | No | Name of the form (e.g., "WH-347") |
| `agency_name` | string | No | Name of the agency |
| `confidence_threshold` | integer | No | Minimum confidence threshold (0-100) |
| `use_llm_fallback` | boolean | No | Whether to use LLM for complex analysis |

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/analysis/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "old_content": "Employee Name: ________________\nHours Worked: ________\nRate: $15.00/hour",
    "new_content": "Employee Name: ________________\nRegular Hours: ________\nOvertime Hours: ________\nBase Rate: $15.50/hour\nOvertime Rate: $23.25/hour",
    "form_name": "WH-347",
    "agency_name": "Department of Labor",
    "confidence_threshold": 75,
    "use_llm_fallback": true
  }'
```

#### Response

```json
{
    "analysis_id": "analysis_abc123_1234567890",
    "timestamp": "2024-01-15T10:30:00Z",
    "has_meaningful_changes": true,
    "classification": {
        "category": "requirement_change",
        "subcategory": "field_modification", 
        "severity": "medium",
        "priority_score": 65,
        "is_cosmetic": false,
        "confidence": 85
    },
    "semantic_analysis": {
        "similarity_score": 72,
        "significant_differences": [
            "New overtime tracking fields added",
            "Rate structure modified to include overtime rates"
        ],
        "change_indicators": [
            "New important terms: overtime, base rate",
            "Structural change: 3 -> 5 lines"
        ],
        "model_name": "all-MiniLM-L6-v2",
        "processing_time_ms": 245
    },
    "llm_analysis": {
        "reasoning": "The document has been significantly updated to include overtime tracking capabilities, which represents a requirement change affecting payroll calculation workflows.",
        "key_changes": [
            "Addition of separate regular and overtime hour fields",
            "Implementation of dual-rate pay structure"
        ],
        "impact_assessment": "Medium impact on compliance - organizations must update their payroll systems to handle the new overtime tracking requirements.",
        "recommendations": [
            "Update payroll software to handle separate overtime calculations",
            "Train staff on new form structure",
            "Review existing processes for overtime hour tracking"
        ],
        "model_used": "gpt-3.5-turbo",
        "tokens_used": 342
    },
    "processing_summary": {
        "processing_time_ms": 1250,
        "semantic_model": "all-MiniLM-L6-v2",
        "classification_method": "llm",
        "cache_used": false,
        "analysis_version": "1.0"
    },
    "confidence_breakdown": {
        "semantic_similarity": 72,
        "classification_confidence": 85,
        "llm_analysis": 90,
        "overall": 82
    }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `analysis_id` | string | Unique identifier for this analysis |
| `has_meaningful_changes` | boolean | Whether meaningful changes were detected |
| `classification.category` | string | Primary change category (`form_update`, `requirement_change`, `logic_modification`, `cosmetic_change`) |
| `classification.severity` | string | Severity level (`low`, `medium`, `high`, `critical`) |
| `classification.priority_score` | integer | Priority score (0-100) |
| `semantic_analysis.similarity_score` | integer | Semantic similarity percentage (0-100) |
| `llm_analysis` | object | Optional detailed LLM analysis results |

### 2. Batch Document Analysis

**POST** `/batch`

Processes multiple document comparisons in parallel for efficient bulk analysis.

#### Request Body

```json
{
    "batch_id": "string (optional)",
    "analyses": [
        {
            "old_content": "string",
            "new_content": "string",
            "form_name": "string (optional)",
            "agency_name": "string (optional)"
        }
    ]
}
```

#### Limitations

- Maximum 10 analyses per batch
- Each analysis follows the same structure as single document comparison
- Individual failures don't affect other analyses in the batch

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/analysis/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "monthly_review_2024_01",
    "analyses": [
        {
            "old_content": "Form WH-347 Version 1...",
            "new_content": "Form WH-347 Version 2...",
            "form_name": "WH-347"
        },
        {
            "old_content": "Form CA_A1131 Version 1...", 
            "new_content": "Form CA_A1131 Version 2...",
            "form_name": "CA_A1131"
        }
    ]
  }'
```

#### Response

```json
{
    "batch_id": "monthly_review_2024_01",
    "timestamp": "2024-01-15T10:30:00Z",
    "total_analyses": 2,
    "successful_analyses": 2,
    "failed_analyses": 0,
    "results": [
        {
            "analysis_id": "analysis_def456_1234567891",
            "has_meaningful_changes": true,
            "classification": { /* ... */ },
            "semantic_analysis": { /* ... */ }
        }
    ],
    "errors": [],
    "processing_time_ms": 2340
}
```

### 3. Service Health Check

**GET** `/health`

Checks the operational status of all analysis components.

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/analysis/health"
```

#### Response

```json
{
    "service": "healthy",
    "semantic_analyzer": "healthy", 
    "llm_classifier": "healthy",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Status Values

- `healthy`: Component fully operational
- `degraded`: Component operational with limitations  
- `unhealthy`: Component not functioning

### 4. Service Statistics

**GET** `/stats`

Returns performance metrics and statistics for the analysis service.

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/analysis/stats"
```

#### Response

```json
{
    "total_analyses": 1247,
    "successful_analyses": 1198,
    "failed_analyses": 49,
    "avg_processing_time_ms": 890,
    "cache_hits": 156,
    "llm_fallback_count": 89,
    "cache_size": 45,
    "service_uptime_seconds": 86400
}
```

### 5. Clear Analysis Cache

**POST** `/cache/clear`

Clears the analysis result cache. Useful after model updates or for memory management.

#### Example Request

```bash
curl -X POST "http://localhost:8000/api/analysis/cache/clear"
```

#### Response

```json
{
    "status": "success",
    "message": "Analysis cache cleared successfully"
}
```

### 6. Model Information

**GET** `/models/info`

Returns information about the AI models currently in use.

#### Example Request

```bash
curl -X GET "http://localhost:8000/api/analysis/models/info"
```

#### Response

```json
{
    "semantic_model": {
        "name": "all-MiniLM-L6-v2",
        "similarity_threshold": 0.85,
        "status": "loaded"
    },
    "llm_model": {
        "name": "gpt-3.5-turbo",
        "temperature": 0.1,
        "max_tokens": 1000,
        "status": "available"
    },
    "service_config": {
        "confidence_threshold": 70,
        "max_processing_time": 180,
        "caching_enabled": true
    }
}
```

### 7. API Examples

**GET** `/examples`

Returns comprehensive examples for API integration and testing.

## Error Handling

### Standard Error Responses

#### 400 Bad Request
```json
{
    "detail": "Both old_content and new_content must be non-empty"
}
```

#### 408 Request Timeout
```json
{
    "detail": "Analysis analysis_xyz789_1234567890 timed out after 180 seconds"
}
```

#### 500 Internal Server Error
```json
{
    "detail": "Internal server error during analysis"
}
```

### Error Prevention

1. **Content Validation**: Ensure both `old_content` and `new_content` are non-empty
2. **Batch Size**: Keep batch requests under 10 analyses
3. **Content Length**: Very large documents may cause timeouts
4. **Rate Limiting**: Implement appropriate rate limiting in production

## Integration Examples

### Python Integration

```python
import requests
import json

def analyze_document_changes(old_content, new_content, form_name=None):
    """Analyze changes between document versions."""
    
    url = "http://localhost:8000/api/analysis/compare"
    payload = {
        "old_content": old_content,
        "new_content": new_content,
        "form_name": form_name,
        "confidence_threshold": 75,
        "use_llm_fallback": True
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        return {
            "has_changes": result["has_meaningful_changes"],
            "category": result["classification"]["category"],
            "severity": result["classification"]["severity"],
            "confidence": result["classification"]["confidence"],
            "description": result.get("llm_analysis", {}).get("reasoning", "")
        }
    else:
        response.raise_for_status()

# Usage example
old_form = "Employee Name: _____ Hours: _____"
new_form = "Employee Name: _____ Regular Hours: _____ Overtime Hours: _____"

result = analyze_document_changes(old_form, new_form, "WH-347")
print(f"Changes detected: {result['has_changes']}")
print(f"Category: {result['category']}")
print(f"Severity: {result['severity']}")
```

### JavaScript Integration

```javascript
async function analyzeDocumentChanges(oldContent, newContent, formName = null) {
    const url = 'http://localhost:8000/api/analysis/compare';
    
    const payload = {
        old_content: oldContent,
        new_content: newContent,
        form_name: formName,
        confidence_threshold: 75,
        use_llm_fallback: true
    };
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        return {
            hasChanges: result.has_meaningful_changes,
            category: result.classification.category,
            severity: result.classification.severity,
            confidence: result.classification.confidence,
            reasoning: result.llm_analysis?.reasoning || ''
        };
    } catch (error) {
        console.error('Analysis failed:', error);
        throw error;
    }
}

// Usage example
const oldForm = "Employee Name: _____ Hours: _____";
const newForm = "Employee Name: _____ Regular Hours: _____ Overtime Hours: _____";

analyzeDocumentChanges(oldForm, newForm, "WH-347")
    .then(result => {
        console.log('Changes detected:', result.hasChanges);
        console.log('Category:', result.category);
        console.log('Severity:', result.severity);
    })
    .catch(error => {
        console.error('Error:', error);
    });
```

## Performance Considerations

### Optimization Tips

1. **Caching**: Results are automatically cached based on content hash
2. **Batch Processing**: Use batch endpoints for multiple analyses
3. **Content Size**: Optimal performance with documents under 10KB
4. **Confidence Thresholds**: Higher thresholds reduce LLM usage and improve speed
5. **Parallel Processing**: Batch requests process analyses in parallel

### Performance Benchmarks

| Document Size | Processing Time | Memory Usage |
|---------------|----------------|--------------|
| < 1KB | 200-500ms | ~50MB |
| 1-5KB | 500-1000ms | ~100MB |
| 5-10KB | 1-2s | ~150MB |
| > 10KB | 2-5s | ~200MB+ |

## Security Considerations

### Production Deployment

1. **Authentication**: Implement API key or OAuth authentication
2. **Rate Limiting**: Protect against abuse with rate limiting
3. **Input Validation**: Sanitize all input content
4. **HTTPS**: Use HTTPS for all API communications
5. **API Keys**: Secure storage of OpenAI API keys
6. **Audit Logging**: Log all analysis requests for compliance

### Data Privacy

- Document content is processed in memory only
- No persistent storage of analyzed content (except optional caching)
- Cache can be cleared on demand
- LLM analysis may send content to external services (OpenAI)

## Troubleshooting

### Common Issues

1. **Service Unavailable (503)**
   - Check service health endpoint
   - Verify AI models are loaded
   - Check system resources

2. **Timeout Errors (408)**
   - Reduce document size
   - Increase timeout configuration
   - Check system performance

3. **Low Confidence Scores**
   - Documents may be very similar
   - Try lowering confidence threshold
   - Enable LLM fallback for better analysis

4. **Inconsistent Results**
   - Clear cache if models were updated
   - Check for proper content encoding
   - Verify document preprocessing

### Support

For additional support or questions:
- Check service health: `GET /api/analysis/health`
- View API examples: `GET /api/analysis/examples`
- Monitor service stats: `GET /api/analysis/stats`
- Review application logs for detailed error information