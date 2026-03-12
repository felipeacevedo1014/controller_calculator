# Controller Calculator User Guide

**Quick Start Guide  |  v1.3.1**

---

## Overview

The Controller Calculator helps you quickly select Trane/Tridium controllers, expand them with modules, and compare configurations with accurate pricing. Perfect for sizing HVAC control systems right the first time.

---

## Getting Started in 2 Minutes

### Single System Workflow

1. **Select Your Brand**
   - Choose **Trane** or **Tridium** from the brand dropdown (top-left)
   - Available controllers change based on brand

2. **Enter Your Point Requirements**
   - Fill in point counts:
     - **BO** (Binary Output): relay/coil switches
     - **BI** (Binary Input): switch/sensor inputs
     - **AO** (Analog Output): 4-20mA/0-10V outputs
     - **UI** (Unives Input): value inputs
     - **AI** (Analog Input): sensor values
   - Leave blank if not needed (defaults to 0)

3. **Add Expansions** *(optional)*
   - Check expansion boxes below controllers to add:
     - **XM90, XM30, XM32** (Trane)
     - **IO-R-16, IO-R-34** (Tridium JACE)
   - Each addition increases available points

4. **Set Pricing Multipliers** *(see Pricing section below)*
   - **Trane**: Default 1.00 (may be ≤ 1.0 with volume discounts)
   - **Tridium**: Default 1.00 (may be ≤ 1.0 with service contracts)
   - Adjust both fields to reflect your deal pricing

5. **Calculate**
   - Click **Calculate** → Results table shows all valid combinations
   - Green rows = within point budget; red rows = over budget
   - Prices are **final delivered costs** (list price × your multiplier)

6. **Export**
   - Click **Export to Excel** to save detailed specs and pricing
   - Use for quotes, documentation, or further analysis

---

## Batch Workflow (Multiple Systems)

Perfect for multi-building projects or comparing hundreds of point sets.

1. **Download Template**
   - Click **Download Template** in the "Batch Systems" tab
   - Opens a CSV file with column headers

2. **Fill in Your System Data**
   - One system per row:
     - System name
     - Point counts (BO, BI, AO, UI, AI)
     - Brand (Trane or Tridium)
     - Trane multiplier
     - Tridium multiplier
   - Save as `.xlsx` or `.csv`

3. **Load and Calculate**
   - Click **Load Systems from Excel**
   - Select your filled file
   - App processes all systems and displays results in the table

4. **View or Export Results**
   - Scroll through results for each system
   - Click **Export Results to Excel** for a complete analysis file
   - Results include all combinations + pricing for every system

---

## Understanding the Results Table

| Column | Meaning |
|--------|---------|
| **Controller** | Base controller name (S500, S800, JACE9000, etc.) |
| **Expansion 1, 2, 3** | Module names (e.g., XM90 + XM30 + XM32) |
| **Total Points** | Sum of all point types in the configuration |
| **Budget Points** | Maximum points this config can handle |
| **Color Indicator** | Green = within budget; Red = exceeds budget |
| **Price** | Final cost = (list price) × (your multiplier) |

---

## Pricing Model

### How Pricing Works

The app uses a **list price + multiplier** model to give you real-world pricing without exposing internal cost data.

**Formula:**
```
Final Price = List Price × Your Brand Multiplier
```

### Default Multipliers

| Brand | Default Multiplier | What It Means |
|-------|-------------------|---------------|
| **Trane** | 1.00 | Full list price; adjust down for volume deals |
| **Tridium** | 1.00 | Full list price; adjust down for service contracts |

### Examples

**Scenario 1: Volume Discount**
- Trane S500 list price = $2,200
- You negotiate 15% volume discount → multiplier = 0.85
- Final price = $2,200 × 0.85 = **$1,870**

**Scenario 2: Multi-Year Contract**
- Tridium JACE9000 list price = $3,100
- Service contract = 10% discount → multiplier = 0.90
- Final price = $3,100 × 0.90 = **$2,790**

### Adjusting Multipliers

- Use the spinner buttons (+ / −) or type directly
- Must be **greater than 0** (e.g., 0.50, 0.85, 1.00, 1.15)
- Multiplier applies to **all** controllers of that brand in the current calculation
- Click **Calculate** again to refresh pricing with new multiplier

---

## Active Product Catalog

### Controllers

| Brand | Models | Notes |
|-------|--------|-------|
| **Trane** | S500, S800, XM90, XM30, XM32, PM014 | Tested and current |
| **Tridium** | JACE9000, JACE9100, JACE9200, IO-R-16, IO-R-34 | Tested and current |

### Why Multipliers?

- **Security**: Real costs not exposed in publicly available data
- **Flexibility**: Reflects volume, service, or contract discounts you negotiate
- **Simplicity**: Single adjustment point instead of managing 6+ changing prices

---

## Tips & Tricks

### Point Balancing
- Try removing smaller expansions first if over budget—saves cost and complexity
- Larger expansions (XM90) give biggest point jump; use strategically

### Exporting Results
- Excel files include raw data and calculated combinations
- Colors (green/red) export for quick visual review in spreadsheets
- Reorder columns in Excel as needed; don't change point calculation columns

### Multiple Configurations
- Run single-system calcs with different multipliers to see price sensitivity
- Use batch mode for side-by-side comparisons across 10+ systems

### Common Issues
- **"No valid combinations found"**: Your point requirement may exceed any single controller. Try reducing points or using larger expansions.
- **All results red**: Budget exceeded for all options. Either reduce points or step up to a larger controller.

---

## Support & Feedback

For issues, feature requests, or to report incorrect pricing:

1. Check the README for technical details
2. Review the "Fork Notes" for recent changes and known limitations
3. Report issues via GitHub Issues

---

**Last Updated**: March 2026  
**Version**: 1.3.1  
**License**: MIT
