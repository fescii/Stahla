# Pricing Calculations and Algorithms

This document details the mathematical formulas, business rules, and algorithms used for pricing calculations in the Stahla AI SDR system.

## Overview

The pricing calculation engine determines rental costs based on multiple factors including trailer type, rental duration, usage type, seasonal multipliers, extras, delivery distance, and applicable taxes. The system is designed for accuracy, consistency, and performance.

## Base Pricing Calculation

### Trailer Type Pricing

Base pricing is determined by trailer type and rental duration:

```python
def calculate_base_price(trailer_type: str, rental_days: int, usage_type: str) -> float:
    """
    Calculate base rental price before extras and delivery
    
    Formula: base_rate * duration_multiplier * usage_multiplier * seasonal_multiplier
    """
```

#### Trailer Types and Base Rates

```yaml
trailer_pricing:
  "2_stall":
    daily: 150.00
    weekly: 900.00      # 10% discount vs 7 daily rates
    monthly: 3000.00    # 33% discount vs 30 daily rates
    
  "4_stall":
    daily: 200.00
    weekly: 1200.00
    monthly: 4000.00
    
  "6_stall":
    daily: 275.00
    weekly: 1650.00
    monthly: 5500.00
    
  "8_stall":
    daily: 350.00
    weekly: 2100.00
    monthly: 7000.00
    
  "luxury_2_stall":
    daily: 200.00
    weekly: 1200.00
    monthly: 4000.00
    
  "luxury_4_stall":
    daily: 300.00
    weekly: 1800.00
    monthly: 6000.00
```

### Duration Multipliers

Pricing tiers based on rental duration:

```python
def get_duration_multiplier(rental_days: int) -> Tuple[float, str]:
    """
    Determine pricing tier and multiplier based on rental duration
    
    Returns: (multiplier, tier_name)
    """
    if rental_days == 1:
        return (1.0, "daily")
    elif 2 <= rental_days <= 6:
        return (1.0, "daily")  # Daily rate applies
    elif 7 <= rental_days <= 29:
        return (0.857, "weekly")  # Weekly discount: 6/7 = ~0.857
    elif rental_days >= 30:
        return (0.667, "monthly")  # Monthly discount: 20/30 = ~0.667
```

### Usage Type Multipliers

Different pricing for event vs commercial usage:

```yaml
usage_multipliers:
  event: 1.0      # Standard event pricing
  commercial: 0.85  # 15% discount for commercial use
  municipal: 0.75   # 25% discount for government/municipal
  non_profit: 0.80  # 20% discount for non-profit organizations
```

### Seasonal Multipliers

Seasonal pricing adjustments based on demand:

```yaml
seasonal_multipliers:
  peak_season:      # May-September
    multiplier: 1.2
    months: [5, 6, 7, 8, 9]
    
  standard_season:  # March-April, October
    multiplier: 1.0
    months: [3, 4, 10]
    
  off_season:       # November-February
    multiplier: 0.9
    months: [11, 12, 1, 2]
    
  holiday_premium:  # Memorial Day, July 4th, Labor Day weekends
    multiplier: 1.5
    specific_dates: 
      - "2025-05-24"  # Memorial Day weekend
      - "2025-07-04"  # Independence Day
      - "2025-09-01"  # Labor Day weekend
```

## Extras Calculation

### Extra Items and Pricing

Additional services and their costs:

```yaml
extras_catalog:
  generators:
    "3kW Generator":
      daily_rate: 50.00
      weekly_rate: 300.00
      monthly_rate: 1000.00
      description: "Standard 3kW generator for basic power needs"
      
    "6kW Generator":
      daily_rate: 75.00
      weekly_rate: 450.00
      monthly_rate: 1500.00
      description: "Heavy-duty 6kW generator for extended power needs"
  
  services:
    "pump_out":
      per_service: 125.00
      description: "Additional pump out service during rental period"
      
    "cleaning":
      per_service: 75.00
      description: "Enhanced cleaning service"
      
    "setup_breakdown":
      per_event: 200.00
      description: "Full setup and breakdown service"
      
    "attendant":
      per_hour: 25.00
      minimum_hours: 4
      description: "On-site attendant service"
  
  accessories:
    "hand_washing_station":
      daily_rate: 25.00
      weekly_rate: 150.00
      monthly_rate: 500.00
      description: "Portable hand washing station"
      
    "luxury_amenities":
      daily_rate: 100.00
      weekly_rate: 600.00
      monthly_rate: 2000.00
      description: "Premium amenities package"
```

### Extras Calculation Logic

```python
def calculate_extras_cost(
    extras: List[ExtraItem], 
    rental_days: int
) -> Tuple[float, List[ExtraLineItem]]:
    """
    Calculate total cost for all extras
    
    Args:
        extras: List of requested extra items with quantities
        rental_days: Number of rental days for duration-based pricing
        
    Returns:
        (total_extras_cost, detailed_line_items)
    """
```

#### Calculation Examples

**Generator Rental (3kW, 5 days):**

```python
# 5 days = daily rate applies
cost = 50.00 * 5 * 1  # daily_rate * days * quantity
total = 250.00
```

**Pump Out Service (2 services):**

```python
# Per-service pricing
cost = 125.00 * 2  # per_service * quantity
total = 250.00
```

**Attendant Service (8 hours):**

```python
# Hourly pricing with minimum
hours = max(8, 4)  # Apply minimum hours
cost = 25.00 * 8  # per_hour * hours
total = 200.00
```

## Delivery Cost Calculation

### Distance-Based Pricing

Delivery costs are calculated based on distance and service zones:

```python
def calculate_delivery_cost(
    distance_miles: float,
    trailer_type: str,
    service_zone: str
) -> DeliveryCost:
    """
    Calculate delivery and pickup costs
    
    Formula: max(minimum_charge, base_rate + (distance * rate_per_mile))
    """
```

### Service Zone Rates

```yaml
delivery_zones:
  local:
    max_distance: 25
    base_rate: 25.00      # Base delivery charge
    rate_per_mile: 2.50   # Additional per mile
    minimum_charge: 50.00 # Minimum total charge
    
  regional:
    max_distance: 100
    base_rate: 50.00
    rate_per_mile: 3.00
    minimum_charge: 100.00
    
  extended:
    max_distance: 250
    base_rate: 100.00
    rate_per_mile: 3.50
    minimum_charge: 200.00
```

### Trailer Size Multipliers

Larger trailers have higher delivery costs:

```yaml
delivery_multipliers:
  "2_stall": 1.0
  "4_stall": 1.2
  "6_stall": 1.4
  "8_stall": 1.6
  "luxury_2_stall": 1.1
  "luxury_4_stall": 1.3
```

### Delivery Calculation Example

```python
# Example: 4-stall trailer, 30 miles (regional zone)
base_rate = 50.00
distance_cost = 30 * 3.00  # 90.00
trailer_multiplier = 1.2
subtotal = (base_rate + distance_cost) * trailer_multiplier
# (50.00 + 90.00) * 1.2 = 168.00

delivery_cost = max(subtotal, 100.00)  # Apply minimum
# final_cost = 168.00 (above minimum)
```

## Tax Calculation

### Tax Rate Determination

Tax rates are determined by delivery location and service type:

```python
def calculate_tax(
    subtotal: float,
    delivery_location: str,
    service_type: str = "rental"
) -> TaxCalculation:
    """
    Calculate applicable taxes based on location and service type
    
    Returns detailed tax breakdown
    """
```

### Tax Rate Configuration

```yaml
tax_rates:
  georgia:
    state_rate: 0.04      # 4% state sales tax
    local_rates:
      atlanta: 0.089      # 8.9% total (state + local)
      savannah: 0.08      # 8% total
      columbus: 0.075     # 7.5% total
      default: 0.07       # 7% default for other areas
      
  florida:
    state_rate: 0.06
    local_rates:
      miami: 0.085
      orlando: 0.075
      jacksonville: 0.0775
      default: 0.07
      
  alabama:
    state_rate: 0.04
    local_rates:
      birmingham: 0.10
      montgomery: 0.085
      mobile: 0.09
      default: 0.08
```

### Tax Exemptions

Support for tax-exempt organizations:

```yaml
tax_exemptions:
  non_profit: true      # 501(c)(3) organizations
  government: true      # Government entities
  religious: true       # Religious organizations
  educational: true     # Educational institutions
```

## Discount and Promotion Engine

### Discount Types

```yaml
discount_types:
  percentage:
    description: "Percentage off total"
    max_discount: 0.50  # Maximum 50% discount
    
  fixed_amount:
    description: "Fixed dollar amount off"
    max_discount: 1000.00
    
  free_delivery:
    description: "Free delivery service"
    applies_to: "delivery_cost"
    
  free_extras:
    description: "Complimentary extra services"
    applies_to: "extras_cost"
```

### Promotion Rules

```yaml
promotions:
  first_time_customer:
    type: "percentage"
    value: 0.15         # 15% off
    min_order: 300.00   # Minimum order amount
    max_discount: 200.00
    
  bulk_rental:
    type: "percentage"
    value: 0.10         # 10% off
    min_quantity: 3     # 3+ trailers
    applies_to: "base_cost"
    
  off_season:
    type: "percentage"
    value: 0.20         # 20% off
    months: [11, 12, 1, 2]  # Winter months
    max_discount: 500.00
    
  corporate_rate:
    type: "percentage"
    value: 0.12         # 12% off
    customer_type: "commercial"
    min_annual_volume: 10000.00
```

### Discount Application Order

Discounts are applied in a specific order to ensure fairness:

1. **Base Rental Discounts** - Applied to base rental cost
2. **Delivery Discounts** - Applied to delivery costs
3. **Extras Discounts** - Applied to extras costs
4. **Total Order Discounts** - Applied to subtotal
5. **Tax Calculation** - Tax calculated on discounted amount

```python
def apply_discounts(
    base_cost: float,
    delivery_cost: float,
    extras_cost: float,
    applicable_discounts: List[Discount]
) -> DiscountedPricing:
    """
    Apply discounts in proper order and calculate final pricing
    """
```

## Quote Validation and Business Rules

### Minimum Order Requirements

```yaml
minimums:
  order_total: 100.00    # Minimum total order
  rental_duration: 1     # Minimum 1 day rental
  advance_booking: 1     # Minimum 1 day advance notice
```

### Maximum Limits

```yaml
maximums:
  rental_duration: 365   # Maximum 1 year rental
  delivery_distance: 250 # Maximum delivery distance
  extras_quantity: 10    # Maximum quantity per extra item
```

### Business Rule Validations

```python
def validate_quote_request(request: QuoteRequest) -> ValidationResult:
    """
    Validate quote request against business rules
    
    Checks:
    - Rental duration limits
    - Delivery distance limits
    - Trailer availability
    - Service area coverage
    - Minimum order requirements
    """
```

## Performance Optimizations

### Calculation Caching

Cache calculated results to improve performance:

```python
# Cache key format
cache_key = f"quote:{hash(request_params)}"

# Cache TTL based on request type
cache_ttl = {
    "identical_request": 300,    # 5 minutes for identical requests
    "similar_location": 900,     # 15 minutes for same location
    "pricing_data": 1800         # 30 minutes for pricing rules
}
```

### Precomputed Values

Precompute common calculations:

- **Duration multipliers** - Cached multiplier lookup table
- **Tax rates** - Cached by ZIP code/city
- **Delivery zones** - Precomputed zone boundaries
- **Seasonal multipliers** - Date-based lookup table

### Batch Processing

For multiple quotes, optimize with batch processing:

```python
async def calculate_batch_quotes(
    requests: List[QuoteRequest]
) -> List[QuoteResponse]:
    """
    Process multiple quote requests efficiently
    
    Optimizations:
    - Batch geocoding requests
    - Shared pricing data lookup
    - Parallel processing where possible
    """
```

## Audit and Compliance

### Calculation Audit Trail

Track all calculation steps for transparency:

```python
class CalculationAudit:
    base_calculation: Dict[str, Any]
    extras_calculation: Dict[str, Any]
    delivery_calculation: Dict[str, Any]
    tax_calculation: Dict[str, Any]
    discounts_applied: List[Dict[str, Any]]
    final_totals: Dict[str, float]
    calculation_timestamp: datetime
    version: str  # Calculation engine version
```

### Regulatory Compliance

Ensure calculations comply with regulations:

- **Tax Compliance** - Accurate tax calculation by jurisdiction
- **Price Transparency** - Detailed breakdown of all charges
- **Fair Pricing** - Consistent application of pricing rules
- **Accessibility** - Support for various customer types and needs

### Version Control

Track changes to pricing rules and calculations:

```yaml
pricing_version:
  version: "2025.07.1"
  effective_date: "2025-07-01"
  changes:
    - "Updated seasonal multipliers"
    - "Added luxury trailer pricing"
    - "Modified delivery zone boundaries"
  migration_notes: "Automatic migration for existing quotes"
```
